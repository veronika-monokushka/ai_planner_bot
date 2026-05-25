# bot_backend/handlers/nutrition.py

"""Обработчики плана питания"""

import logging
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import asyncio

from .utils import main_menu
from bot_backend.states import UserState
from bot_backend.keyboards import (
    get_main_menu_keyboard,
    get_plan_actions_keyboard,
    get_budget_keyboard,
    get_back_to_menu_keyboard,
    get_days_keyboard, get_confirm_generate_list_keyboard,
    get_confirm_meal_plan_changes_keyboard,
    MAIN_MENU_BUTTON, CREATE_PLAN_BUTTON
)
from database import db
from ai_agent.meals_generator import create_meal_plan_ai

from bot_backend.logger import default_logger as logger

MAX_DAYS_PLAN = 3

def format_meal_plan_text(plan: dict, daily_calories: int = None) -> str:
    """
    Форматирует план питания в читаемый текст без заголовка.
    
    Args:
        plan: Словарь с планом питания вида:
            {
                "День 1": {
                    "завтрак": "...",
                    "обед": "...",
                    "ужин": "...",
                    "перекус": "..."
                },
                ...
            }
        daily_calories: Дневная норма калорий (опционально)
    
    Returns:
        str: Отформатированный текст плана
    """
    plan_text = ""
    
    for day, meals in plan.items():
        plan_text += f"📅 {day}:\n"
        plan_text += f"  🍳 Завтрак: {meals.get('завтрак', '-')}\n"
        plan_text += f"  🍲 Обед: {meals.get('обед', '-')}\n"
        plan_text += f"  🍽️ Ужин: {meals.get('ужин', '-')}\n"
        plan_text += f"  🥗 Перекус: {meals.get('перекус', '-')}\n\n"
    
    if daily_calories is not None:
        plan_text += f"🔥 Дневная норма: ~{daily_calories} ккал"
    
    return plan_text



# ===== Создание плана ===========================================================================

async def handle_plan_generation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик плана на неделю (для message updates)"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("Сначала зарегистрируйся через /start")
        return UserState.MAIN_MENU
    
    await update.message.reply_text(
        "📅 На сколько дней составить план питания?\n\n"
        f"Введи число от 1 до {MAX_DAYS_PLAN}:",
        reply_markup=get_days_keyboard()
    )
    context.user_data['awaiting_days_count'] = True
    return UserState.AWAITING_DAYS_COUNT


async def handle_plan_generation_callback(query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Обработчик для создания плана питания для quick_create_plan (без вывода текущего)
    1. Запрашивает количество дней и бюджет"""

    user_data = db.get_user(user_id)
    
    if not user_data:
        await query.message.reply_text("Сначала зарегистрируйся через /start")
        return UserState.MAIN_MENU
    
    # ✅ Спрашиваем количество дней
    await query.message.reply_text(
        "📅 На сколько дней составить план питания?\n\n"
        f"Введи число от 1 до {MAX_DAYS_PLAN}:",
        reply_markup=get_days_keyboard()
    )
    context.user_data['awaiting_days_count'] = True
    return UserState.AWAITING_DAYS_COUNT




# ===== Просмотр плана ===========================================================================

# Общая логика
def _get_nutrition_response(user_id: int) -> tuple:
    """Возвращает (plan_text, keyboard) или None если нет плана"""
    user_data = db.get_user(user_id)
    if not user_data:
        return None, None
    
    active_plan = db.get_active_meal_plan(user_id)
    
    if not active_plan:
        return None, get_plan_actions_keyboard()
    
    plan_text = "🍎 ТВОЙ ПЛАН ПИТАНИЯ\n\n"
    plan_text += format_meal_plan_text(active_plan.get('plan', {}), user_data.get('daily_calories', None))
    
    keyboard = get_plan_actions_keyboard()
    
    return plan_text, keyboard

# Тогда обработчики становятся тонкими:
async def handle_nutrition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == MAIN_MENU_BUTTON:
        return await main_menu(update)
        
    user_id = update.effective_user.id
    plan_text, keyboard = _get_nutrition_response(user_id)
    
    if plan_text is None and keyboard is None:
        await update.message.reply_text(
            "❌ Сначала зарегистрируйся через /start",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    elif plan_text is None:
        await update.message.reply_text(
            "🍎 РАЗДЕЛ ПИТАНИЯ\n\n"
            "У тебя нет активного плана питания.\n"
            "Хочешь создать новый?",
            reply_markup=keyboard
        )
        return UserState.AWAIT_CONFIRM_GENERATION
    else:
        await update.message.reply_text(plan_text, reply_markup=keyboard) 
    
    return UserState.AWAIT_CONFIRM_GENERATION


async def handle_nutrition_callback(query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    plan_text, keyboard = _get_nutrition_response(user_id)
    
    if plan_text is None and keyboard is None:
        await query.message.reply_text(
            "❌ Сначала зарегистрируйся через /start",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END
    
    elif plan_text is None:
        await query.message.reply_text(
            "🍎 РАЗДЕЛ ПИТАНИЯ\n\n"
            "У тебя нет активного плана питания.\n"
            "Хочешь создать новый?",
            reply_markup=keyboard
        )
        return UserState.AWAIT_CONFIRM_GENERATION
    else:
        await query.message.reply_text(plan_text, reply_markup=keyboard)
    
    return UserState.AWAIT_CONFIRM_GENERATION


async def handle_confirm_generation_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == MAIN_MENU_BUTTON:
        return await main_menu(update)
    
    if text == CREATE_PLAN_BUTTON or text == 'Да':
        return await handle_plan_generation(update, context)
    
    else:
        await update.message.reply_text(
            "Пожалуйста, используй кнопки меню 👇",
            reply_markup=get_plan_actions_keyboard()
        )
        return UserState.AWAIT_CONFIRM_GENERATION
        


#================================================================================
async def handle_days_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода количества дней"""
    text = update.message.text
    if text == MAIN_MENU_BUTTON:
        return await main_menu(update)

    try:
        count_days = int(text)
        
        if count_days < 1 or count_days > MAX_DAYS_PLAN:
            await update.message.reply_text(
                f"❌ Количество дней должно быть от 1 до {MAX_DAYS_PLAN}. Попробуй еще раз:",
                reply_markup=get_days_keyboard()
            )
            return UserState.AWAITING_DAYS_COUNT
        
        # ✅ Сохраняем количество дней в context.user_data
        context.user_data['meal_plan_days'] = count_days
        context.user_data.pop('awaiting_days_count', None)
        
        # ✅ Проверяем, есть ли бюджет в context.user_data
        budget = context.user_data.get('meal_plan_budget')
        
        if budget is not None:
            # Бюджет уже есть → сразу создаём план
            user_id = update.effective_user.id
            user_data = db.get_user(user_id)
            
            return await create_meal_plan(
                update, context, user_id, user_data, count_days, budget
            )
        else:
            # Бюджета нет → спрашиваем бюджет
            await update.message.reply_text(
                "💰 Учтем бюджет на еду?\nВведи сумму в рублях или нажми 'Пропустить'",
                reply_markup=get_budget_keyboard()
            )
            context.user_data['awaiting_budget'] = True
            return UserState.AWAITING_BUDGET
            
    except ValueError:
        await update.message.reply_text(
            f"❌ Пожалуйста, введи число от 1 до {MAX_DAYS_PLAN}:",
            reply_markup=get_days_keyboard()
        )
        return UserState.AWAITING_DAYS_COUNT


async def handle_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода бюджета и создание плана"""
    text = update.message.text
    if text == MAIN_MENU_BUTTON:
        return await main_menu(update)

    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    if not user_data:
        logger.error(f"❌ Профиль не найден user_id={user_id}.")
        await update.message.reply_text(
            "❌ Профиль не найден. Пожалуйста, начните с команды /start",
            reply_markup=get_main_menu_keyboard()
        )
        context.user_data.pop('awaiting_budget', None)
        return UserState.MAIN_MENU
    
    # ✅ Получаем количество дней из context
    count_days = context.user_data.get('meal_plan_days')

    # Если количество дней не найдено — возвращаемся к запросу дней
    if not count_days:
        await update.message.reply_text(
            f"📅 На сколько дней составить план?\nВведи число от 1 до {MAX_DAYS_PLAN}:",
            reply_markup=get_days_keyboard()
        )
        context.user_data['awaiting_days_count'] = True
        context.user_data.pop('awaiting_budget', None)
        return UserState.AWAITING_DAYS_COUNT
    
    if text == "⏭️ Пропустить":
        budget = None
        # ✅ Сохраняем бюджет в context
        context.user_data.pop('awaiting_budget', None)
        context.user_data['meal_plan_budget'] = budget
        return await create_meal_plan(update, context, user_id, user_data, count_days, budget)
            
    else:
        try:
            budget = float(text)
            if budget < 0:
                await update.message.reply_text(
                    "❌ Бюджет не может быть отрицательным. Введи положительное число или нажми 'Пропустить':",
                    reply_markup=get_budget_keyboard()
                )
                return UserState.AWAITING_BUDGET
            
            # ✅ Сохраняем бюджет в context
            context.user_data.pop('awaiting_budget', None)
            context.user_data['meal_plan_budget'] = budget
            return await create_meal_plan(update, context, user_id, user_data, count_days, budget)
            
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, используй кнопки или введи число:",
                reply_markup=get_budget_keyboard()
            )
            return UserState.AWAITING_BUDGET


async def create_meal_plan(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    user_id: int, 
    user_data: dict, 
    count_days: int,
    budget: int = None
):
    """Создаёт план питания через AI и сохраняет его в базу данных.
    
    Функция выполняет следующие шаги:
    1. Отправляет сообщение-загрузку пользователю
    2. Вызывает AI для генерации плана питания (create_meal_plan_ai)
    3. Сохраняет сгенерированный план в БД и контекст
    4. Форматирует план в читаемый текст с эмодзи
    5. Отображает план пользователю
    6. Предлагает создать список покупок на основе плана

    Returns:
        int: UserState.MAIN_MENU — после создания плана пользователь возвращается в главное меню
    """
    text = update.message.text
    if text == MAIN_MENU_BUTTON:
        return await main_menu(update)

    loading_message = await update.message.reply_text(
        "Составляю меню...\n"
        "Это займет немного времени!",
        reply_markup=None
    )
    
    user_from_db = db.get_user(user_id)
    preferences = user_from_db.get('preferences') if user_from_db else None
    
    result = create_meal_plan_ai(
        user_id=user_id,
        goal=user_data.get('goal', 'здоровое питание'),
        preferences_promt=preferences,
        count_days=count_days,
        use_saved_recipes=False,
        daily_calories=user_data.get('daily_calories', 2000),
        budget=budget,
        language="ru"
    )
    
    await loading_message.delete()
    
    # ✅ Получаем сохранённый план из БД
    meal_plan = db.get_active_meal_plan(user_id)
    
    if not meal_plan or not meal_plan.get('plan'):
        await update.message.reply_text(
            "❌ Не удалось сохранить план питания. Попробуй ещё раз.",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    plan = meal_plan.get('plan', {})
    
    # ✅ Сохраняем план в context.user_data для последующего использования
    context.user_data['last_created_plan'] = {
        'plan': plan,
        'budget': budget,
        'user_data': user_data
    }
    
    plan_text = "🍝 ТВОЙ НОВЫЙ ПЛАН ПИТАНИЯ\n\n"
    plan_text += format_meal_plan_text(plan, user_data.get('daily_calories', None))
    
    if budget is not None:
        plan_text += f"\n💰 Бюджет: {budget} руб."
    
    await update.message.reply_text(plan_text, reply_markup=get_main_menu_keyboard())
    
    # Убираем флаг ожидания ввода дней на всякий случай
    context.user_data.pop('awaiting_days_count', None)
    context.user_data.pop('awaiting_budget', None)

    # Спрашиваем хочет ли пользователь что-то изменить в плане
    await update.message.reply_text(
        "❓ Хочешь ли что-то изменить в этом плане?",
        reply_markup=get_confirm_meal_plan_changes_keyboard()
    )

    return UserState.CONFIRM_MEAL_PLAN_CHANGES


async def handle_create_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик создания плана (входная точка)"""
    text = update.message.text
    if text == MAIN_MENU_BUTTON:
        return await main_menu(update)

    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if text == CREATE_PLAN_BUTTON:
        # ✅ Сначала спрашиваем количество дней
        await update.message.reply_text(
            "📅 На сколько дней составить план питания?\n\n"
            f"Введи число от 1 до {MAX_DAYS_PLAN}:",
            reply_markup=get_days_keyboard()
        )
        context.user_data['awaiting_days_count'] = True
        return UserState.AWAITING_DAYS_COUNT
    elif text == MAIN_MENU_BUTTON:
        await update.message.reply_text("Главное меню", reply_markup=get_main_menu_keyboard())
        return UserState.MAIN_MENU
    else:
        await update.message.reply_text(
            "Пожалуйста, используй кнопки меню 👇",
            reply_markup=get_plan_actions_keyboard()
        )
        return UserState.MAIN_MENU


async def handle_confirm_meal_plan_changes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответа о необходимости изменений в плане питания"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == MAIN_MENU_BUTTON:
        return await main_menu(update)
    
    # Если ответ "Нет" - предложить создать список покупок
    if text == "✅ Нет, всё нравится":
        await update.message.reply_text(
            "🛒 Хочешь создать список покупок на основе этого плана?",
            reply_markup=get_confirm_generate_list_keyboard()
        )
        return UserState.AWAIT_CONFIRM_GENERATION
    
    # Если ответ "Да" или любой другой текст - перейти в режим модификации плана
    elif text == "✏️ Да, хочу изменить" or text != "✅ Нет, всё нравится":
        await update.message.reply_text(
            "✏️ Отлично! Напиши свои пожелания и я изменю план",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.MODIFY_MEAL_PLAN_INPUT
    
    else:
        await update.message.reply_text(
            "Пожалуйста, используй кнопки меню 👇",
            reply_markup=get_confirm_meal_plan_changes_keyboard()
        )
        return UserState.CONFIRM_MEAL_PLAN_CHANGES


async def handle_modify_meal_plan_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода пожеланий по изменению плана и отправка в агент"""
    from bot_backend.handlers.common import handle_agent_chat
    from ai_agent.agent_class import AgentWithMemory
    from ai_agent.mistral_llm_api import mistral_llm_client
    from ai_agent.tools import ALL_TOOLS, get_tool_executors
    from ai_agent.ai_logger import log_error
    from telegram import KeyboardButton, ReplyKeyboardMarkup
    
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == MAIN_MENU_BUTTON:
        return await main_menu(update)
    
    # Получаем последний созданный план из context
    last_plan = context.user_data.get('last_created_plan', {})
    plan_dict = last_plan.get('plan', {})
    
    # Форматируем план для вставки в промт
    plan_text = format_meal_plan_text(plan_dict, last_plan.get('user_data', {}).get('daily_calories', None))
    
    # Создаём модифицированное сообщение с информацией о плане
    modified_user_message = f"Я хочу изменить этот план питания:\n\n{plan_text}\n\nМои пожелания:\n{text}"
    
    # Получаем или создаем агента для этого пользователя
    agent_key = f"agent_{user_id}"
    if agent_key not in context.user_data:
        agent = AgentWithMemory(mistral_llm_client, user_id=user_id)
        context.user_data[agent_key] = agent
    else:
        agent = context.user_data[agent_key]
    
    # Показываем статус "печатает"
    await update.message.chat.send_action(action="typing")
    
    # Отправляем модифицированное сообщение в агент
    tool_executors = get_tool_executors()
    
    result = agent.ask_with_tools(
        user_message=modified_user_message,
        tools=ALL_TOOLS,
        tool_executors=tool_executors,
        max_tokens=300
    )
    
    # Получаем ответ
    if result.get("success"):
        response_text = result.get("response", "Готово!")
    else:
        error_text = result.get('error', 'Неизвестная ошибка')
        log_error(
            user_id=user_id,
            error_text=error_text,
            log_type='general'
        )
        
        if '429' in error_text:
            response_text = "Превышен лимит запросов в минуту, пожалуйста пишите не так быстро ❄"
        else:
            response_text = 'Неизвестная ошибка. Попробуйте пожалуйста снова или введите /start 😇'
    
    # Отправляем ответ пользователю
    from bot_backend.keyboards import get_agent_chat_keyboard
    await update.message.reply_text(
        response_text,
        reply_markup=get_agent_chat_keyboard()
    )
    
    # Переходим в режим чата с агентом
    return UserState.CHAT_WITH_AGENT

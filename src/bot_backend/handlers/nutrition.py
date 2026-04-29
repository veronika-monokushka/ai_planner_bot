# bot_backend/handlers/nutrition.py

"""Обработчики плана питания"""

import logging
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes


from ai_agent.meals_generator import create_meal_plan_ai 
from bot_backend.states import UserState
from bot_backend.keyboards import (
    get_main_menu_keyboard,      # Главное меню
    get_plan_actions_keyboard,   # Кнопки действий с планом
    get_budget_keyboard,         # Кнопки для ввода бюджета
    get_back_to_menu_keyboard    # Кнопка возврата в меню
)
from database import db

logger = logging.getLogger(__name__)


async def handle_week_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик плана на неделю"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("Сначала зарегистрируйся через /start")
        return UserState.MAIN_MENU
    
    active_plan = db.get_active_meal_plan(user_id)
    
    if not active_plan:
        await update.message.reply_text(
            "📅 У тебя нет активного плана на неделю.\nХочешь создать новый?",
            reply_markup=get_plan_actions_keyboard()
        )
        return UserState.MAIN_MENU
    else:
        plan_text = "📅 ТВОЙ ПЛАН НА НЕДЕЛЮ\n\n"
        for day, meals in active_plan.get('plan', {}).items():
            plan_text += f"{day}:\n"
            plan_text += f"  🍳 Завтрак: {meals.get('завтрак', '-')}\n"
            plan_text += f"  🍲 Обед: {meals.get('обед', '-')}\n"
            plan_text += f"  🍽️ Ужин: {meals.get('ужин', '-')}\n"
            plan_text += f"  🥗 Перекус: {meals.get('перекус', '-')}\n\n"
        
        plan_text += f"🔥 Дневная норма: ~{user_data.get('daily_calories', '?')} ккал\n"
        plan_text += f"💰 Бюджет на неделю: {active_plan.get('budget', 'не указан')} руб."
        
        await update.message.reply_text(plan_text, reply_markup=get_main_menu_keyboard())
        return UserState.MAIN_MENU

async def handle_nutrition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик раздела питания"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        await update.message.reply_text(
            "❌ Сначала зарегистрируйся через /start",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    active_plan = db.get_active_meal_plan(user_id)
    
    if not active_plan:
        # ✅ Здесь показываем кнопку "Создать план"
        await update.message.reply_text(
            "🍎 РАЗДЕЛ ПИТАНИЯ\n\n"
            "У тебя нет активного плана питания.\n"
            "Хочешь создать новый?",
            reply_markup=get_plan_actions_keyboard()
        )
        # ✅ Возвращаем MAIN_MENU, а не AWAITING_BUDGET
        # Потому что кнопка "Создать план" будет обработана в handle_main_menu
        return UserState.MAIN_MENU
    else:
        plan_text = "🍎 ТВОЙ ПЛАН ПИТАНИЯ\n\n"
        for day, meals in active_plan.get('plan', {}).items():
            plan_text += f"📅 {day}:\n"
            plan_text += f"  🍳 Завтрак: {meals.get('завтрак', '-')}\n"
            plan_text += f"  🍲 Обед: {meals.get('обед', '-')}\n"
            plan_text += f"  🍽️ Ужин: {meals.get('ужин', '-')}\n"
            plan_text += f"  🥗 Перекус: {meals.get('перекус', '-')}\n\n"
        
        plan_text += f"🔥 Дневная норма: ~{user_data.get('daily_calories', '?')} ккал\n"
        
        keyboard = [
            [KeyboardButton("📝 Создать новый план")],
            [KeyboardButton("🍳 Посмотреть рецепты")],
            [KeyboardButton("🔙 Главное меню")]
        ]
        
        await update.message.reply_text(
            plan_text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return UserState.MAIN_MENU


async def handle_create_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик создания плана"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    text = update.message.text
    
    if "Создать план" in text:
        await update.message.reply_text(
            "💰 Учтем бюджет на еду?\nВведи сумму в рублях на неделю (или нажми 'Пропустить'):",
            reply_markup=get_budget_keyboard()
        )
        return UserState.AWAITING_BUDGET
    elif text == "🔙 Вернуться в меню":
        await update.message.reply_text("Главное меню:", reply_markup=get_main_menu_keyboard())
        return UserState.MAIN_MENU
    else:
        await update.message.reply_text(
            "Пожалуйста, используй кнопки меню 👆",
            reply_markup=get_plan_actions_keyboard()
        )
        return UserState.MAIN_MENU

async def create_meal_plan(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    user_id: int, 
    user_data: dict, 
    budget: int = None
):
    """Вспомогательная функция для создания плана питания"""
    
    # ✅ Показываем индикатор загрузки
    loading_message = await update.message.reply_text(
        "🤖 AI составляет ваш план питания...\n"
        "Это займет немного времени!",
        reply_markup=None
    )
  
    result = await create_meal_plan_ai(
        goal=user_data.get('goal'),
        budget=budget,
        daily_calories=user_data.get('daily_calories', 2000),
        count_days=3
    )
    
    plan = result.get("plan", {})
    
    # ✅ Удаляем сообщение о загрузке
    await loading_message.delete()
    
    # ✅ Сохраняем план в базу данных
    db.save_meal_plan(user_id, {
        'plan': plan,
        'budget': budget,
        'created_at': datetime.now().isoformat()
    })
    
    # ✅ Сохраняем план в context.user_data для последующего использования
    context.user_data['last_created_plan'] = {
        'plan': plan,
        'budget': budget,
        'user_data': user_data
    }
    
    # ✅ Форматируем текст плана
    plan_text = "📅 ТВОЙ НОВЫЙ ПЛАН НА НЕДЕЛЮ\n\n"
    for day, meals in plan.items():
        plan_text += f"{day}:\n"
        plan_text += f"  🍳 Завтрак: {meals.get('завтрак', '-')}\n"
        plan_text += f"  🍲 Обед: {meals.get('обед', '-')}\n"
        plan_text += f"  🍽️ Ужин: {meals.get('ужин', '-')}\n"
        plan_text += f"  🥗 Перекус: {meals.get('перекус', '-')}\n\n"
    
    if budget:
        plan_text += f"💰 Бюджет на неделю: {budget} руб.\n"
    plan_text += f"🔥 Дневная норма: ~{user_data.get('daily_calories', '?')} ккал"
    
    await update.message.reply_text(plan_text, reply_markup=get_main_menu_keyboard())
    
    await update.message.reply_text(
        "🛒 Хочешь создать список покупок на основе этого плана?",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("✅ Да, создать список")],
            [KeyboardButton("🔙 Остаться в меню")]
        ], resize_keyboard=True)
    )

async def handle_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода бюджета и создание плана"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    text = update.message.text
    
    if text == "⏭️ Пропустить":
        budget = None
        await create_meal_plan(update, context, user_id, user_data, budget)
        return UserState.MAIN_MENU
    elif text == "🔙 Вернуться в меню":
        await update.message.reply_text("Главное меню:", reply_markup=get_main_menu_keyboard())
        return UserState.MAIN_MENU
    else:
        try:
            budget = float(text)
            if budget < 0:
                await update.message.reply_text(
                    "❌ Бюджет не может быть отрицательным. Введи положительное число или нажми 'Пропустить':",
                    reply_markup=get_budget_keyboard()
                )
                return UserState.AWAITING_BUDGET
            await create_meal_plan(update, context, user_id, user_data, budget)
            return UserState.MAIN_MENU
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, используй кнопки или введи число:",
                reply_markup=get_budget_keyboard()
            )
            return UserState.AWAITING_BUDGET
        

def format_meal_plan(plan_data: dict) -> str:
    """Форматирует план питания для вывода пользователю"""
    if not plan_data:
        return "📅 У тебя пока нет активного плана питания."
    
    plan = plan_data.get('plan', {})
    if not plan:
        return "📅 План питания пуст. Создай новый!"
    
    plan_text = "📅 ТВОЙ ПЛАН ПИТАНИЯ\n\n"
    for day, meals in plan.items():
        plan_text += f"{day}:\n"
        plan_text += f"  🍳 Завтрак: {meals.get('завтрак', '-')}\n"
        plan_text += f"  🍲 Обед: {meals.get('обед', '-')}\n"
        plan_text += f"  🍽️ Ужин: {meals.get('ужин', '-')}\n"
        plan_text += f"  🥗 Перекус: {meals.get('перекус', '-')}\n\n"
    
    return plan_text
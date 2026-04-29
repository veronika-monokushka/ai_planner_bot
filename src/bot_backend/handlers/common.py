# bot_backend/handlers/common.py
"""Общие обработчики"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot_backend.states import UserState
from bot_backend.keyboards import get_main_menu_keyboard, get_profile_actions_keyboard
from database import db

from .utils import recalculate_profile

logger = logging.getLogger(__name__)


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if not db.user_exists(user_id):
        await update.message.reply_text("Сначала зарегистрируйся через /start")
        return UserState.MAIN_MENU
    
    if text == "🤖 Спросить агента":
        await update.message.reply_text(
            "🤖 РЕЖИМ ОБЩЕНИЯ С ИИ-АГЕНТОМ\n\n"
            "Теперь ты можешь просто писать мне сообщения, и я буду отвечать.\n"
            "Я помогу с питанием, рецептами, напоминаниями и другими вопросами.\n\n"
            "Чтобы выйти из режима, нажми '🤖 Закончить диалог'",
            reply_markup=get_agent_chat_keyboard()
        )
        return UserState.CHAT_WITH_AGENT

    # ✅ Импортируем здесь, чтобы избежать циклических импортов
    from .nutrition import handle_week_plan, handle_nutrition, handle_create_plan
    from .recipes import handle_recipes_menu
    from .shopping import handle_shopping_list_menu

    from .reminders import handle_reminders_menu
    from .profile import show_profile, edit_profile_menu
    from .weighing import setup_weighing
    
    if text == "✅ Да, создать список": 
        return await handle_shopping_list_menu(update, context)
    
    if text in ["📝 Создать план", "📝 Создать новый план"]:
        return await handle_create_plan(update, context)
    elif text == "📅 План на неделю":
        return await handle_week_plan(update, context)
    elif text == "🍎 Питание":
        return await handle_nutrition(update, context)
    elif text == "📝 Мои рецепты":
        return await handle_recipes_menu(update, context)
    elif text == "📋 Список покупок":
        return await handle_shopping_list_menu(update, context)
    elif text == "💧 Напоминалки":
        return await handle_reminders_menu(update, context)
    elif text == "📊 Профиль":
        await show_profile(update, context)
    elif text in ["🔙 Вернуться в меню", "🔙 Назад в меню", "🔙 Главное меню"]:
        await update.message.reply_text("Главное меню:", reply_markup=get_main_menu_keyboard())
    elif text == "✏️ Редактировать профиль":
        return await edit_profile_menu(update, context)
    elif text == "📊 Пересчитать ИМТ":
        await recalculate_profile(update, context)
    elif text == "⚖️ Настроить взвешивание":
        return await setup_weighing(update, context)
    
    else:
        # Если сообщение не похоже на кнопку меню → переходим в режим агента
        # Проверяем, не является ли текст командой или кнопкой
        if text.startswith('/'):
            await update.message.reply_text(
                "Я не понимаю эту команду. Используй кнопки меню для навигации 👆",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            # Автоматически переключаемся в режим чата с агентом
            await update.message.reply_text(
                "Переключаюсь в режим общения с ИИ-агентом...\n\n"
                "Чтобы выйти из режима, нажми '🤖 Закончить диалог'",
                reply_markup=get_agent_chat_keyboard()
            )
            # Перенаправляем сообщение агенту
            return await handle_agent_chat(update, context)
    
    return UserState.MAIN_MENU



async def handle_agent_chat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало чата с AI агентом"""
    query = update.callback_query
    if query:
        await query.message.reply_text(
            "💬 Чат с AI-помощником\n\n"
            "Теперь ты можешь задавать мне любые вопросы о питании, "
            "рецептах, здоровом образе жизни. Я постараюсь помочь!\n\n"
            "Напиши свой вопрос, а я отвечу.\n\n"
            "Чтобы выйти из чата, отправь команду /cancel",
            reply_markup=None
        )
    else:
        await update.message.reply_text(
            "💬 Чат с AI-помощником\n\n"
            "Задай мне любой вопрос о питании, рецептах или здоровом образе жизни!\n\n"
            "Чтобы выйти из чата, отправь команду /cancel",
            reply_markup=None
        )
    return UserState.CHAT_WITH_AGENT

# bot_backend/handlers/common.py

async def handle_quick_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик быстрых действий с главного меню (Inline кнопки)"""
    from bot_backend.handlers.nutrition import handle_nutrition, handle_week_plan
    from bot_backend.handlers.profile import show_profile
    from bot_backend.handlers.reminders import handle_reminders_navigation
    from bot_backend.keyboards import get_main_menu_keyboard
    from database import db
    
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "quick_create_plan":
        # Вызываем существующую функцию handle_nutrition
        # Она сама отправит нужное сообщение и вернет состояние
        return await handle_nutrition(update, context)
        
    elif query.data == "quick_show_plan":
        # Вызываем функцию показа плана
        return await handle_week_plan(update, context)
        
    elif query.data == "quick_add_reminder":
        # Устанавливаем флаг и переходим в меню напоминаний
        context.user_data['from_quick_action'] = True
        return await handle_reminders_navigation(update, context)
        
    elif query.data == "quick_show_profile":
        # Показываем профиль
        await show_profile(update, context)
        return UserState.MAIN_MENU
        
    elif query.data == "quick_chat":
        # Переход в чат с AI
        await query.message.reply_text(
            "💬 Чат с AI-помощником\n\n"
            "Теперь ты можешь задавать мне любые вопросы о питании, "
            "рецептах, здоровом образе жизни.\n\n"
            "Напиши свой вопрос!\n\n"
            "Чтобы выйти, нажми '🤖 Закончить диалог'",
            reply_markup=get_agent_chat_keyboard()
        )
        return UserState.CHAT_WITH_AGENT
    
    return UserState.MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего действия"""
    await update.message.reply_text(
        "Действие отменено. Возвращаюсь в главное меню.",
        reply_markup=get_main_menu_keyboard()
    )
    return UserState.MAIN_MENU


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка неизвестных команд"""
    await update.message.reply_text(
        "Я не понимаю эту команду. Используй меню для навигации 👆",
        reply_markup=get_main_menu_keyboard()
    )


from ai_agent.agent_class import AgentWithMemory
from ai_agent.mistral_llm_api import mistral_llm_client
from ai_agent.tools import ALL_TOOLS, get_tool_executors
from telegram import KeyboardButton, ReplyKeyboardMarkup



# Создаем глобальный экземпляр агента (или можно создавать на пользователя)
# Для простоты используем глобальный, но учтите, что история диалога будет общей
_agent = None

"""
def get_agent():
    "Ленивая инициализация агента (синглтон)"
    global _agent
    if _agent is None:
        _agent = AgentWithMemory(mistral_llm_client)
    return _agent
"""

async def handle_agent_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик сообщений в режиме общения с AI агентом.
    Любое сообщение (кроме кнопки выхода) отправляется в LLM.
    """
    text = update.message.text
    user_id = update.effective_user.id
    
    # Кнопка для выхода из режима агента
    if text == "🤖 Закончить диалог" or text == "🔙 Вернуться в меню":
        agent_key = f"agent_{user_id}"
        if agent_key in context.user_data:
            context.user_data.pop(agent_key, None)
        
        await update.message.reply_text(
            "👋 Возвращаюсь в главное меню! Если захочешь ещё поговорить, просто напиши что-нибудь.",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    # Получаем или создаем агента для этого пользователя
    agent_key = f"agent_{user_id}"
    if agent_key not in context.user_data:
        agent = AgentWithMemory(mistral_llm_client, user_id=user_id)
        context.user_data[agent_key] = agent
    else:
        agent = context.user_data[agent_key]
    
    await update.message.chat.send_action(action="typing")
    
    tool_executors = get_tool_executors()
    
    result = agent.ask_with_tools(
        user_message=text,
        tools=ALL_TOOLS,
        tool_executors=tool_executors,
        max_tokens=300
    )
    
    # Получаем ответ (уже обработанный, с учетом выполнения инструментов)
    if result.get("success"):
        response_text = result.get("response", "Готово!")
    else:
        response_text = f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}"
    
    # Отправляем ответ пользователю
    await update.message.reply_text(
        response_text,
        reply_markup=get_agent_chat_keyboard()
    )
    
    return UserState.CHAT_WITH_AGENT

def get_agent_chat_keyboard():
    """Клавиатура для режима общения с агентом"""
    keyboard = [
        [KeyboardButton("🤖 Закончить диалог")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
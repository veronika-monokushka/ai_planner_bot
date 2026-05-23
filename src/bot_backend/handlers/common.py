# bot_backend/handlers/common.py
"""Общие обработчики"""
from telegram import Update
from telegram.ext import ContextTypes

from .utils import recalculate_profile
from bot_backend.handlers.nutrition import handle_budget, handle_nutrition_callback, handle_week_plan_callback, handle_days_count, handle_week_plan, handle_nutrition, handle_create_plan
from bot_backend.handlers.reminders import handle_reminders_menu_callback, handle_reminders_menu
from bot_backend.states import UserState
from bot_backend.keyboards import get_main_menu_keyboard, get_profile_actions_keyboard, MAIN_MENU_BUTTON, END_CHAT_BUTTON, get_agent_chat_keyboard
from database import db

from ai_agent.agent_class import AgentWithMemory
from ai_agent.mistral_llm_api import mistral_llm_client
from ai_agent.tools import ALL_TOOLS, get_tool_executors
from ai_agent.ai_logger import log_error
from telegram import KeyboardButton, ReplyKeyboardMarkup
from bot_backend.logger import default_logger as logger

Ami_text = ("🌺 Чат с Ами\n\n"
            #"Теперь ты можешь писать мне и я буду отвечать.\n"
            f"Чтобы выйти из режима, нажми '{END_CHAT_BUTTON}'")

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Главное меню 👇", reply_markup=get_main_menu_keyboard())
    return UserState.MAIN_MENU

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню"""
    logger.debug('handle_main_menu запущен')
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "🤖 Спросить агента":
        await update.message.reply_text(
            Ami_text,
            reply_markup=get_agent_chat_keyboard()
        )
        return UserState.CHAT_WITH_AGENT

    # ✅ Если мы ожидаем ввод количества дней, перенаправляем сюда сразу
    if context.user_data.get('awaiting_days_count'):
        logger.debug("Вызов handle_days_count из handle_main_menu")
        return await handle_days_count(update, context)
    
    if context.user_data.get('awaiting_budget'):
        return await handle_budget(update, context)

    from .recipes import handle_recipes_menu
    from .shopping import handle_shopping_list_menu
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
    elif text == "✏️ Редактировать профиль":
        return await edit_profile_menu(update, context)
    elif text == "📊 Пересчитать ИМТ":
        await recalculate_profile(update, context)
    elif text == "⚖️ Настроить взвешивание":
        return await setup_weighing(update, context)
    
    else:
        # Автоматически переключаемся в режим чата с агентом
        await update.message.reply_text(
            "Переключаюсь в режим общения с Ами...\n\n"
            "Чтобы выйти из режима, нажми {'🤖 Закончить диалог'}",
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
            Ami_text,
            reply_markup=None
        )
    else:
        await update.message.reply_text(
            Ami_text,
            reply_markup=None
        )
    return UserState.CHAT_WITH_AGENT

async def handle_quick_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик быстрых действий с главного меню (Inline кнопки)"""
   
    
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "quick_show_plan":
        return await handle_nutrition_callback(query, context, user_id)
        
    elif query.data == "quick_create_plan":
        return await handle_week_plan_callback(query, context, user_id)
        
    elif query.data == "quick_add_reminder":
        return await handle_reminders_menu_callback(query, context, user_id)
        
    elif query.data == "quick_chat":
        # Переход в чат с AI
        await query.message.reply_text(
            Ami_text,
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
        "Я не понимаю эту команду. Используй меню для навигации 👇",
        reply_markup=get_main_menu_keyboard()
    )


async def handle_agent_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик сообщений в режиме общения с AI агентом.
    Любое сообщение (кроме кнопки выхода) отправляется в LLM.
    """
    text = update.message.text
    user_id = update.effective_user.id
    
    # Кнопка для выхода из режима агента
    if text == END_CHAT_BUTTON or text == MAIN_MENU_BUTTON:
        
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
    await update.message.reply_text(
        response_text,
        reply_markup=get_agent_chat_keyboard()
    )
    
    return UserState.CHAT_WITH_AGENT

#bot.py
import logging
import asyncio
import sys
import os
import httpx
from datetime import datetime
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters, 
    ContextTypes,
    ConversationHandler
)
from telegram.request import HTTPXRequest
from telegram import Update, ReplyKeyboardRemove

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_backend.config import BOT_TOKEN
from bot_backend.states import UserState
from bot_backend.keyboards import MAIN_MENU_BUTTON, END_CHAT_BUTTON
from database import db
from bot_backend.handlers.common import handle_agent_chat, handle_quick_actions, main_menu, start_dialog_with_bot


from bot_backend.handlers import *

from bot_backend.logger import default_logger as logger


async def start_new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Автоматический обработчик сообщений от незарегистрированных пользователей.
    Запускает регистрацию без необходимости вводить /start.
    """
    logger.debug("start_new_session запущен")
    user_id = update.effective_user.id

    if not db.user_exists(user_id):
        # Автоматически запускаем регистрацию
        await update.message.reply_text(
            "👋 Привет! Я твой персональный помощник в питании Ами.\n"
            "Похоже, ты здесь впервые! Давай быстро зарегистрируемся.\n\n"
            "Как мне тебя называть?",
            reply_markup=ReplyKeyboardRemove()
        )
        # Инициализируем регистрацию и переходим к первому шагу
        from bot_backend.states import UserData
        UserData.init_registration(context)
        return UserState.REGISTRATION_NAME
    
    logger.debug("вызываем handle_main_menu из start_new_session")
    return await handle_main_menu(update, context)


def main():
    """Главная функция запуска бота"""
    
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        pool_timeout=30.0,
        http_version="1.1"
    )
    
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .build()
    )
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_reminder_jobs(application))
    
    # Регистрация обработчиков (порядок ВАЖЕН!)
    application.add_handler(CommandHandler('test_reminder', test_reminder_command))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, start_new_session)],
        states={
            # Регистрация
            UserState.REGISTRATION_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            UserState.REGISTRATION_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gender)],
            UserState.REGISTRATION_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age)],
            UserState.REGISTRATION_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weight)],
            UserState.REGISTRATION_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_height)],
            UserState.REGISTRATION_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_goal)],
            UserState.REGISTRATION_ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_activity)],
            UserState.REGISTRATION_CONFIRM: [CallbackQueryHandler(handle_confirmation, pattern="^(confirm_yes|confirm_no)$")],
            
            # Главное меню
            UserState.MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)],
            
            # Редактирование профиля
            UserState.EDIT_PROFILE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_profile)],
            UserState.EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
            UserState.EDIT_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_gender)],
            UserState.EDIT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_age)],
            UserState.EDIT_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_weight)],
            UserState.EDIT_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_height)],
            UserState.EDIT_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_goal)],
            
            # Создание меню
            UserState.AWAIT_CONFIRM_GENERATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_confirm_generation_plan)],
            UserState.AWAITING_DAYS_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_days_count)],
            UserState.AWAITING_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_budget)],
            
            # Рецепты
            UserState.RECIPES_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_recipes_navigation)],
            UserState.ADD_RECIPE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_name)],
            UserState.ADD_RECIPE_PORTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_portions)],
            UserState.ADD_RECIPE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_time)],
            UserState.ADD_RECIPE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_price)],
            UserState.ADD_RECIPE_TAGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_tags)],
            UserState.ADD_RECIPE_INGREDIENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_ingredients)],
            UserState.ADD_RECIPE_STEPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_steps)],
            UserState.SEARCH_RECIPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_recipe)],
            
            # Напоминания
            UserState.REMINDERS_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reminders_navigation)],
            UserState.ADD_REMINDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_name)],
            UserState.ADD_REMINDER_PERIODICITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_periodicity)],
            UserState.ADD_REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_time)],
            UserState.ADD_REMINDER_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_interval)],
            UserState.ADD_REMINDER_START_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_start_time)],
            UserState.ADD_REMINDER_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_datetime)],
            
            # Взвешивание
            UserState.WEIGHING_SETUP_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weighing_day)],
            UserState.WEIGHING_SETUP_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weighing_time)],
            UserState.WEIGHING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weighing_input)],
            
            # Список покупок
            UserState.SHOPPING_LIST_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_shopping_list_menu)],

            # Чат с агентом
            UserState.CHAT_WITH_AGENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_agent_chat)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start),
            CallbackQueryHandler(handle_quick_actions, pattern="^(quick_)"),
            CallbackQueryHandler(handle_recipe_callback, pattern="^(price_|time_|recipe_|increase_|decrease_|add_to_|recipes_page_|back_to_)"),
            CallbackQueryHandler(handle_weekday_callback, pattern="^weekday_"),
            CallbackQueryHandler(handle_reminder_callback, pattern="^(reminder_|pause_|back_to_reminder_)"),
            MessageHandler(filters.COMMAND, handle_unknown)
        ],
    )
    application.add_handler(conv_handler)

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog_with_bot))
    
    print("🤖 Бот запущен...")
    print("✅ Автоматическая регистрация включена (можно не писать /start)")
    print("="*40)
    
    application.run_polling(
        drop_pending_updates=True,
        poll_interval=1.0,
        timeout=60
    )


if __name__ == '__main__':
    main()
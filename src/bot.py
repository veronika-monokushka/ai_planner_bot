import logging
import asyncio
import sys
import os
import httpx
from datetime import datetime
#from telegram import Update
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

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_backend.config import BOT_TOKEN
from bot_backend.states import UserState
from bot_backend.keyboards import get_main_menu_keyboard
from database import db
from bot_backend.handlers.common import handle_agent_chat


# Импорты из handlers
from bot_backend.handlers import (
    start, handle_name, handle_gender, handle_age, handle_weight,
    handle_height, handle_goal, handle_confirmation,
    handle_main_menu,
    show_profile, edit_profile_menu, handle_edit_profile,
    edit_name, edit_gender, edit_age, edit_weight, edit_height,
    edit_goal, recalculate_profile,
    handle_week_plan, handle_nutrition, handle_create_plan, handle_budget,
    handle_recipes_menu, handle_recipes_navigation, handle_recipe_callback,
    add_recipe_name, add_recipe_portions, add_recipe_time, add_recipe_price,
    add_recipe_tags, add_recipe_ingredients, add_recipe_steps, search_recipe,
    handle_reminders_menu, handle_reminders_navigation, handle_reminder_callback,
    add_reminder_name, add_reminder_periodicity, add_reminder_time,
    add_reminder_interval, add_reminder_start_time, add_reminder_datetime,
    handle_weekday_callback,
    setup_weighing, handle_weighing_day, handle_weighing_time, handle_weighing_input,
    handle_shopping_list_menu, handle_shopping_list_actions,
    cancel, handle_unknown, test_reminder_command, setup_reminder_jobs
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


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
    
    application.add_handler(CommandHandler('test_reminder', test_reminder_command))
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            # Регистрация
            UserState.REGISTRATION_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            UserState.REGISTRATION_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gender)],
            UserState.REGISTRATION_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age)],
            UserState.REGISTRATION_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weight)],
            UserState.REGISTRATION_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_height)],
            UserState.REGISTRATION_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_goal)],
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
            
            # Питание
            UserState.AWAITING_BUDGET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_budget),
                MessageHandler(filters.Regex('^(📝 Создать план|🔙 Вернуться в меню)$'), handle_create_plan)
            ],
            
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
            UserState.SHOPPING_LIST_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_shopping_list_actions)],


            UserState.CHAT_WITH_AGENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_agent_chat)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            MessageHandler(filters.Regex('^(🔙 Вернуться в меню|🔙 Назад в меню|🔙 Главное меню)$'), handle_main_menu)
        ],
    )
    
    application.add_handler(CallbackQueryHandler(handle_recipe_callback, pattern="^(price_|time_|recipe_|increase_|decrease_|add_to_|recipes_page_|back_to_)"))
    application.add_handler(CallbackQueryHandler(handle_weekday_callback, pattern="^weekday_"))
    application.add_handler(CallbackQueryHandler(handle_reminder_callback, pattern="^(reminder_|pause_|back_to_reminder_)"))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.COMMAND, handle_unknown))
    
    print("🤖 Бот запущен...")
    print("="*40)
    
    application.run_polling(
        drop_pending_updates=True,
        poll_interval=1.0,
        timeout=30
    )


if __name__ == '__main__':
    main()
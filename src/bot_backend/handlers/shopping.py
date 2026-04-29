# bot_backend/handlers/shopping.py

import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from bot_backend.states import UserState
from bot_backend.keyboards import get_shopping_list_keyboard, get_main_menu_keyboard
from database import db

logger = logging.getLogger(__name__)


async def handle_shopping_list_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню списка покупок - генерирует список из активного плана"""
    user_id = update.effective_user.id
    
    # Получаем активный план питания
    active_plan = db.get_active_meal_plan(user_id)
    
    if not active_plan:
        await update.message.reply_text(
            "❌ Сначала создай план питания в разделе 'План на неделю'!",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    # Показываем индикатор загрузки
    loading_message = await update.message.reply_text(
        "🤖 AI составляет список покупок...\n"
        "Это займет немного времени!",
        reply_markup=None
    )
    
    try:
        # Вызываем инструмент генерации списка покупок (используя LLM агента)
        from ai_agent.tools import generate_shopping_list
        
        result = generate_shopping_list.invoke({
            "user_id": user_id
        })
        
        # Удаляем сообщение о загрузке
        await loading_message.delete()
        
        # Выводим результат
        await update.message.reply_text(
            result,
            reply_markup=get_main_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при генерации списка покупок: {e}")
        await loading_message.delete()
        await update.message.reply_text(
            f"❌ Ошибка при генерации списка: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )
    
    return UserState.MAIN_MENU
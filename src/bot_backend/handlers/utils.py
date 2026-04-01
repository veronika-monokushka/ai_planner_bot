# bot_backend/handlers/utils.py
"""Вспомогательные функции для обработчиков"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database import db, recalculate_user_data
from bot_backend.keyboards import get_profile_actions_keyboard

logger = logging.getLogger(__name__)


async def recalculate_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, show_menu=True):
    """Пересчет ИМТ и калорий"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        return
    
    updated_data = recalculate_user_data(user_data)
    db.update_user(
        user_id,
        bmi=updated_data['bmi'],
        bmi_category=updated_data['bmi_category'],
        daily_calories=updated_data['daily_calories'],
        goal_description=updated_data['goal_description']
    )
    
    if show_menu:
        await update.message.reply_text(
            "📊 Данные пересчитаны! Посмотри обновленный профиль.",
            reply_markup=get_profile_actions_keyboard()
        )
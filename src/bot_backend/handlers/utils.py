# bot_backend/handlers/utils.py
"""Вспомогательные функции для обработчиков"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database import db, recalculate_user_data
from bot_backend.keyboards import get_profile_actions_keyboard

from bot_backend.logger import default_logger as logger
from bot_backend.states import UserState
from bot_backend.keyboards import get_main_menu_keyboard


async def main_menu(update: Update):
    await update.message.reply_text("Главное меню 👇", reply_markup=get_main_menu_keyboard())
    return UserState.MAIN_MENU

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
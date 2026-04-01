# bot_backend/handlers/common.py
"""Общие обработчики"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot_backend.states import UserState
from bot_backend.keyboards import get_main_menu_keyboard, get_profile_actions_keyboard
from database import db

# ✅ Импортируем из utils
from .utils import recalculate_profile

logger = logging.getLogger(__name__)


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if not db.user_exists(user_id):
        await update.message.reply_text("Сначала зарегистрируйся через /start")
        return UserState.MAIN_MENU
    
    # ✅ Импортируем здесь, чтобы избежать циклических импортов
    from .nutrition import handle_week_plan, handle_nutrition, handle_create_plan
    from .recipes import handle_recipes_menu
    from .shopping import handle_shopping_list_menu, handle_create_shopping_list_from_plan

    from .reminders import handle_reminders_menu
    from .profile import show_profile, edit_profile_menu
    from .weighing import setup_weighing
    
    if text == "✅ Да, создать список": 
        return await handle_create_shopping_list_from_plan(update, context)
    
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
        await update.message.reply_text("Используй кнопки меню для навигации 👆", 
                                       reply_markup=get_main_menu_keyboard())
    
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
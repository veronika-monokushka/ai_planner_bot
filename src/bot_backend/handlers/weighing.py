"""Обработчики взвешивания"""

import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes

# ИСПРАВЛЕНО: убрал ai_planner_bot.
from bot_backend.states import UserState
from bot_backend.keyboards import (
    get_main_menu_keyboard, get_weighing_days_keyboard, 
    get_weighing_actions_keyboard
)
from database import db, get_motivational_message

logger = logging.getLogger(__name__)


async def setup_weighing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка напоминаний о взвешивании"""
    await update.message.reply_text(
        "⚖️ НАСТРОЙКА ВЗВЕШИВАНИЯ\n\n"
        "Хочешь, чтобы я напоминал взвешиваться раз в неделю?\n\n"
        "Выбери удобный день:",
        reply_markup=get_weighing_days_keyboard()
    )
    return UserState.WEIGHING_SETUP_DAY


async def handle_weighing_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора дня взвешивания"""
    day = update.message.text
    user_id = update.effective_user.id
    
    if day == "⏭️ Пропустить":
        await update.message.reply_text(
            "Хорошо, можешь настроить позже в разделе Профиль.",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    valid_days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    
    if day not in valid_days:
        await update.message.reply_text(
            "Пожалуйста, выбери день из кнопок:",
            reply_markup=get_weighing_days_keyboard()
        )
        return UserState.WEIGHING_SETUP_DAY
    
    context.user_data['weighing_day'] = day
    
    await update.message.reply_text(
        f"Выбран день: {day}\n\n"
        "В какое время тебе удобно взвешиваться?\n"
        "(в формате ЧЧ:ММ, например 09:00)\n\n"
        "💡 Рекомендую делать это утром натощак",
        reply_markup=ReplyKeyboardRemove()
    )
    return UserState.WEIGHING_SETUP_TIME


async def handle_weighing_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора времени взвешивания"""
    try:
        time_str = update.message.text
        datetime.strptime(time_str, "%H:%M")
        
        user_id = update.effective_user.id
        day = context.user_data.get('weighing_day')
        
        weighing_settings = {
            'day': day,
            'time': time_str,
            'enabled': True
        }
        
        db.update_user(user_id, weighing_settings=weighing_settings)
        
        await update.message.reply_text(
            f"✅ Отлично! Каждый {day} в {time_str} я буду спрашивать твой новый вес ⚖️",
            reply_markup=get_main_menu_keyboard()
        )
        
        return UserState.MAIN_MENU
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат времени. Используй ЧЧ:ММ (например 09:00):"
        )
        return UserState.WEIGHING_SETUP_TIME


async def handle_weighing_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода веса"""
    if update.message.text == "🔔 Напомнить позже":
        await update.message.reply_text(
            "Хорошо, напомню через час!",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    elif update.message.text == "⏭️ Пропустить эту неделю":
        await update.message.reply_text(
            "Хорошо, пропускаем эту неделю. Увидимся через 7 дней!",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    try:
        weight = float(update.message.text.replace(',', '.'))
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        
        if weight < 20 or weight > 300:
            await update.message.reply_text(
                "❌ Вес должен быть от 20 до 300 кг. Попробуй еще раз:",
                reply_markup=get_weighing_actions_keyboard()
            )
            return UserState.WEIGHING_INPUT
        
        weight_history = user_data.get('weight_history', [])
        prev_weight = weight_history[-1]['weight'] if weight_history else user_data.get('weight', weight)
        
        db.add_weight_record(user_id, weight)
        
        weight_change = weight - prev_weight
        goal = user_data.get('goal')
        total_lost = weight_history[0]['weight'] - weight if weight_history and goal == "⚖️ Похудеть" else None
        remaining = None
        
        motivation = get_motivational_message(goal, weight_change, total_lost, remaining)
        
        await update.message.reply_text(
            f"⚖️ Твой вес: {weight} кг\n"
            f"Изменение: {weight_change:+.1f} кг\n\n"
            f"{motivation}",
            reply_markup=get_main_menu_keyboard()
        )
        
        return UserState.MAIN_MENU
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введи корректное число:",
            reply_markup=get_weighing_actions_keyboard()
        )
        return UserState.WEIGHING_INPUT
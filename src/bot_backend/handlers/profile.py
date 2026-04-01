# bot_backend/handlers/profile.py
"""Обработчики профиля и его редактирования"""

import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from bot_backend.states import UserState
from bot_backend.keyboards import (
    get_edit_profile_keyboard, get_profile_actions_keyboard, 
    get_gender_keyboard, get_goal_keyboard
)
from database import db
from .utils import recalculate_profile  # ✅ Импортируем из utils

logger = logging.getLogger(__name__)


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает профиль пользователя"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ Профиль не найден. Начни регистрацию с /start")
        return
    
    weight_history = user_data.get('weight_history', [])
    last_weight = weight_history[-1]['weight'] if weight_history else user_data.get('weight', 0)
    first_weight = weight_history[0]['weight'] if weight_history else last_weight
    total_change = last_weight - first_weight
    
    profile_text = (
        f"📊 ТВОЙ ПРОФИЛЬ\n\n"
        f"👤 Имя: {user_data.get('name', 'Не указано')}\n"
        f"⚥ Пол: {user_data.get('gender', 'Не указан')}\n"
        f"📅 Возраст: {user_data.get('age', '?')} лет\n"
        f"⚖️ Вес: {user_data.get('weight', '?')} кг\n"
        f"📏 Рост: {user_data.get('height', '?')} см\n"
        f"🎯 Цель: {user_data.get('goal', 'Не указана')}\n\n"
        f"📈 ИМТ: {user_data.get('bmi', '?')} ({user_data.get('bmi_category', '?')})\n"
        f"🔥 Дневная норма: ~{user_data.get('daily_calories', '?')} ккал\n"
        f"📝 Режим: {user_data.get('goal_description', '?')}\n\n"
        f"⚖️ Изменение веса: {total_change:+.1f} кг\n"
        f"📅 Зарегистрирован: {user_data.get('registered_at', '?')[:10]}"
    )
    
    weighing_settings = user_data.get('weighing_settings', {})
    if weighing_settings:
        profile_text += f"\n\n📅 День взвешивания: {weighing_settings.get('day', 'не выбран')} в {weighing_settings.get('time', '??:??')}"
    
    await update.message.reply_text(profile_text, reply_markup=get_profile_actions_keyboard())


async def edit_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню редактирования профиля"""
    await update.message.reply_text(
        "✏️ РЕДАКТИРОВАНИЕ ПРОФИЛЯ\n\nЧто ты хочешь изменить?",
        reply_markup=get_edit_profile_keyboard()
    )
    return UserState.EDIT_PROFILE_MENU


async def handle_edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора что редактировать"""
    text = update.message.text
    
    if text == "👤 Изменить имя":
        await update.message.reply_text("Введи новое имя:", reply_markup=ReplyKeyboardRemove())
        return UserState.EDIT_NAME
    elif text == "⚥ Изменить пол":
        await update.message.reply_text("Выбери пол:", reply_markup=get_gender_keyboard())
        return UserState.EDIT_GENDER
    elif text == "📅 Изменить возраст":
        await update.message.reply_text("Введи новый возраст:", reply_markup=ReplyKeyboardRemove())
        return UserState.EDIT_AGE
    elif text == "⚖️ Изменить вес":
        await update.message.reply_text("Введи новый вес (в кг):", reply_markup=ReplyKeyboardRemove())
        return UserState.EDIT_WEIGHT
    elif text == "📏 Изменить рост":
        await update.message.reply_text("Введи новый рост (в см):", reply_markup=ReplyKeyboardRemove())
        return UserState.EDIT_HEIGHT
    elif text == "🎯 Изменить цель":
        await update.message.reply_text("Выбери новую цель:", reply_markup=get_goal_keyboard())
        return UserState.EDIT_GOAL
    elif text == "🔙 Вернуться в профиль":
        await show_profile(update, context)
        return UserState.MAIN_MENU
    else:
        await update.message.reply_text(
            "Пожалуйста, используй кнопки меню", 
            reply_markup=get_edit_profile_keyboard()
        )
        return UserState.EDIT_PROFILE_MENU


async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование имени"""
    new_name = update.message.text.strip()
    user_id = update.effective_user.id
    
    if len(new_name) < 2 or len(new_name) > 50:
        await update.message.reply_text("❌ Имя должно быть от 2 до 50 символов. Попробуй еще раз:")
        return UserState.EDIT_NAME
    
    db.update_user(user_id, name=new_name)
    await update.message.reply_text(f"✅ Имя успешно изменено на {new_name}!", reply_markup=get_edit_profile_keyboard())
    await recalculate_profile(update, context, show_menu=False)
    return UserState.EDIT_PROFILE_MENU


async def edit_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование пола"""
    new_gender = update.message.text
    user_id = update.effective_user.id
    
    if new_gender not in ["👨 Мужской", "👩 Женский"]:
        await update.message.reply_text("Пожалуйста, выбери пол, используя кнопки:", reply_markup=get_gender_keyboard())
        return UserState.EDIT_GENDER
    
    db.update_user(user_id, gender=new_gender)
    await update.message.reply_text(f"✅ Пол изменен!", reply_markup=get_edit_profile_keyboard())
    await recalculate_profile(update, context, show_menu=False)
    return UserState.EDIT_PROFILE_MENU


async def edit_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование возраста"""
    try:
        new_age = int(update.message.text)
        user_id = update.effective_user.id
        
        db.update_user(user_id, age=new_age)
        await update.message.reply_text(f"✅ Возраст изменен на {new_age} лет!", reply_markup=get_edit_profile_keyboard())
        await recalculate_profile(update, context, show_menu=False)
        return UserState.EDIT_PROFILE_MENU
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введи корректное число:")
        return UserState.EDIT_AGE


async def edit_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование веса"""
    try:
        new_weight = float(update.message.text.replace(',', '.'))
        user_id = update.effective_user.id
        
        if new_weight < 20 or new_weight > 300:
            await update.message.reply_text("❌ Вес должен быть от 20 до 300 кг. Попробуй еще раз:")
            return UserState.EDIT_WEIGHT
        
        db.update_user(user_id, weight=new_weight)
        await update.message.reply_text(f"✅ Вес изменен на {new_weight} кг!", reply_markup=get_edit_profile_keyboard())
        await recalculate_profile(update, context, show_menu=False)
        return UserState.EDIT_PROFILE_MENU
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введи корректное число:")
        return UserState.EDIT_WEIGHT


async def edit_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование роста"""
    try:
        new_height = float(update.message.text.replace(',', '.'))
        user_id = update.effective_user.id
        
        if new_height < 100 or new_height > 250:
            await update.message.reply_text("❌ Рост должен быть от 100 до 250 см. Попробуй еще раз:")
            return UserState.EDIT_HEIGHT
        
        db.update_user(user_id, height=new_height)
        await update.message.reply_text(f"✅ Рост изменен на {new_height} см!", reply_markup=get_edit_profile_keyboard())
        await recalculate_profile(update, context, show_menu=False)
        return UserState.EDIT_PROFILE_MENU
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введи корректное число:")
        return UserState.EDIT_HEIGHT


async def edit_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование цели"""
    new_goal = update.message.text
    user_id = update.effective_user.id
    valid_goals = ["⚖️ Похудеть", "💪 Набрать мышечную массу", "😊 Просто жить (поддержание)"]
    
    if new_goal not in valid_goals:
        await update.message.reply_text("Пожалуйста, выбери цель, используя кнопки:", reply_markup=get_goal_keyboard())
        return UserState.EDIT_GOAL
    
    db.update_user(user_id, goal=new_goal)
    await update.message.reply_text(f"✅ Цель изменена!", reply_markup=get_edit_profile_keyboard())
    await recalculate_profile(update, context, show_menu=False)
    return UserState.EDIT_PROFILE_MENU
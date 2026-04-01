"""Обработчики регистрации пользователя"""

import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from bot_backend.states import UserState, UserData
from bot_backend.keyboards import (
    get_gender_keyboard, get_goal_keyboard, get_confirmation_keyboard, 
    get_main_menu_keyboard
)
from database import db, calculate_bmi, calculate_calories, get_bmi_category

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    if db.user_exists(user_id):
        await update.message.reply_text(
            f"С возвращением, {db.get_user(user_id).get('name', 'друг')}! 👋\n"
            "Чем займемся сегодня?",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    await update.message.reply_text(
        "👋 Привет! Я твой личный помощник в здоровье.\n"
        "Давай настроим твой профиль. Это займет 1 минуту.\n\n"
        "Как мне тебя называть? Введи свое имя:",
        reply_markup=ReplyKeyboardRemove()
    )
    
    UserData.init_registration(context)
    return UserState.REGISTRATION_NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода имени"""
    name = update.message.text.strip()
    
    if len(name) < 2 or len(name) > 50:
        await update.message.reply_text("❌ Имя должно быть от 2 до 50 символов. Попробуй еще раз:")
        return UserState.REGISTRATION_NAME
    
    UserData.set_registration_field(context, 'name', name)
    
    await update.message.reply_text(
        f"Приятно познакомиться, {name}! 👋\nТеперь выбери свой пол:",
        reply_markup=get_gender_keyboard()
    )
    return UserState.REGISTRATION_GENDER


async def handle_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора пола"""
    gender = update.message.text
    
    if gender not in ["👨 Мужской", "👩 Женский"]:
        await update.message.reply_text(
            "Пожалуйста, выбери пол, используя кнопки ниже:", 
            reply_markup=get_gender_keyboard()
        )
        return UserState.REGISTRATION_GENDER
    
    UserData.set_registration_field(context, 'gender', gender)
    
    await update.message.reply_text(
        "📅 Введи свой возраст:",
        reply_markup=ReplyKeyboardRemove()
    )
    return UserState.REGISTRATION_AGE


async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода возраста"""
    try:
        age = int(update.message.text)
        UserData.set_registration_field(context, 'age', age)
        await update.message.reply_text("⚖️ Введи свой вес (в кг):")
        return UserState.REGISTRATION_WEIGHT
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введи корректное число:")
        return UserState.REGISTRATION_AGE


async def handle_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода веса"""
    try:
        weight = float(update.message.text.replace(',', '.'))
        if weight < 20 or weight > 300:
            await update.message.reply_text("❌ Вес должен быть от 20 до 300 кг. Попробуй еще раз:")
            return UserState.REGISTRATION_WEIGHT
        
        UserData.set_registration_field(context, 'weight', weight)
        await update.message.reply_text("📏 Введи свой рост (в см):")
        return UserState.REGISTRATION_HEIGHT
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введи корректное число (например: 70.5):")
        return UserState.REGISTRATION_WEIGHT


async def handle_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода роста"""
    try:
        height = float(update.message.text.replace(',', '.'))
        if height < 100 or height > 250:
            await update.message.reply_text("❌ Рост должен быть от 100 до 250 см. Попробуй еще раз:")
            return UserState.REGISTRATION_HEIGHT
        
        UserData.set_registration_field(context, 'height', height)
        await update.message.reply_text(
            "🎯 Выбери свою главную цель:",
            reply_markup=get_goal_keyboard()
        )
        return UserState.REGISTRATION_GOAL
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введи корректное число (например: 175):")
        return UserState.REGISTRATION_HEIGHT


async def handle_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора цели"""
    goal = update.message.text
    valid_goals = ["⚖️ Похудеть", "💪 Набрать мышечную массу", "😊 Просто жить (поддержание)"]
    
    if goal not in valid_goals:
        await update.message.reply_text(
            "Пожалуйста, выбери цель, используя кнопки ниже:", 
            reply_markup=get_goal_keyboard()
        )
        return UserState.REGISTRATION_GOAL
    
    UserData.set_registration_field(context, 'goal', goal)
    data = UserData.get_registration_data(context)
    
    bmi = calculate_bmi(data['weight'], data['height'])
    calories = calculate_calories(data['gender'], data['weight'], data['height'], data['age'])
    
    if goal == "⚖️ Похудеть":
        calories = int(calories * 0.85)
        goal_desc = "дефицит калорий"
    elif goal == "💪 Набрать мышечную массу":
        calories = int(calories * 1.15)
        goal_desc = "профицит калорий"
    else:
        goal_desc = "поддержание формы"
    
    data['bmi'] = bmi
    data['bmi_category'] = get_bmi_category(bmi)
    data['daily_calories'] = calories
    data['goal_description'] = goal_desc
    
    await update.message.reply_text(
        f"📊 ТВОИ ДАННЫЕ:\n\n"
        f"👤 Имя: {data['name']}\n"
        f"⚥ Пол: {data['gender']}\n"
        f"📅 Возраст: {data['age']} лет\n"
        f"⚖️ Вес: {data['weight']} кг\n"
        f"📏 Рост: {data['height']} см\n"
        f"🎯 Цель: {goal}\n\n"
        f"📈 Твой ИМТ: {bmi} ({data['bmi_category']})\n"
        f"🔥 Дневная норма калорий: ~{calories} ккал ({goal_desc})\n\n"
        f"Сохраняем профиль?",
        reply_markup=get_confirmation_keyboard()
    )
    return UserState.REGISTRATION_CONFIRM


async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения регистрации"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_yes":
        user_id = update.effective_user.id
        data = UserData.get_registration_data(context)
        
        data['telegram_username'] = update.effective_user.username or "NoUsername"
        data['telegram_first_name'] = update.effective_user.first_name
        data['registered_at'] = query.message.date.isoformat()
        data['weight_history'] = [{'date': datetime.now().isoformat(), 'weight': data['weight']}]
        
        db.save_user(user_id, data)
        
        await query.edit_message_text(
            f"✅ Профиль успешно сохранен!\n\nПриятно познакомиться, {data['name']}! "
            "Теперь ты можешь пользоваться всеми функциями бота.",
            reply_markup=None
        )
        
        await query.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    else:
        await query.edit_message_text(
            "❌ Регистрация отменена. Для начала заново введи /start", 
            reply_markup=None
        )
        return ConversationHandler.END
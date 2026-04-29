"""Обработчики регистрации пользователя"""

import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from bot_backend import AGENT_DESCRIPTION
from bot_backend.states import UserState, UserData
from bot_backend.keyboards import (
    get_gender_keyboard, get_goal_keyboard, get_activity_keyboard,
    get_confirmation_keyboard, get_main_menu_keyboard
)
from database import db, calculate_bmi, get_bmi_category

logger = logging.getLogger(__name__)


# Коэффициенты активности
ACTIVITY_FACTORS = {
    "Сидячий и малоподвижный": 1.2,
    "Легкая активность (1-3 раза в неделю)": 1.375,
    "Средняя активность (3-5 раз в неделю)": 1.55,
    "Высокая активность (6-7 раз в неделю)": 1.725
}


def calculate_bmr(gender: str, weight: float, height: float, age: int) -> float:
    """
    Расчет базового метаболизма (Basal Metabolic Rate) по формуле Миффлина-Сан Жеора.
    
    Для мужчин: BMR = 10 × вес + 6.25 × рост − 5 × возраст + 5
    Для женщин: BMR = 10 × вес + 6.25 × рост − 5 × возраст − 161
    """
    if "Мужской" in gender:
        return (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        return (10 * weight) + (6.25 * height) - (5 * age) - 161


def calculate_daily_calories(
    gender: str, 
    weight: float, 
    height: float, 
    age: int, 
    activity_level: str,
    goal: str
) -> int:
    """
    Расчет дневной нормы калорий с учетом:
    1. Базового метаболизма (BMR)
    2. Коэффициента физической активности
    3. Коррекции под цель (похудение/набор/поддержание)
    """
    # 1. Базовый метаболизм
    bmr = calculate_bmr(gender, weight, height, age)
    
    # 2. Умножаем на коэффициент активности
    activity_factor = ACTIVITY_FACTORS.get(activity_level, 1.2)
    tdee = bmr * activity_factor  # Total Daily Energy Expenditure
    
    # 3. Коррекция под цель
    if goal == "⚖️ Похудеть":
        calories = tdee - 350
    elif goal == "💪 Набрать мышечную массу":
        calories = tdee + 350
    else:
        calories = tdee
    
    return max(int(calories), 1200)  # минимум 1200 ккал для здоровья


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
    
    if len(name) < 2 or len(name) > 20:
        await update.message.reply_text("❌ Имя должно быть от 2 до 20 символов. Попробуй еще раз:")
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
    
    if gender not in ["👨 М", "👩 Ж"]:
        await update.message.reply_text(
            "Пожалуйста, выбери пол, используя кнопки ниже:", 
            reply_markup=get_gender_keyboard()
        )
        return UserState.REGISTRATION_GENDER
    gender = gender[-1]
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
        if age < 10 or age > 120:
            await update.message.reply_text("❌ Возраст должен быть от 10 до 120 лет. Попробуй еще раз:")
            return UserState.REGISTRATION_AGE
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
    
    # ✅ Новый шаг: вопрос об активности
    await update.message.reply_text(
        "🏃‍♂️ Какой у тебя уровень физической активности?\n\n"
        "Выбери подходящий вариант:",
        reply_markup=get_activity_keyboard()
    )
    return UserState.REGISTRATION_ACTIVITY


async def handle_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора уровня активности"""
    activity = update.message.text
    
    valid_activities = list(ACTIVITY_FACTORS.keys())
    if activity not in valid_activities:
        await update.message.reply_text(
            "Пожалуйста, выбери уровень активности, используя кнопки ниже:",
            reply_markup=get_activity_keyboard()
        )
        return UserState.REGISTRATION_ACTIVITY
    
    UserData.set_registration_field(context, 'activity', activity)
    data = UserData.get_registration_data(context)
    
    # ✅ РАСЧЕТ КАЛОРИЙ ПО НОВОЙ ФОРМУЛЕ
    bmi = calculate_bmi(data['weight'], data['height'])
    calories = calculate_daily_calories(
        gender=data['gender'],
        weight=data['weight'],
        height=data['height'],
        age=data['age'],
        activity_level=activity,
        goal=data['goal']
    )
    
    # Описание цели для пользователя
    goal = data['goal']
    if goal == "⚖️ Похудеть":
        goal_desc = "дефицит 350 калорий"
    elif goal == "💪 Набрать мышечную массу":
        goal_desc = "профицит 350 калорий"
    else:
        goal_desc = "поддержание формы"
    
    data['bmi'] = bmi
    data['bmi_category'] = get_bmi_category(bmi)
    data['daily_calories'] = calories
    data['goal_description'] = goal_desc
    data['activity_factor'] = ACTIVITY_FACTORS.get(activity, 1.2)
    
    # Расшифровка активности для отображения
    activity_desc = {
        "Сидячий и малоподвижный": "Сидячий образ жизни, без тренировок",
        "Легкая активность (1-3 раза в неделю)": "Легкие тренировки 1-3 раза в неделю",
        "Средняя активность (3-5 раз в неделю)": "Умеренные тренировки 3-5 раз в неделю",
        "Высокая активность (6-7 раз в неделю)": "Интенсивные тренировки 6-7 раз в неделю"
    }.get(activity, activity)
    
    await update.message.reply_text(
        f"📊 ТВОИ ДАННЫЕ:\n\n"
        f"👤 Имя: {data['name']}\n"
        f"🚻 Пол: {data['gender']}\n"
        f"📅 Возраст: {data['age']} лет\n"
        f"⚖️ Вес: {data['weight']} кг\n"
        f"📏 Рост: {data['height']} см\n"
        f"🎯 Цель: {goal}\n"
        f"🏃‍♂️ Активность: {activity_desc}\n\n"
        f"📈 Твой ИМТ: {bmi} ({data['bmi_category']})\n"
        f"🔥 Дневная норма калорий: ~{calories} ккал ({goal_desc})\n\n"
        f"Сохраняем профиль?",
        reply_markup=get_confirmation_keyboard()
    )
    return UserState.REGISTRATION_CONFIRM


async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения регистрации"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
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
        
        # ✅ Используем константу из __init__.py
        greeting = f"✨ Приятно познакомиться, {data['name']}! 👋\n\n"
        
        await query.edit_message_text(
            greeting + AGENT_DESCRIPTION,
            reply_markup=None
        )
        
        # Клавиатура с вариантами выбора действий
        keyboard = [
            [InlineKeyboardButton("🥗 Создать план питания", callback_data="quick_create_plan")],
            [InlineKeyboardButton("📅 Мой план питания", callback_data="quick_show_plan")],
            [InlineKeyboardButton("⏰ Добавить напоминание", callback_data="quick_add_reminder")],
            [InlineKeyboardButton("📊 Мой профиль", callback_data="quick_show_profile")],
            [InlineKeyboardButton("💬 Чат с AI", callback_data="quick_chat")],
        ]
        
        await query.message.reply_text(
            "Выбери действие из меню или спроси у меня 😏",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return UserState.MAIN_MENU
    else:
        await query.edit_message_text(
            "❌ Регистрация отменена. Для начала заново введи /start", 
            reply_markup=None
        )
        return ConversationHandler.END
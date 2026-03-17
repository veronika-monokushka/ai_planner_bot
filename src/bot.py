from ai_agent.meals_generator import create_meal_plan_ai, generate_shopping_list_ai

from tg_bot.config import BOT_TOKEN
from tg_bot.states import UserState, UserData
from tg_bot.keyboards import *
from tg_bot.database import db, calculate_bmi, calculate_calories, get_bmi_category, recalculate_user_data, get_motivational_message


import logging
import asyncio
from datetime import datetime, timedelta
import re
import httpx
from telegram import Update, ReplyKeyboardRemove
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
import json

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================== РЕГИСТРАЦИЯ ========================

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
    gender = update.message.text
    
    if gender not in ["👨 Мужской", "👩 Женский"]:
        await update.message.reply_text("Пожалуйста, выбери пол, используя кнопки ниже:", reply_markup=get_gender_keyboard())
        return UserState.REGISTRATION_GENDER
    
    UserData.set_registration_field(context, 'gender', gender)
    
    await update.message.reply_text(
        "📅 Введи свой возраст:",
        reply_markup=ReplyKeyboardRemove()
    )
    return UserState.REGISTRATION_AGE

async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода возраста (без ограничений)"""
    try:
        age = int(update.message.text)
        UserData.set_registration_field(context, 'age', age)
        await update.message.reply_text("⚖️ Введи свой вес (в кг):")
        return UserState.REGISTRATION_WEIGHT
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введи корректное число:")
        return UserState.REGISTRATION_AGE

async def handle_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    goal = update.message.text
    valid_goals = ["⚖️ Похудеть", "💪 Набрать мышечную массу", "😊 Просто жить (поддержание)"]
    
    if goal not in valid_goals:
        await update.message.reply_text("Пожалуйста, выбери цель, используя кнопки ниже:", reply_markup=get_goal_keyboard())
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
        await query.edit_message_text("❌ Регистрация отменена. Для начала заново введи /start", reply_markup=None)
        return ConversationHandler.END

# ======================== ГЛАВНОЕ МЕНЮ ========================

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if not db.user_exists(user_id):
        await update.message.reply_text("Сначала зарегистрируйся через /start")
        return UserState.MAIN_MENU
    
    if text == "📝 Создать план":
        return await handle_create_plan(update, context)

    if text == "📅 План на неделю":
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
        await update.message.reply_text("Используй кнопки меню для навигации 👆", reply_markup=get_main_menu_keyboard())
    
    return UserState.MAIN_MENU

# ======================== ПРОФИЛЬ И РЕДАКТИРОВАНИЕ ========================

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(
        "✏️ РЕДАКТИРОВАНИЕ ПРОФИЛЯ\n\nЧто ты хочешь изменить?",
        reply_markup=get_edit_profile_keyboard()
    )
    return UserState.EDIT_PROFILE_MENU

async def handle_edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text("Пожалуйста, используй кнопки меню", reply_markup=get_edit_profile_keyboard())
        return UserState.EDIT_PROFILE_MENU

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    """Редактирование возраста (без ограничений)"""
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

async def recalculate_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, show_menu=True):
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

# ======================== ПЛАН НА НЕДЕЛЮ ========================

async def handle_week_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("Сначала зарегистрируйся через /start")
        return UserState.MAIN_MENU
    
    active_plan = db.get_active_meal_plan(user_id)
    
    if not active_plan:
        await update.message.reply_text(
            "📅 У тебя нет активного плана на неделю.\nХочешь создать новый?",
            reply_markup=get_plan_actions_keyboard()
        )
        return UserState.MAIN_MENU
    else:
        plan_text = "📅 ТВОЙ ПЛАН НА НЕДЕЛЮ\n\n"
        for day, meals in active_plan.get('plan', {}).items():
            plan_text += f"{day}:\n"
            plan_text += f"  🍳 Завтрак: {meals.get('завтрак', '-')}\n"
            plan_text += f"  🍲 Обед: {meals.get('обед', '-')}\n"
            plan_text += f"  🍽️ Ужин: {meals.get('ужин', '-')}\n"
            plan_text += f"  🥗 Перекус: {meals.get('перекус', '-')}\n\n"
        
        plan_text += f"🔥 Дневная норма: ~{user_data.get('daily_calories', '?')} ккал\n"
        plan_text += f"💰 Бюджет на неделю: {active_plan.get('budget', 'не указан')} руб."
        
        await update.message.reply_text(plan_text, reply_markup=get_main_menu_keyboard())
        return UserState.MAIN_MENU

# ======================== ПИТАНИЕ ========================


async def handle_nutrition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        await update.message.reply_text(
            "❌ Сначала зарегистрируйся через /start",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    active_plan = db.get_active_meal_plan(user_id)
    
    if not active_plan:
        await update.message.reply_text(
            "🍎 РАЗДЕЛ ПИТАНИЯ\n\n"
            "У тебя нет активного плана питания.\n"
            "Хочешь создать новый с помощью AI?",
            reply_markup=get_plan_actions_keyboard()
        )
        return UserState.AWAITING_BUDGET
    else:
        plan_text = "🍎 ТВОЙ ПЛАН ПИТАНИЯ\n\n"
        for day, meals in active_plan.get('plan', {}).items():
            plan_text += f"📅 {day}:\n"
            plan_text += f"  🍳 Завтрак: {meals.get('завтрак', '-')}\n"
            plan_text += f"  🍲 Обед: {meals.get('обед', '-')}\n"
            plan_text += f"  🍽️ Ужин: {meals.get('ужин', '-')}\n"
            plan_text += f"  🥗 Перекус: {meals.get('перекус', '-')}\n\n"
        
        plan_text += f"🔥 Дневная норма: ~{user_data.get('daily_calories', '?')} ккал\n"
        
        keyboard = [
            [KeyboardButton("📝 Создать план")],
            [KeyboardButton("🍳 Посмотреть рецепты")],
            [KeyboardButton("🔙 Главное меню")]
        ]
        
        await update.message.reply_text(
            plan_text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return UserState.MAIN_MENU

async def handle_create_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    text = update.message.text
    
    if text == "📝 Создать план":
        await update.message.reply_text(
            "💰 Учтем бюджет на еду?\n"
            "Введи сумму в рублях на неделю (или нажми 'Пропустить'):",
            reply_markup=get_budget_keyboard()
        )
        return UserState.AWAITING_BUDGET
    elif text == "🔙 Вернуться в меню":
        await update.message.reply_text("Главное меню:", reply_markup=get_main_menu_keyboard())
        return UserState.MAIN_MENU
    else:
        await update.message.reply_text(
            "Пожалуйста, используй кнопки меню 👆",
            reply_markup=get_plan_actions_keyboard()
        )
        return UserState.MAIN_MENU

async def create_meal_plan(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, user_data: dict, budget=None):
    """Асинхронная версия создания плана через AI"""
    
    # Запускаем генерацию плана через AI
    await update.message.reply_text(
        "🤖 AI составляет ваш план питания...\n"
        "Это займет немного времени!",
        reply_markup=None
    )
    
    result = await create_meal_plan_ai(
        goal=user_data.get('goal', ''),
        budget=budget,
        daily_calories=user_data.get('daily_calories', 2000),
        count_days=3
    )
    
    if not result["success"]:
        await update.message.reply_text(
            f"⚠️ Не удалось создать план (AI временно недоступен).\n"
            f"Но мы сохраним базовый вариант для вас:\n\n"
            f"```{json.dumps(result['plan'], ensure_ascii=False, indent=2)}```",
            parse_mode="Markdown"
        )
        return
    
    plan = result.get("plan", {})
    
    # Сохраняем план в базу данных
    db.save_meal_plan(user_id, {
        'plan': plan,
        'budget': budget,
        'created_at': datetime.now().isoformat(),
        'source': 'ai' if result["success"] else 'fallback'
    })
    
    # Форматируем вывод пользователю
    plan_text = "📅 ТВОЙ НОВЫЙ ПЛАН НА НЕДЕЛЮ\n\n"
    for day, meals in plan.items():
        plan_text += f"{day}:\n"
        plan_text += f"  🍳 Завтрак: {meals.get('завтрак', '-\n')}\n"
        plan_text += f"  🍲 Обед: {meals.get('обед', '-')}\n"
        plan_text += f"  🍽️ Ужин: {meals.get('ужин', '-\n')}\n"
        plan_text += f"  🥗 Перекус: {meals.get('перекус', '-\n')}\n\n"
    
    if budget:
        plan_text += f"💰 Бюджет на неделю: {budget} руб.\n"
    plan_text += f"🔥 Дневная норма: ~{user_data.get('daily_calories', '?')} ккал"
    
    await update.message.reply_text(plan_text, reply_markup=get_main_menu_keyboard())
    
    # Предлагаем создать список покупок
    await update.message.reply_text(
        "🛒 Хочешь создать список покупок на основе этого плана?",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("✅ Да, создать список")],
            [KeyboardButton("🔙 Остаться в меню")]
        ], resize_keyboard=True)
    )

async def handle_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода бюджета и создание плана через AI"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    text = update.message.text
    
    if text == "⏭️ Пропустить":
        budget = None
        await create_meal_plan(update, context, user_id, user_data, budget)
        return UserState.MAIN_MENU
    elif text == "🔙 Вернуться в меню":
        await update.message.reply_text("Главное меню:", reply_markup=get_main_menu_keyboard())
        return UserState.MAIN_MENU
    else:
        try:
            budget = float(text)
            if budget < 0:
                await update.message.reply_text(
                    "❌ Бюджет не может быть отрицательным. Введи положительное число или нажми 'Пропустить':",
                    reply_markup=get_budget_keyboard()
                )
                return UserState.AWAITING_BUDGET
            await create_meal_plan(update, context, user_id, user_data, budget)
            return UserState.MAIN_MENU
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, используй кнопки или введи число:",
                reply_markup=get_budget_keyboard()
            )
            return UserState.AWAITING_BUDGET


# ======================== РЕЦЕПТЫ ========================

async def handle_recipes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню рецептов - только категории по времени"""
    await update.message.reply_text(
        "🍳 МОИ РЕЦЕПТЫ\n\n"
        "Выбери категорию по времени приготовления:",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("🥚 Быстрые (до 30 мин)")],
            [KeyboardButton("⏲️ Средние (30-60 мин)")],
            [KeyboardButton("🔥 Сложные (более 1 часа)")],
            [KeyboardButton("📚 Все рецепты")],
            [KeyboardButton("➕ Добавить рецепт")],
            [KeyboardButton("🔍 Поиск")],
            [KeyboardButton("🔙 Назад в меню")]
        ], resize_keyboard=True)
    )
    return UserState.RECIPES_MENU

async def handle_recipes_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Навигация по меню рецептов"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "🥚 Быстрые (до 30 мин)":
        await update.message.reply_text(
            "🥚 БЫСТРЫЕ РЕЦЕПТЫ (до 30 мин)\n\n"
            "Теперь выбери ценовую категорию:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💚 Бюджетные", callback_data="price_budget_fast")],
                [InlineKeyboardButton("💛 Средние", callback_data="price_medium_fast")],
                [InlineKeyboardButton("❤️ Дорогие", callback_data="price_expensive_fast")],
                [InlineKeyboardButton("🎲 Все быстрые", callback_data="price_all_fast")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_recipes_time")]
            ])
        )
        return UserState.RECIPES_MENU
    
    elif text == "⏲️ Средние (30-60 мин)":
        await update.message.reply_text(
            "⏲️ СРЕДНИЕ РЕЦЕПТЫ (30-60 мин)\n\n"
            "Теперь выбери ценовую категорию:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💚 Бюджетные", callback_data="price_budget_medium")],
                [InlineKeyboardButton("💛 Средние", callback_data="price_medium_medium")],
                [InlineKeyboardButton("❤️ Дорогие", callback_data="price_expensive_medium")],
                [InlineKeyboardButton("🎲 Все средние", callback_data="price_all_medium")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_recipes_time")]
            ])
        )
        return UserState.RECIPES_MENU
    
    elif text == "🔥 Сложные (более 1 часа)":
        await update.message.reply_text(
            "🔥 СЛОЖНЫЕ РЕЦЕПТЫ (более 1 часа)\n\n"
            "Теперь выбери ценовую категорию:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💚 Бюджетные", callback_data="price_budget_hard")],
                [InlineKeyboardButton("💛 Средние", callback_data="price_medium_hard")],
                [InlineKeyboardButton("❤️ Дорогие", callback_data="price_expensive_hard")],
                [InlineKeyboardButton("🎲 Все сложные", callback_data="price_all_hard")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_recipes_time")]
            ])
        )
        return UserState.RECIPES_MENU
    
    elif text == "📚 Все рецепты":
        recipes = db.get_user_recipes(user_id)
        if not recipes:
            await update.message.reply_text(
                "📚 У тебя пока нет рецептов. Добавь первый! ➕",
                reply_markup=ReplyKeyboardMarkup([
                    [KeyboardButton("🥚 Быстрые (до 30 мин)")],
                    [KeyboardButton("⏲️ Средние (30-60 мин)")],
                    [KeyboardButton("🔥 Сложные (более 1 часа)")],
                    [KeyboardButton("📚 Все рецепты")],
                    [KeyboardButton("➕ Добавить рецепт")],
                    [KeyboardButton("🔍 Поиск")],
                    [KeyboardButton("🔙 Назад в меню")]
                ], resize_keyboard=True)
            )
        else:
            await show_recipes_list(update, context, recipes, "all")
        return UserState.RECIPES_MENU
    
    elif text == "➕ Добавить рецепт":
        UserData.init_recipe(context)
        await update.message.reply_text(
            "🍳 ДОБАВЛЕНИЕ РЕЦЕПТА\n\n"
            "Шаг 1 из 7: Отправь название блюда:",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.ADD_RECIPE_NAME
    
    elif text == "🔍 Поиск":
        await update.message.reply_text(
            "🔍 Введи название блюда для поиска:",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.SEARCH_RECIPE
    
    elif text == "🔙 Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    else:
        await update.message.reply_text(
            "Используй кнопки меню 👆",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("🥚 Быстрые (до 30 мин)")],
                [KeyboardButton("⏲️ Средние (30-60 мин)")],
                [KeyboardButton("🔥 Сложные (более 1 часа)")],
                [KeyboardButton("📚 Все рецепты")],
                [KeyboardButton("➕ Добавить рецепт")],
                [KeyboardButton("🔍 Поиск")],
                [KeyboardButton("🔙 Назад в меню")]
            ], resize_keyboard=True)
        )
        return UserState.RECIPES_MENU

async def handle_recipe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data.startswith("price_"):
        parts = data.split('_')
        price_category = parts[1]
        time_category = parts[2]
        
        recipes = db.filter_recipes(user_id, time_category=time_category, price_category=price_category)
        
        if not recipes:
            await query.edit_message_text(
                f"❌ Рецепты не найдены в этой категории.\nПопробуй другие фильтры.",
                reply_markup=None
            )
        else:
            await show_recipes_list(query, context, recipes, f"{time_category}_{price_category}")
    
    elif data.startswith("recipe_"):
        recipe_id = int(data.split('_')[1])
        recipe = db.get_recipe(recipe_id)
        
        if recipe:
            await show_recipe_card(query, context, recipe)
    
    elif data.startswith("increase_portions_"):
        recipe_id = int(data.split('_')[2])
        current_portions = context.user_data.get('current_portions', 4)
        context.user_data['current_portions'] = current_portions + 1
        recipe = db.get_recipe(recipe_id)
        if recipe:
            await show_recipe_card(query, context, recipe, update=True)
    
    elif data.startswith("decrease_portions_"):
        recipe_id = int(data.split('_')[2])
        current_portions = context.user_data.get('current_portions', 4)
        if current_portions > 1:
            context.user_data['current_portions'] = current_portions - 1
            recipe = db.get_recipe(recipe_id)
            if recipe:
                await show_recipe_card(query, context, recipe, update=True)
    
    elif data.startswith("add_to_plan_"):
        recipe_id = int(data.split('_')[3])
        await query.edit_message_text(
            f"✅ Рецепт добавлен в план питания!",
            reply_markup=None
        )
    
    elif data.startswith("add_to_shopping_"):
        recipe_id = int(data.split('_')[3])
        await query.edit_message_text(
            f"✅ Ингредиенты добавлены в список покупок!",
            reply_markup=None
        )
    
    elif data.startswith("recipes_page_"):
        parts = data.split('_')
        page = int(parts[2])
        filter_key = context.user_data.get('current_filter', 'all')
        recipes = context.user_data.get('cached_recipes', [])
        await show_recipes_list(query, context, recipes, filter_key, page)
    
    elif data == "back_to_recipes_time":
        await query.edit_message_text(
            "🍳 МОИ РЕЦЕПТЫ\n\n"
            "Выбери категорию по времени приготовления:",
            reply_markup=None
        )
        await query.message.reply_text(
            "Выбери категорию:",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("🥚 Быстрые (до 30 мин)")],
                [KeyboardButton("⏲️ Средние (30-60 мин)")],
                [KeyboardButton("🔥 Сложные (более 1 часа)")],
                [KeyboardButton("📚 Все рецепты")],
                [KeyboardButton("➕ Добавить рецепт")],
                [KeyboardButton("🔍 Поиск")],
                [KeyboardButton("🔙 Назад в меню")]
            ], resize_keyboard=True)
        )
    
    elif data == "back_to_recipes_list":
        filter_key = context.user_data.get('current_filter', 'all')
        recipes = context.user_data.get('cached_recipes', [])
        await show_recipes_list(query, context, recipes, filter_key)

async def show_recipes_list(update, context, recipes, filter_key, page=0):
    items_per_page = 5
    start = page * items_per_page
    end = start + items_per_page
    current_recipes = recipes[start:end]
    total_pages = (len(recipes) + items_per_page - 1) // items_per_page
    
    context.user_data['cached_recipes'] = recipes
    context.user_data['current_filter'] = filter_key
    
    text = f"📚 Найдено рецептов: {len(recipes)}\n\n"
    for i, recipe in enumerate(current_recipes, start=start+1):
        time_emoji = "🥚" if recipe.get('time_category') == 'fast' else "⏲️" if recipe.get('time_category') == 'medium' else "🔥"
        price_emoji = "💚" if recipe.get('price_category') == 'budget' else "💛" if recipe.get('price_category') == 'medium' else "❤️"
        text += f"{i}. {time_emoji} {recipe['name']} {price_emoji}\n"
    
    keyboard = []
    for i, recipe in enumerate(current_recipes):
        keyboard.append([InlineKeyboardButton(
            f"{i+start+1}. {recipe['name']}", 
            callback_data=f"recipe_{recipe['id']}"
        )])
    
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("◀️", callback_data=f"recipes_page_{page-1}"))
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="no_action"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("▶️", callback_data=f"recipes_page_{page+1}"))
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_recipes")])
    
    if hasattr(update, 'edit_message_text'):
        await update.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def show_recipe_card(update, context, recipe, update_message=False):
    portions = context.user_data.get('current_portions', 4)
    original_portions = recipe.get('portions', 4)
    multiplier = portions / original_portions
    
    time_emoji = {
        'fast': '🥚',
        'medium': '⏲️',
        'hard': '🔥'
    }.get(recipe.get('time_category'), '⏱️')
    
    price_emoji = {
        'budget': '💚',
        'medium': '💛',
        'expensive': '❤️'
    }.get(recipe.get('price_category'), '💰')
    
    time_text = {
        'fast': 'Быстрое (до 30 мин)',
        'medium': 'Среднее (30-60 мин)',
        'hard': 'Сложное (более 1 часа)'
    }.get(recipe.get('time_category'), 'Не указано')
    
    price_text = {
        'budget': 'Бюджетный',
        'medium': 'Средний',
        'expensive': 'Дорогой'
    }.get(recipe.get('price_category'), 'Не указано')
    
    text = (
        f"*{recipe['name']}*\n"
        f"{time_emoji} Время: {time_text}\n"
        f"{price_emoji} Цена: {price_text}\n"
        f"🏷️ Теги: {', '.join(recipe.get('tags', ['нет']))}\n\n"
        f"*Ингредиенты (на {portions} порций):*\n"
    )
    
    for ingredient in recipe.get('ingredients', []):
        if isinstance(ingredient, dict):
            name = ingredient.get('ingredient', '')
            quantity = ingredient.get('quantity', 0) * multiplier
            unit = ingredient.get('unit', '')
            text += f"— {name} — {quantity:.1f} {unit}\n"
        else:
            text += f"— {ingredient}\n"
    
    text += f"\n*Приготовление:*\n{recipe.get('steps', 'Нет описания')}"
    
    if hasattr(update, 'edit_message_text') and update_message:
        await update.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=get_recipe_actions_inline(recipe['id'])
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=get_recipe_actions_inline(recipe['id'])
        )

# ======================== ДОБАВЛЕНИЕ РЕЦЕПТА ========================

async def add_recipe_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Вернуться в меню":
        await update.message.reply_text("Главное меню:", reply_markup=get_main_menu_keyboard())
        return UserState.MAIN_MENU
    
    context.user_data['new_recipe']['name'] = update.message.text
    
    await update.message.reply_text(
        "Шаг 2 из 7: Сколько порций получается? (введи число)",
        reply_markup=get_back_to_menu_keyboard()
    )
    return UserState.ADD_RECIPE_PORTIONS

async def add_recipe_portions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        portions = int(update.message.text)
        if portions < 1 or portions > 50:
            raise ValueError
        
        context.user_data['new_recipe']['portions'] = portions
        
        keyboard = [
            [KeyboardButton("🥚 Быстрый (до 30 мин)")],
            [KeyboardButton("⏲️ Средний (30-60 мин)")],
            [KeyboardButton("🔥 Сложный (более 1 часа)")],
            [KeyboardButton("🔙 Вернуться в меню")]
        ]
        
        await update.message.reply_text(
            "Шаг 3 из 7: Выбери категорию по времени:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return UserState.ADD_RECIPE_TIME
    except:
        await update.message.reply_text(
            "❌ Введи корректное число порций (от 1 до 50):",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.ADD_RECIPE_PORTIONS

async def add_recipe_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    time_map = {
        "🥚 Быстрый (до 30 мин)": "fast",
        "⏲️ Средний (30-60 мин)": "medium",
        "🔥 Сложный (более 1 часа)": "hard"
    }
    
    if text in time_map:
        context.user_data['new_recipe']['time_category'] = time_map[text]
        
        keyboard = [
            [KeyboardButton("💰 Бюджетный")],
            [KeyboardButton("💰💰 Средний")],
            [KeyboardButton("💰💰💰 Дорогой")],
            [KeyboardButton("🔙 Вернуться в меню")]
        ]
        
        await update.message.reply_text(
            "Шаг 4 из 7: Выбери ценовую категорию:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return UserState.ADD_RECIPE_PRICE
    else:
        await update.message.reply_text(
            "Пожалуйста, используй кнопки для выбора 👆"
        )
        return UserState.ADD_RECIPE_TIME

async def add_recipe_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    price_map = {
        "💰 Бюджетный": "budget",
        "💰💰 Средний": "medium",
        "💰💰💰 Дорогой": "expensive"
    }
    
    if text in price_map:
        context.user_data['new_recipe']['price_category'] = price_map[text]
        
        await update.message.reply_text(
            "Шаг 5 из 7: Добавь теги через запятую\n"
            "(например: завтрак, диетическое, мясное)\n"
            "Или отправь '-' чтобы пропустить",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.ADD_RECIPE_TAGS
    else:
        await update.message.reply_text(
            "Пожалуйста, используй кнопки для выбора 👆"
        )
        return UserState.ADD_RECIPE_PRICE

async def add_recipe_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "-":
        context.user_data['new_recipe']['tags'] = []
    else:
        tags = [tag.strip() for tag in text.split(',')]
        context.user_data['new_recipe']['tags'] = tags
    
    await update.message.reply_text(
        "Шаг 6 из 7: Отправь список ингредиентов\n"
        "Каждый ингредиент с новой строки\n"
        "Например:\n"
        "Куриное филе — 500 г\n"
        "Яйца — 3 шт\n"
        "Соль — по вкусу",
        reply_markup=get_back_to_menu_keyboard()
    )
    return UserState.ADD_RECIPE_INGREDIENTS

async def add_recipe_ingredients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ingredients = update.message.text.split('\n')
    parsed_ingredients = []
    
    for ingredient in ingredients:
        ingredient = ingredient.strip()
        if ingredient:
            if '—' in ingredient:
                parts = ingredient.split('—')
                name = parts[0].strip()
                rest = parts[1].strip()
                
                match = re.match(r'([\d.]+)\s*([а-яА-Яa-zA-Z]+)', rest)
                if match:
                    quantity = float(match.group(1))
                    unit = match.group(2)
                    parsed_ingredients.append({
                        'ingredient': name,
                        'quantity': quantity,
                        'unit': unit
                    })
                else:
                    parsed_ingredients.append(ingredient)
            else:
                parsed_ingredients.append(ingredient)
    
    context.user_data['new_recipe']['ingredients'] = parsed_ingredients
    
    await update.message.reply_text(
        "Шаг 7 из 7: Опиши шаги приготовления:",
        reply_markup=get_back_to_menu_keyboard()
    )
    return UserState.ADD_RECIPE_STEPS

async def add_recipe_steps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    steps = update.message.text
    user_id = update.effective_user.id
    
    context.user_data['new_recipe']['steps'] = steps
    
    recipe_id = db.add_recipe(user_id, context.user_data['new_recipe'])
    
    await update.message.reply_text(
        f"✅ Рецепт успешно сохранен!\n\n"
        f"Ты можешь найти его в разделе 'Все мои рецепты'",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("🥚 Быстрые (до 30 мин)")],
            [KeyboardButton("⏲️ Средние (30-60 мин)")],
            [KeyboardButton("🔥 Сложные (более 1 часа)")],
            [KeyboardButton("📚 Все рецепты")],
            [KeyboardButton("➕ Добавить рецепт")],
            [KeyboardButton("🔍 Поиск")],
            [KeyboardButton("🔙 Назад в меню")]
        ], resize_keyboard=True)
    )
    
    return UserState.RECIPES_MENU

async def search_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    user_id = update.effective_user.id
    
    if query == "🔙 Вернуться в меню":
        await update.message.reply_text("Главное меню:", reply_markup=get_main_menu_keyboard())
        return UserState.MAIN_MENU
    
    recipes = db.search_recipes(user_id, query)
    
    if not recipes:
        await update.message.reply_text(
            f"❌ Рецепты с названием '{query}' не найдены.\nПопробуй другой запрос.",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("🥚 Быстрые (до 30 мин)")],
                [KeyboardButton("⏲️ Средние (30-60 мин)")],
                [KeyboardButton("🔥 Сложные (более 1 часа)")],
                [KeyboardButton("📚 Все рецепты")],
                [KeyboardButton("➕ Добавить рецепт")],
                [KeyboardButton("🔍 Поиск")],
                [KeyboardButton("🔙 Назад в меню")]
            ], resize_keyboard=True)
        )
    else:
        await show_recipes_list(update, context, recipes, "search")
    
    return UserState.RECIPES_MENU

# ======================== НАПОМИНАЛКИ ========================

async def handle_reminders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню напоминалок"""
    await update.message.reply_text(
        "⏰ УПРАВЛЕНИЕ НАПОМИНАНИЯМИ\n\n"
        "Выбери действие:",
        reply_markup=get_reminders_main_keyboard()
    )
    return UserState.REMINDERS_MENU

async def handle_reminders_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Навигация по меню напоминалок с запросом времени"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "💧 Пить воду":
        await update.message.reply_text(
            "💧 НАПОМИНАНИЕ О ВОДЕ\n\n"
            "В какое время напоминать? (в формате ЧЧ:ММ)\n"
            "Например: 09:00, 14:30, 20:00\n\n"
            "Или выбери готовый вариант:",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("Каждые 2 часа с 09:00 до 21:00")],
                [KeyboardButton("09:00, 12:00, 15:00, 18:00, 21:00")],
                [KeyboardButton("🔙 Назад")]
            ], resize_keyboard=True)
        )
        context.user_data['reminder_type'] = 'water'
        return UserState.ADD_REMINDER_TIME
    
    elif text == "🍎 Поесть":
        await update.message.reply_text(
            "🍎 НАПОМИНАНИЕ О ЕДЕ\n\n"
            "В какое время напоминать о еде? (в формате ЧЧ:ММ)\n"
            "Например: 08:00 (завтрак), 13:00 (обед), 19:00 (ужин)",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("08:00, 13:00, 19:00")],
                [KeyboardButton("09:00, 14:00, 20:00")],
                [KeyboardButton("🔙 Назад")]
            ], resize_keyboard=True)
        )
        context.user_data['reminder_type'] = 'meal'
        return UserState.ADD_REMINDER_TIME
    
    elif text == "🏋️ Тренировка":
        await update.message.reply_text(
            "🏋️ НАПОМИНАНИЕ О ТРЕНИРОВКЕ\n\n"
            "В какое время напоминать о тренировке? (ЧЧ:ММ)",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("18:00")],
                [KeyboardButton("19:30")],
                [KeyboardButton("20:00")],
                [KeyboardButton("🔙 Назад")]
            ], resize_keyboard=True)
        )
        context.user_data['reminder_type'] = 'workout'
        return UserState.ADD_REMINDER_TIME
    
    elif text == "💊 Принять витамины":
        await update.message.reply_text(
            "💊 НАПОМИНАНИЕ О ВИТАМИНАХ\n\n"
            "В какое время напоминать? (ЧЧ:ММ)\n"
            "Рекомендуется утром:",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("08:00")],
                [KeyboardButton("09:00")],
                [KeyboardButton("10:00")],
                [KeyboardButton("🔙 Назад")]
            ], resize_keyboard=True)
        )
        context.user_data['reminder_type'] = 'vitamins'
        return UserState.ADD_REMINDER_TIME
    
    elif text == "🛏️ Проснуться":
        await update.message.reply_text(
            "🛏️ НАПОМИНАНИЕ О ПРОБУЖДЕНИИ\n\n"
            "Во сколько ты просыпаешься? (ЧЧ:ММ)",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("07:00")],
                [KeyboardButton("08:00")],
                [KeyboardButton("09:00")],
                [KeyboardButton("🔙 Назад")]
            ], resize_keyboard=True)
        )
        context.user_data['reminder_type'] = 'wakeup'
        return UserState.ADD_REMINDER_TIME
    
    elif text == "🌙 Лечь спать":
        await update.message.reply_text(
            "🌙 НАПОМИНАНИЕ О СНЕ\n\n"
            "Во сколько ты ложишься спать? (ЧЧ:ММ)",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("22:00")],
                [KeyboardButton("23:00")],
                [KeyboardButton("00:00")],
                [KeyboardButton("🔙 Назад")]
            ], resize_keyboard=True)
        )
        context.user_data['reminder_type'] = 'sleep'
        return UserState.ADD_REMINDER_TIME
    
    elif text == "➕ Создать своё напоминание":
        UserData.init_reminder(context)
        await update.message.reply_text(
            "✨ СОЗДАНИЕ НАПОМИНАНИЯ\n\n"
            "Введи название напоминания\n"
            "(например: 'Полить цветы', 'Позвонить маме')",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.ADD_REMINDER_NAME
    
    elif text == "📋 Мои напоминания":
        await show_my_reminders(update, context)
        return UserState.REMINDERS_MENU
    
    elif text == "❌ Отключить все":
        await disable_all_reminders(update, context)
        return UserState.REMINDERS_MENU
    
    elif text == "🔙 Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    else:
        await update.message.reply_text(
            "Используй кнопки меню 👆",
            reply_markup=get_reminders_main_keyboard()
        )
        return UserState.REMINDERS_MENU

async def add_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода времени для напоминания"""
    time_str = update.message.text
    user_id = update.effective_user.id
    
    if time_str == "🔙 Назад":
        await update.message.reply_text(
            "Выбери действие:",
            reply_markup=get_reminders_main_keyboard()
        )
        return UserState.REMINDERS_MENU
    
    reminder_type = context.user_data.get('reminder_type', 'custom')
    
    if ',' in time_str:
        times = [t.strip() for t in time_str.split(',')]
        valid_times = []
        
        for t in times:
            try:
                datetime.strptime(t, "%H:%M")
                valid_times.append(t)
            except:
                await update.message.reply_text(
                    f"❌ Неверный формат времени '{t}'. Используй ЧЧ:ММ",
                    reply_markup=get_back_to_menu_keyboard()
                )
                return UserState.ADD_REMINDER_TIME
        
        name_map = {
            'water': '💧 Пить воду',
            'meal': '🍎 Поесть',
            'workout': '🏋️ Тренировка',
            'vitamins': '💊 Принять витамины',
            'wakeup': '🛏️ Проснуться',
            'sleep': '🌙 Лечь спать',
            'custom': context.user_data.get('new_reminder', {}).get('name', 'Напоминание')
        }
        
        name = name_map.get(reminder_type, 'Напоминание')
        
        for t in valid_times:
            reminder_data = {
                'name': f"{name} в {t}",
                'periodicity': 'daily',
                'time': t,
                'active': True,
                'created_at': datetime.now().isoformat()
            }
            db.add_reminder(user_id, reminder_data)
        
        await update.message.reply_text(
            f"✅ Создано {len(valid_times)} напоминаний!\n"
            f"Времена: {', '.join(valid_times)}",
            reply_markup=get_reminders_main_keyboard()
        )
        return UserState.REMINDERS_MENU
    
    if time_str == "Каждые 2 часа с 09:00 до 21:00":
        times = [f"{h:02d}:00" for h in range(9, 22, 2)]
        name = "💧 Пить воду"
        
        for t in times:
            reminder_data = {
                'name': f"{name} в {t}",
                'periodicity': 'daily',
                'time': t,
                'active': True,
                'created_at': datetime.now().isoformat()
            }
            db.add_reminder(user_id, reminder_data)
        
        await update.message.reply_text(
            f"✅ Создано напоминаний о воде!\n"
            f"Времена: {', '.join(times)}",
            reply_markup=get_reminders_main_keyboard()
        )
        return UserState.REMINDERS_MENU
    
    try:
        datetime.strptime(time_str, "%H:%M")
        
        name_map = {
            'water': '💧 Пить воду',
            'meal': '🍎 Поесть',
            'workout': '🏋️ Тренировка',
            'vitamins': '💊 Принять витамины',
            'wakeup': '🛏️ Проснуться',
            'sleep': '🌙 Лечь спать',
            'custom': context.user_data.get('new_reminder', {}).get('name', 'Напоминание')
        }
        
        name = name_map.get(reminder_type, 'Напоминание')
        
        reminder_data = {
            'name': name,
            'periodicity': 'daily',
            'time': time_str,
            'active': True,
            'created_at': datetime.now().isoformat()
        }
        
        reminder_id = db.add_reminder(user_id, reminder_data)
        
        await update.message.reply_text(
            f"✅ Напоминание '{name}' установлено!\n"
            f"📅 Каждый день в {time_str}",
            reply_markup=get_reminders_main_keyboard()
        )
        return UserState.REMINDERS_MENU
        
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат времени. Используй ЧЧ:ММ (например 14:30):",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.ADD_REMINDER_TIME

async def add_reminder_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Вернуться в меню":
        await update.message.reply_text("Главное меню:", reply_markup=get_main_menu_keyboard())
        return UserState.MAIN_MENU
    
    context.user_data['new_reminder']['name'] = update.message.text
    
    await update.message.reply_text(
        "Выбери периодичность:",
        reply_markup=get_reminder_periodicity_keyboard()
    )
    return UserState.ADD_REMINDER_PERIODICITY

async def add_reminder_periodicity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    periodicity_map = {
        "Каждый день": "daily",
        "Раз в несколько часов": "interval",
        "По дням недели": "weekly",
        "Один раз": "once"
    }
    
    if text in periodicity_map:
        context.user_data['new_reminder']['periodicity'] = periodicity_map[text]
        
        if text == "Каждый день":
            await update.message.reply_text(
                "В какое время отправлять?\n"
                "(отправь в формате ЧЧ:ММ, например 14:30)",
                reply_markup=get_back_to_menu_keyboard()
            )
            return UserState.ADD_REMINDER_TIME
        elif text == "Раз в несколько часов":
            await update.message.reply_text(
                "Введи интервал (в часах):",
                reply_markup=get_back_to_menu_keyboard()
            )
            return UserState.ADD_REMINDER_INTERVAL
        elif text == "По дням недели":
            await update.message.reply_text(
                "Выбери дни недели:",
                reply_markup=get_weekdays_inline()
            )
            return UserState.ADD_REMINDER_WEEKDAYS
        elif text == "Один раз":
            await update.message.reply_text(
                "Введи дату и время в формате:\n"
                "ДД.ММ.ГГГГ ЧЧ:ММ\n"
                "Например: 25.12.2026 19:00",
                reply_markup=get_back_to_menu_keyboard()
            )
            return UserState.ADD_REMINDER_DATETIME
    else:
        await update.message.reply_text(
            "Пожалуйста, используй кнопки для выбора 👆",
            reply_markup=get_reminder_periodicity_keyboard()
        )
        return UserState.ADD_REMINDER_PERIODICITY

async def add_reminder_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        interval = int(update.message.text)
        if interval < 1 or interval > 24:
            raise ValueError
        
        context.user_data['new_reminder']['interval'] = interval
        
        await update.message.reply_text(
            "С какого времени начать? (ЧЧ:ММ):",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.ADD_REMINDER_START_TIME
    except ValueError:
        await update.message.reply_text(
            "❌ Введи корректное число часов (от 1 до 24):",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.ADD_REMINDER_INTERVAL

async def add_reminder_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        time_str = update.message.text
        datetime.strptime(time_str, "%H:%M")
        
        context.user_data['new_reminder']['time'] = time_str
        
        user_id = update.effective_user.id
        reminder_id = db.add_reminder(user_id, context.user_data['new_reminder'])
        
        interval = context.user_data['new_reminder']['interval']
        await update.message.reply_text(
            f"✅ Напоминание '{context.user_data['new_reminder']['name']}' установлено!\n"
            f"📅 Каждые {interval} часа(ов) начиная с {time_str}",
            reply_markup=get_reminders_main_keyboard()
        )
        return UserState.REMINDERS_MENU
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат времени. Используй ЧЧ:ММ:",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.ADD_REMINDER_START_TIME

async def handle_weekday_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "weekday_done":
        weekdays = context.user_data.get('selected_weekdays', [])
        if not weekdays:
            await query.edit_message_text(
                "❌ Выбери хотя бы один день недели!",
                reply_markup=get_weekdays_inline()
            )
            return
        
        context.user_data['new_reminder']['weekdays'] = weekdays
        await query.edit_message_text(
            "В какое время отправлять? (ЧЧ:ММ):",
            reply_markup=None
        )
        return UserState.ADD_REMINDER_TIME
    
    day_map = {
        "weekday_mon": "ПН", "weekday_tue": "ВТ", "weekday_wed": "СР",
        "weekday_thu": "ЧТ", "weekday_fri": "ПТ", "weekday_sat": "СБ", "weekday_sun": "ВС"
    }
    
    if data in day_map:
        selected = context.user_data.get('selected_weekdays', [])
        day = day_map[data]
        
        if day in selected:
            selected.remove(day)
        else:
            selected.append(day)
        
        context.user_data['selected_weekdays'] = selected
        
        await query.edit_message_text(
            f"Выбери дни недели (выбрано: {', '.join(selected) if selected else 'нет'}):",
            reply_markup=get_weekdays_inline()
        )

async def add_reminder_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        datetime_str = update.message.text
        reminder_dt = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M")
        
        if reminder_dt < datetime.now():
            await update.message.reply_text(
                "❌ Дата и время должны быть в будущем!",
                reply_markup=get_back_to_menu_keyboard()
            )
            return UserState.ADD_REMINDER_DATETIME
        
        context.user_data['new_reminder']['datetime'] = reminder_dt.isoformat()
        
        user_id = update.effective_user.id
        reminder_id = db.add_reminder(user_id, context.user_data['new_reminder'])
        
        await update.message.reply_text(
            f"✅ Напоминание '{context.user_data['new_reminder']['name']}' установлено!\n"
            f"📅 {reminder_dt.strftime('%d.%m.%Y в %H:%M')}",
            reply_markup=get_reminders_main_keyboard()
        )
        return UserState.REMINDERS_MENU
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат. Используй ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 25.12.2026 19:00",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.ADD_REMINDER_DATETIME

async def show_my_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminders = db.get_user_reminders(user_id)
    
    if not reminders:
        await update.message.reply_text(
            "📋 У тебя пока нет активных напоминаний.\n"
            "Создай первое! ➕",
            reply_markup=get_reminders_main_keyboard()
        )
        return
    
    text = "📋 ТВОИ НАПОМИНАНИЯ:\n\n"
    
    for i, reminder in enumerate(reminders, 1):
        name = reminder.get('name', 'Без названия')
        periodicity = reminder.get('periodicity', 'unknown')
        
        if periodicity == 'daily':
            schedule = f"ежедневно в {reminder.get('time', '??:??')}"
        elif periodicity == 'interval':
            schedule = f"каждые {reminder.get('interval', '?')} ч с {reminder.get('time', '??:??')}"
        elif periodicity == 'weekly':
            days = ', '.join(reminder.get('weekdays', []))
            schedule = f"{days} в {reminder.get('time', '??:??')}"
        elif periodicity == 'once':
            dt = datetime.fromisoformat(reminder.get('datetime', datetime.now().isoformat()))
            schedule = dt.strftime('%d.%m.%Y %H:%M')
        else:
            schedule = "неизвестно"
        
        text += f"{i}. {name} ({schedule})\n"
    
    text += "\nВыбери напоминание для управления:"
    
    keyboard = []
    for i, reminder in enumerate(reminders, 1):
        keyboard.append([InlineKeyboardButton(
            f"{i}. {reminder.get('name', 'Без названия')}",
            callback_data=f"reminder_select_{reminder['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_reminders_menu")])
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка инлайн кнопок напоминаний с поддержкой редактирования"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data.startswith("reminder_select_"):
        reminder_id = int(data.split('_')[2])
        reminder = None
        
        data_db = db._load_data()
        if 'reminders' in data_db and str(user_id) in data_db['reminders']:
            reminder = data_db['reminders'][str(user_id)].get(str(reminder_id))
        
        if reminder:
            context.user_data['current_reminder_id'] = reminder_id
            
            status = "✅ Активно" if reminder.get('active', True) else "❌ Отключено"
            if 'paused_until' in reminder:
                paused_until = datetime.fromisoformat(reminder['paused_until'])
                if paused_until > datetime.now():
                    status = f"⏸️ На паузе до {paused_until.strftime('%d.%m.%Y')}"
            
            await query.edit_message_text(
                f"📋 НАПОМИНАНИЕ:\n\n"
                f"📝 Название: {reminder.get('name')}\n"
                f"⏱️ Периодичность: {reminder.get('periodicity')}\n"
                f"⏰ Время: {reminder.get('time', reminder.get('datetime', 'не указано'))}\n"
                f"📊 Статус: {status}\n\n"
                f"Выбери действие:",
                reply_markup=get_reminder_actions_inline(reminder_id)
            )
    
    elif data.startswith("reminder_delete_"):
        reminder_id = int(data.split('_')[2])
        db.delete_reminder(user_id, reminder_id)
        await query.edit_message_text(
            "✅ Напоминание удалено!",
            reply_markup=None
        )
        await show_my_reminders(update, context)
    
    elif data.startswith("reminder_pause_"):
        reminder_id = int(data.split('_')[2])
        await query.edit_message_text(
            "⏸️ Выбери период паузы:",
            reply_markup=get_pause_options_inline(reminder_id)
        )
    
    elif data.startswith("pause_"):
        parts = data.split('_')
        days = int(parts[1][:-1])
        if 'w' in parts[1]:
            days = days * 7
        elif 'm' in parts[1]:
            days = days * 30
        
        reminder_id = int(parts[2])
        db.pause_reminder(user_id, reminder_id, days)
        
        await query.edit_message_text(
            f"✅ Напоминание приостановлено на {days} дней",
            reply_markup=None
        )
        await show_my_reminders(update, context)
    
    elif data.startswith("reminder_edit_"):
        reminder_id = int(data.split('_')[2])
        context.user_data['editing_reminder_id'] = reminder_id
        
        keyboard = [
            [InlineKeyboardButton("📝 Название", callback_data=f"edit_name_{reminder_id}")],
            [InlineKeyboardButton("⏱️ Периодичность", callback_data=f"edit_period_{reminder_id}")],
            [InlineKeyboardButton("⏰ Время", callback_data=f"edit_time_{reminder_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_reminder_{reminder_id}")]
        ]
        
        await query.edit_message_text(
            "✏️ РЕДАКТИРОВАНИЕ\n\nЧто ты хочешь изменить?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("edit_name_"):
        reminder_id = int(data.split('_')[2])
        context.user_data['editing_reminder_id'] = reminder_id
        context.user_data['edit_action'] = 'name'
        
        await query.edit_message_text(
            "✏️ Введи новое название для напоминания:",
            reply_markup=None
        )
    
    elif data.startswith("edit_time_"):
        reminder_id = int(data.split('_')[2])
        context.user_data['editing_reminder_id'] = reminder_id
        context.user_data['edit_action'] = 'time'
        
        await query.edit_message_text(
            "✏️ Введи новое время в формате ЧЧ:ММ (например 14:30):",
            reply_markup=None
        )
    
    elif data.startswith("reminder_disable_"):
        reminder_id = int(data.split('_')[2])
        db.update_reminder(user_id, reminder_id, active=False)
        await query.edit_message_text(
            "🔕 Напоминание отключено!",
            reply_markup=None
        )
        await show_my_reminders(update, context)
    
    elif data.startswith("reminder_enable_"):
        reminder_id = int(data.split('_')[2])
        db.update_reminder(user_id, reminder_id, active=True)
        if 'paused_until' in db.get_user_reminders(user_id)[0]:
            db.update_reminder(user_id, reminder_id, paused_until=None)
        await query.edit_message_text(
            "✅ Напоминание включено!",
            reply_markup=None
        )
        await show_my_reminders(update, context)
    
    elif data.startswith("back_to_reminder_"):
        reminder_id = int(data.split('_')[3])
        data_db = db._load_data()
        if 'reminders' in data_db and str(user_id) in data_db['reminders']:
            reminder = data_db['reminders'][str(user_id)].get(str(reminder_id))
            if reminder:
                await query.edit_message_text(
                    f"📋 НАПОМИНАНИЕ:\n\n"
                    f"📝 Название: {reminder.get('name')}\n"
                    f"⏱️ Периодичность: {reminder.get('periodicity')}\n"
                    f"⏰ Время: {reminder.get('time', reminder.get('datetime', 'не указано'))}\n\n"
                    f"Выбери действие:",
                    reply_markup=get_reminder_actions_inline(reminder_id)
                )
    
    elif data == "back_to_reminders_menu":
        await query.edit_message_text(
            "⏰ УПРАВЛЕНИЕ НАПОМИНАНИЯМИ",
            reply_markup=None
        )
        await query.message.reply_text(
            "Выбери действие:",
            reply_markup=get_reminders_main_keyboard()
        )

async def disable_all_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminders = db.get_user_reminders(user_id)
    
    for reminder in reminders:
        db.update_reminder(user_id, int(reminder['id']), active=False)
    
    await update.message.reply_text(
        "❌ Все напоминания отключены!",
        reply_markup=get_reminders_main_keyboard()
    )

# ======================== ВЗВЕШИВАНИЕ ========================

async def setup_weighing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚖️ НАСТРОЙКА ВЗВЕШИВАНИЯ\n\n"
        "Хочешь, чтобы я напоминал взвешиваться раз в неделю?\n\n"
        "Выбери удобный день:",
        reply_markup=get_weighing_days_keyboard()
    )
    return UserState.WEIGHING_SETUP_DAY

async def handle_weighing_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# ======================== СПИСОК ПОКУПОК ========================

async def handle_shopping_list_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛒 СПИСОК ПОКУПОК\n\n"
        "Выбери действие:",
        reply_markup=get_shopping_list_keyboard()
    )
    return UserState.SHOPPING_LIST_MENU

async def handle_shopping_list_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действия со списком покупок"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "📝 Собрать список на неделю":
        active_plan = db.get_active_meal_plan(user_id)
        
        if not active_plan:
            await update.message.reply_text(
                "❌ Сначала создай план питания в разделе 'План на неделю'!",
                reply_markup=get_shopping_list_keyboard()
            )
            return UserState.SHOPPING_LIST_MENU
        
        user_recipes = db.get_user_recipes(user_id)
        
        if not user_recipes:
            shopping_list = generate_shopping_list_ai(active_plan.get('plan', {}))
        else:
            shopping_list = generate_shopping_list_ai(active_plan.get('plan', {}))
        
        db.save_shopping_list(user_id, shopping_list)
        
        list_text = "🛒 ТВОЙ СПИСОК ПОКУПОК НА НЕДЕЛЮ:\n\n"
        for item in shopping_list.get('items', []):
            list_text += f"• {item['name']} — {item['quantity']}\n"
        
        await update.message.reply_text(list_text, reply_markup=get_shopping_list_keyboard())
    
    elif text == "📋 Разделить по рецептам":
        shopping_list = db.get_shopping_list(user_id)
        active_plan = db.get_active_meal_plan(user_id)
        
        if not shopping_list or not active_plan:
            await update.message.reply_text(
                "❌ Сначала создай список покупок!",
                reply_markup=get_shopping_list_keyboard()
            )
            return UserState.SHOPPING_LIST_MENU
        
        text = "📋 СПИСОК ПО РЕЦЕПТАМ:\n\n"
        
        for day, meals in active_plan.get('plan', {}).items():
            text += f"📅 {day}:\n"
            text += f"  🍳 {meals.get('завтрак', '-')}\n"
            text += f"  🍲 {meals.get('обед', '-')}\n"
            text += f"  🍽️ {meals.get('ужин', '-')}\n"
            text += f"  🥗 {meals.get('перекус', '-')}\n\n"
        
        await update.message.reply_text(
            text,
            reply_markup=get_shopping_list_keyboard()
        )
    
    elif text == "🗑️ Очистить список":
        db.clear_shopping_list(user_id)
        await update.message.reply_text(
            "✅ Список покупок очищен!",
            reply_markup=get_shopping_list_keyboard()
        )
    elif text == "🔙 Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    return UserState.SHOPPING_LIST_MENU

# ======================== СИСТЕМА НАПОМИНАНИЙ ========================

async def reminder_check(context: ContextTypes.DEFAULT_TYPE):
    """Проверка и отправка напоминаний (запускается каждую минуту)"""
    current_time = datetime.now()
    current_time_str = current_time.strftime("%H:%M")
    
    weekday_map = {
        'Monday': 'ПН', 'Tuesday': 'ВТ', 'Wednesday': 'СР',
        'Thursday': 'ЧТ', 'Friday': 'ПТ', 'Saturday': 'СБ', 'Sunday': 'ВС'
    }
    current_weekday_ru = weekday_map.get(current_time.strftime("%A"), '')
    
    data = db._load_data()
    
    if 'reminders' not in data:
        return
    
    for user_id_str, user_reminders in data['reminders'].items():
        user_id = int(user_id_str)
        
        for reminder_id, reminder in user_reminders.items():
            if not reminder.get('active', True):
                continue
            
            if 'paused_until' in reminder:
                paused_until = datetime.fromisoformat(reminder['paused_until'])
                if current_time < paused_until:
                    continue
            
            periodicity = reminder.get('periodicity')
            
            if periodicity == 'daily' or periodicity == 'Каждый день':
                if reminder.get('time') == current_time_str:
                    await send_reminder(context.bot, user_id, reminder)
            
            elif periodicity == 'interval' or periodicity == 'Раз в несколько часов':
                if 'last_sent' in reminder:
                    last_sent = datetime.fromisoformat(reminder['last_sent'])
                    interval = reminder.get('interval', 1)
                    if (current_time - last_sent).total_seconds() >= interval * 3600:
                        if reminder.get('time'):
                            start_time = datetime.strptime(reminder['time'], "%H:%M").time()
                            if current_time.time() >= start_time:
                                await send_reminder(context.bot, user_id, reminder)
                                reminder['last_sent'] = current_time.isoformat()
                                db.update_reminder(user_id, int(reminder_id), last_sent=current_time.isoformat())
                else:
                    if reminder.get('time'):
                        start_time = datetime.strptime(reminder['time'], "%H:%M").time()
                        if current_time.time() >= start_time:
                            await send_reminder(context.bot, user_id, reminder)
                            reminder['last_sent'] = current_time.isoformat()
                            db.update_reminder(user_id, int(reminder_id), last_sent=current_time.isoformat())
            
            elif periodicity == 'weekly' or periodicity == 'По дням недели':
                weekdays = reminder.get('weekdays', [])
                if current_weekday_ru in weekdays and reminder.get('time') == current_time_str:
                    await send_reminder(context.bot, user_id, reminder)
            
            elif periodicity == 'once' or periodicity == 'Один раз':
                if 'datetime' in reminder:
                    reminder_dt = datetime.fromisoformat(reminder['datetime'])
                    if (reminder_dt.year == current_time.year and
                        reminder_dt.month == current_time.month and
                        reminder_dt.day == current_time.day and
                        reminder_dt.hour == current_time.hour and
                        reminder_dt.minute == current_time.minute):
                        await send_reminder(context.bot, user_id, reminder)
                        db.update_reminder(user_id, int(reminder_id), active=False)

async def send_reminder(bot, user_id: int, reminder: dict):
    """Отправка напоминания пользователю"""
    name = reminder.get('name', 'Напоминание')
    
    if "💧" in name or "вода" in name.lower():
        text = "💧 ПОРА ПИТЬ ВОДУ!\nНапоминаю тебе выпить стакан воды 💧"
    elif "🍎" in name or "есть" in name.lower():
        text = "🍎 ВРЕМЯ ПОЕСТЬ!\nНе забывай о правильном питании 🍎"
    elif "🏋️" in name or "тренировка" in name.lower():
        text = "🏋️ ВРЕМЯ ТРЕНИРОВКИ!\nПора заняться собой 💪"
    elif "💊" in name or "витамины" in name.lower():
        text = "💊 НАПОМИНАНИЕ!\nПрими витамины 💊"
    else:
        text = f"⏰ НАПОМИНАНИЕ!\n{name}"
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=get_main_menu_keyboard()
        )
        print(f"✅ Напоминание отправлено пользователю {user_id}: {name}")
    except Exception as e:
        print(f"❌ Ошибка отправки напоминания: {e}")

async def setup_reminder_jobs(application):
    """Настройка периодических задач для напоминаний"""
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(reminder_check, interval=60, first=10)
        print("✅ Планировщик напоминаний запущен (проверка каждую минуту)")
    else:
        print("⚠️ Job queue не доступен, напоминания не будут работать")

async def test_reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда для проверки напоминалок"""
    await update.message.reply_text(
        "⏰ ТЕСТ НАПОМИНАЛОК\n\n"
        "✅ Система напоминаний активна\n"
        "⏱️ Проверка происходит каждую минуту\n\n"
        "Текущее время: " + datetime.now().strftime("%H:%M:%S"),
        reply_markup=get_reminders_main_keyboard()
    )

# ======================== ОБЩИЕ ОБРАБОТЧИКИ ========================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Действие отменено. Возвращаюсь в главное меню.",
        reply_markup=get_main_menu_keyboard()
    )
    return UserState.MAIN_MENU

async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я не понимаю эту команду. Используй меню для навигации 👆",
        reply_markup=get_main_menu_keyboard()
    )

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
            UserState.REGISTRATION_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            UserState.REGISTRATION_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gender)],
            UserState.REGISTRATION_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age)],
            UserState.REGISTRATION_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weight)],
            UserState.REGISTRATION_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_height)],
            UserState.REGISTRATION_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_goal)],
            UserState.REGISTRATION_CONFIRM: [CallbackQueryHandler(handle_confirmation, pattern="^(confirm_yes|confirm_no)$")],
            UserState.MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)],
            UserState.EDIT_PROFILE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_profile)],
            UserState.EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
            UserState.EDIT_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_gender)],
            UserState.EDIT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_age)],
            UserState.EDIT_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_weight)],
            UserState.EDIT_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_height)],
            UserState.EDIT_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_goal)],
            UserState.AWAITING_BUDGET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_budget),
                MessageHandler(filters.Regex('^(📝 Создать план|🔙 Вернуться в меню)$'), handle_create_plan)
            ],
            UserState.RECIPES_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_recipes_navigation)],
            UserState.ADD_RECIPE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_name)],
            UserState.ADD_RECIPE_PORTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_portions)],
            UserState.ADD_RECIPE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_time)],
            UserState.ADD_RECIPE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_price)],
            UserState.ADD_RECIPE_TAGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_tags)],
            UserState.ADD_RECIPE_INGREDIENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_ingredients)],
            UserState.ADD_RECIPE_STEPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipe_steps)],
            UserState.SEARCH_RECIPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_recipe)],
            UserState.REMINDERS_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reminders_navigation)],
            UserState.ADD_REMINDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_name)],
            UserState.ADD_REMINDER_PERIODICITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_periodicity)],
            UserState.ADD_REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_time)],
            UserState.ADD_REMINDER_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_interval)],
            UserState.ADD_REMINDER_START_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_start_time)],
            UserState.ADD_REMINDER_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_datetime)],
            UserState.WEIGHING_SETUP_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weighing_day)],
            UserState.WEIGHING_SETUP_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weighing_time)],
            UserState.WEIGHING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weighing_input)],
            UserState.SHOPPING_LIST_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_shopping_list_actions)],
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
    print("📋 Все функции загружены:")
    print("  ✅ Регистрация и профиль")
    print("  ✅ План питания на неделю")
    print("  ✅ Рецепты с фильтрацией")
    print("  ✅ Список покупок")
    print("  ✅ Напоминалки (с редактированием)")
    print("  ✅ Еженедельное взвешивание")
    print("="*40)
    
    application.run_polling(
        drop_pending_updates=True,
        poll_interval=1.0,
        timeout=30
    )

if __name__ == '__main__':
    main()
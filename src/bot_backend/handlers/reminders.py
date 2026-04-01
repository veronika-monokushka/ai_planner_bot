"""Обработчики напоминаний"""

import logging
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ИСПРАВЛЕНО: убрал ai_planner_bot.
from bot_backend.states import UserState, UserData
from bot_backend.keyboards import (
    get_back_to_menu_keyboard, get_main_menu_keyboard, get_reminders_main_keyboard,
    get_reminder_periodicity_keyboard, get_weekdays_inline, get_reminder_actions_inline,
    get_pause_options_inline
)
from database import db

logger = logging.getLogger(__name__)


async def handle_reminders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню напоминалок"""
    await update.message.reply_text(
        "⏰ УПРАВЛЕНИЕ НАПОМИНАНИЯМИ\n\n"
        "Выбери действие:",
        reply_markup=get_reminders_main_keyboard()
    )
    return UserState.REMINDERS_MENU


async def handle_reminders_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Навигация по меню напоминалок"""
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
    """Добавление названия напоминания"""
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
    """Выбор периодичности напоминания"""
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
    """Добавление интервала для напоминания"""
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
    """Добавление времени старта для интервального напоминания"""
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
    """Обработка выбора дней недели"""
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
    """Добавление даты и времени для одноразового напоминания"""
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
    """Показывает список напоминаний пользователя"""
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
    """Обработка инлайн кнопок напоминаний"""
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
    """Отключение всех напоминаний"""
    user_id = update.effective_user.id
    reminders = db.get_user_reminders(user_id)
    
    for reminder in reminders:
        db.update_reminder(user_id, int(reminder['id']), active=False)
    
    await update.message.reply_text(
        "❌ Все напоминания отключены!",
        reply_markup=get_reminders_main_keyboard()
    )


async def test_reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда для проверки напоминалок"""
    await update.message.reply_text(
        "⏰ ТЕСТ НАПОМИНАЛОК\n\n"
        "✅ Система напоминаний активна\n"
        "⏱️ Проверка происходит каждую минуту\n\n"
        "Текущее время: " + datetime.now().strftime("%H:%M:%S"),
        reply_markup=get_reminders_main_keyboard()
    )


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
# ai_agent/tools.py
"""Инструменты для LLM агента"""

from langchain_core.tools import tool
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
import sys
import os
import re

# Добавляем путь к проекту для импорта БД
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db as main_db


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def _parse_time(time_str: str) -> Optional[str]:
    """
    Парсит время из строки.
    Примеры: "15:30", "15-30", "в 3 часа дня"
    """
    # Простой формат HH:MM
    match = re.search(r'(\d{1,2})[:.-](\d{2})', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    
    # "в 3 часа дня" → 15:00
    match = re.search(r'в (\d{1,2})\s*час', time_str)
    if match:
        hour = int(match.group(1))
        if 'дня' in time_str or 'вечера' in time_str:
            hour += 12 if hour < 12 else 0
        return f"{hour:02d}:00"
    
    return None


def _parse_datetime(datetime_str: str) -> Optional[datetime]:
    """
    Парсит дату и время из строки.
    Примеры: "сегодня в 15:30", "завтра в 10:00", "2024-12-25 15:30", "завтра 19:00"
    """
    now = datetime.now()
    
    # Конкретная дата: YYYY-MM-DD HH:MM
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})', datetime_str)
    if match:
        return datetime(
            int(match.group(1)), int(match.group(2)), int(match.group(3)),
            int(match.group(4)), int(match.group(5))
        )
    
    # "сегодня в HH:MM" или "сегодня HH:MM"
    if 'сегодня' in datetime_str:
        time = _parse_time(datetime_str)
        if time:
            hour, minute = map(int, time.split(':'))
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # "завтра в HH:MM" или "завтра HH:MM"
    if 'завтра' in datetime_str:
        time = _parse_time(datetime_str)
        if time:
            hour, minute = map(int, time.split(':'))
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Просто время (считаем сегодня)
    time = _parse_time(datetime_str)
    if time:
        hour, minute = map(int, time.split(':'))
        result = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if result < now:
            result += timedelta(days=1)
        return result
    
    return None


def _get_weekday_ru(dt: datetime) -> str:
    """Возвращает название дня недели на русском"""
    weekday_map = {
        'Monday': 'ПН', 'Tuesday': 'ВТ', 'Wednesday': 'СР',
        'Thursday': 'ЧТ', 'Friday': 'ПТ', 'Saturday': 'СБ', 'Sunday': 'ВС'
    }
    return weekday_map.get(dt.strftime("%A"), '')


# ==================== ИНСТРУМЕНТЫ ДЛЯ LLM ====================

@tool
def create_reminder(
    user_id: int,
    text: str,
    remind_at: str,
    repeat_type: str = "once"
) -> str:
    """
    Создает новое напоминание и сохраняет в БД.
    
    Args:
        user_id: ID пользователя в Telegram
        text: Текст напоминания (например, "Выпить воду")
        remind_at: Время срабатывания (формат: "15:30", "сегодня в 15:30", "завтра в 10:00")
        repeat_type: Тип повторения: "once", "daily", "weekly"
    
    Returns:
        Сообщение о результате создания напоминания
    """
    try:
        reminder_datetime = None
        reminder_time = None
        
        if repeat_type == "once":
            # Парсим дату и время
            reminder_datetime = _parse_datetime(remind_at)
            if not reminder_datetime:
                return f"❌ Не удалось распознать дату и время. Используйте формат: 'сегодня в 15:30' или 'завтра в 10:00'"
            
            if reminder_datetime < datetime.now():
                return "❌ Дата и время должны быть в будущем!"
        
        elif repeat_type in ["daily", "weekly"]:
            # Парсим только время
            reminder_time = _parse_time(remind_at)
            if not reminder_time:
                return f"❌ Не удалось распознать время. Используйте формат: '15:30'"
        
        else:
            return f"❌ Неизвестный тип повторения: {repeat_type}. Используйте once, daily или weekly"
        
        # Формируем данные для БД
        reminder_data = {
            "name": text,
            "periodicity": repeat_type,
            "active": True,
            "created_at": datetime.now().isoformat()
        }
        
        if repeat_type == "once" and reminder_datetime:
            reminder_data["datetime"] = reminder_datetime.isoformat()
        elif repeat_type in ["daily", "weekly"] and reminder_time:
            reminder_data["time"] = reminder_time
        
        # Сохраняем в БД
        reminder_id = main_db.reminders.add_reminder(user_id, reminder_data)
        
        # Формируем ответ
        if repeat_type == "once":
            time_str = reminder_datetime.strftime('%d.%m.%Y в %H:%M')
            return f"✅ Напоминание '{text}' создано!\n Однократное на {time_str}"
        elif repeat_type == "daily":
            return f"✅ Напоминание '{text}' создано!\n Ежедневное в {reminder_time}"
        else:  # weekly
            return f"✅ Напоминание '{text}' создано!\n Еженедельное в {reminder_time}"
        
    except Exception as e:
        return f"❌ Ошибка при создании напоминания: {str(e)}"


@tool
def get_reminders(
    user_id: int,
    reminder_id: Optional[int] = None,
    is_active: Optional[bool] = None
) -> str:
    """
    Получает список напоминаний пользователя из БД.
    
    Args:
        user_id: ID пользователя в Telegram
        reminder_id: ID конкретного напоминания (опционально)
        is_active: Фильтр по активности (True/False)
    
    Returns:
        Список напоминаний в читаемом формате
    """
    try:
        if reminder_id:
            reminder = main_db.reminders.get_reminder_by_id(user_id, reminder_id)
            reminders = [reminder] if reminder else []
        else:
            if is_active is False:
                reminders = main_db.reminders.get_all_reminders(user_id)
            else:
                reminders = main_db.reminders.get_reminders(user_id)
        
        if not reminders:
            return "📭 У вас нет активных напоминаний."
        
        result = "📋 ВАШИ НАПОМИНАНИЯ:\n\n"
        for r in reminders:
            status = "" if r.get('active', True) else "⏸️ "
            
            # Форматируем время
            time_str = ""
            if 'datetime' in r:
                dt = datetime.fromisoformat(r['datetime'])
                time_str = f"📅 {dt.strftime('%d.%m.%Y %H:%M')}"
            elif 'time' in r:
                time_str = f"⏰ {r['time']}"
            
            period = r.get('periodicity', 'once')
            period_text = {
                'once': 'однократное',
                'daily': 'ежедневное',
                'weekly': 'еженедельное'
            }.get(period, period)
            
            result += f"{status}{r.get('name', 'Без названия')}\n"
            result += f"   {time_str} | {period_text}\n\n"
        
        return result
        
    except Exception as e:
        return f"❌ Ошибка при получении напоминаний: {str(e)}"


@tool
def delete_reminder(
    user_id: int,
    reminder_id: int
) -> str:
    """
    Удаляет напоминание из БД.
    
    Args:
        user_id: ID пользователя в Telegram
        reminder_id: ID напоминания для удаления
    
    Returns:
        Сообщение о результате удаления
    """
    try:
        existing = main_db.reminders.get_reminder_by_id(user_id, reminder_id)
        if not existing:
            return f"❌ Напоминание с ID {reminder_id} не найдено."
        
        text = existing.get('name', '')
        main_db.reminders.delete_reminder(user_id, reminder_id)
        
        return f"✅ Напоминание '{text}' (ID:{reminder_id}) удалено."
        
    except Exception as e:
        return f"❌ Ошибка при удалении напоминания: {str(e)}"


# ==================== СПИСОК ВСЕХ ИНСТРУМЕНТОВ ====================

ALL_TOOLS = [
    create_reminder,
    get_reminders,
    delete_reminder
]


# ==================== ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ TOOL_EXECUTORS ====================

def get_tool_executors():
    """
    Возвращает словарь исполнителей для инструментов.
    Используется в ask_with_tools для автоматической обработки.
    """
    def reminder_executor(tool_call):
        """Выполняет инструмент и возвращает (ответ_пользователю, нужно_ли_вызывать_LLM)"""
        name = tool_call["name"]
        args = tool_call["args"]
        
        if name == "create_reminder":
            result = create_reminder.invoke(args)
            return result, False
        
        elif name == "get_reminders":
            result = get_reminders.invoke(args)
            return result, False
        
        elif name == "delete_reminder":
            result = delete_reminder.invoke(args)
            return result, False
        
        return f"Выполнен инструмент {name}", True
    
    executors = {}
    for tool in ALL_TOOLS:
        executors[tool.name] = reminder_executor
    
    return executors
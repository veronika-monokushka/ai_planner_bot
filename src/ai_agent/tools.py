# ai_agent/tools.py
"""Инструменты для LLM агента"""

from langchain_core.tools import tool
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
import sys
import os
import re
import asyncio

# Добавляем путь к проекту для импорта БД
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db as main_db
from .agent_class import AgentWithMemory
from .mistral_llm_api import mistral_llm_client
from .fallback_answers import _fallback_plan


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


@tool
def generate_meal_plan(
    user_id: int,
    goal: str,
    count_days: int = 3,
    use_saved_recipes: bool = False,
    daily_calories: int = 2000,
    budget: Optional[int] = None,
    language: str = "ru"
) -> str:
    """
    Генерирует план питания на основе параметров пользователя через Mistral AI.
    Сохраняет план в БД.
    
    Args:
        user_id: ID пользователя в Telegram
        goal: Цель питания ("снижение веса", "набор мышечной массы", "здоровое питание")
        count_days: На сколько дней составить план (от 1 до 7)
        use_saved_recipes: true если пользователь хочет использовать "сохраненные" рецепты, false если хочет попробовать "новые"
        daily_calories: Целевая дневная калорийность в ккал (по умолчанию 2000)
        budget: Бюджет на весь период в рублях (опционально)
        language: Язык ответа (по умолчанию "ru")
    
    Returns:
        Сообщение для пользователя
    """
    try:
        # Валидация параметров
        if not goal:
            return "❌ Необходимо указать цель питания (например, 'снижение веса')"
        
        if count_days < 1 or count_days > 7:
            return "❌ Количество дней должно быть от 1 до 7"
        
        if daily_calories < 800 or daily_calories > 5000:
            return "❌ Дневная калорийность должна быть от 800 до 5000 ккал"
        
        # Информация о рецептах
        recipe_note = "(с использованием новых рецептов)" if not use_saved_recipes else "(с использованием ваших сохраненных рецептов)"
        
        # Создаем агента
        agent = AgentWithMemory(llm_client=mistral_llm_client, user_id=user_id)
        
        # ✅ Явное указание количества дней в системный промпт
        system_prompt = f"""Ты — эксперт по питанию. Создай план питания РОВНО НА {count_days} ДНЕЙ.

ВАЖНО: Если запрошен 1 день, создай ТОЛЬКО 1 день! Не создавай больше дней.

Формат ответа - строго JSON без комментариев:
{{
  "День 1": {{
    "завтрак": "Название блюда - X ккал",
    "обед": "...",
    "ужин": "...",
    "перекус": "..."
  }}
}}
"""
        
        # ✅ Формируем user_message с запросом
        user_request = f"""
Создай план питания на {count_days} день/дней.
Цель: {goal}
Калорийность: {daily_calories} ккал/день
Бюджет: {budget if budget else 'без ограничений'} руб.
Язык: {language}
Рецепты: {'из сохраненных' if use_saved_recipes else 'новые'}

ВНИМАНИЕ: Должно быть РОВНО {count_days} дней. Не больше и не меньше!
"""
        
        # ✅ Передаем user_message, а не пустую строку
        result = agent.ask(
            user_message=user_request,  # Теперь здесь запрос!
            system_prompt=system_prompt,
            max_tokens=2000
        )
        
        if not result.get("success", False):
            error_msg = result.get("error", "Неизвестная ошибка")
            fallback_plan_data = _fallback_plan(goal, daily_calories)
            main_db.meal_plans.save_plan(user_id, {
                "plan": fallback_plan_data,
                "goal": goal,
                "days": count_days,
                "calories": daily_calories,
                "budget": budget,
                "saved_recipes": use_saved_recipes,
                "is_fallback": True
            })
            return f"⚠️ Ошибка при генерации плана: {error_msg}\n\nИспользуется резервный план питания"
        
        # Парсим ответ
        try:
            plan_data = json.loads(result["response"])
            
            # Валидация структуры - проверяем, что есть нужные дни
            expected_days = [f"День {i+1}" for i in range(count_days)]
            if not all(day in plan_data for day in expected_days):
                raise ValueError("Некорректная структура JSON")
            
            # Сохраняем план в БД
            meal_plan_data = {
                "plan": plan_data,
                "goal": goal,
                "days": count_days,
                "calories": daily_calories,
                "budget": budget,
                "saved_recipes": use_saved_recipes,
                "is_fallback": False
            }
            main_db.meal_plans.save_plan(user_id, meal_plan_data)
            
            # Форматируем результат для пользователя
            response = f"✅ План питания создан! \n\n"
            response += f"📅 На {count_days} дн. | 🔥 {daily_calories} ккал/день"
            response += f"\n\n"
            
            # Форматируем дни плана
            for day_key in sorted(plan_data.keys(), key=lambda x: int(x.split()[1]) if len(x.split()) > 1 else 0):
                day_plan = plan_data[day_key]
                response += f"📍 {day_key}:\n"
                
                if isinstance(day_plan, dict):
                    for meal_type in ['завтрак', 'обед', 'ужин', 'перекус']:
                        meal = day_plan.get(meal_type, '')
                        if meal:
                            response += f"   • {meal_type.capitalize()}: {meal}\n"
                else:
                    response += f"   {day_plan}\n"
                
            
            # Добавляем вопрос о соответствии плана
            response += f"\n\n Подходит ли план или хотите что-то поменять❓"
            
            return response
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Ошибка парсинга JSON: {e}")
            
            os.makedirs("logs", exist_ok=True)
            with open("logs/error_ai_answers.txt", "w", encoding="utf-8") as f:
                f.write(result.get('response', ''))
            
            fallback_plan_data = _fallback_plan(goal, daily_calories)
            main_db.meal_plans.save_plan(user_id, {
                "plan": fallback_plan_data,
                "goal": goal,
                "days": count_days,
                "calories": daily_calories,
                "budget": budget,
                "saved_recipes": use_saved_recipes,
                "is_fallback": True
            })
            return f"⚠️ AI вернул невалидный JSON. Используется резервный план питания"
        
    except Exception as e:
        error_text = f"❌ Ошибка при генерации плана питания: {str(e)}"
        print(error_text)
        return error_text


@tool
def get_meal_plan(
    user_id: int
) -> str:
    """
    Получает активный план питания пользователя из БД.
    
    Args:
        user_id: ID пользователя в Telegram
    
    Returns:
        Текущий план питания в читаемом формате или сообщение об отсутствии
    """
    try:
        meal_plan = main_db.meal_plans.get_active_plan(user_id)
        
        if not meal_plan:
            return "📭 У вас нет активного плана питания. Создайте новый через команду 'Составить меню'."
        
        plan_data = meal_plan.get('plan', {})
        
        # Форматируем результат
        result = "📋 ВАШ АКТИВНЫЙ ПЛАН ПИТАНИЯ:\n\n"
        
        # Информация о плане
        goal = meal_plan.get('goal', 'не указана')
        days = meal_plan.get('days', '?')
        calories = meal_plan.get('calories', '?')
        budget = meal_plan.get('budget')
        
        result += f"🎯 Цель: {goal}\n"
        result += f"📅 Период: {days} дн. | 🔥 {calories} ккал/день"
        if budget:
            result += f" | 💰 {budget} руб."
        result += "\n\n"
        
        # Выводим дни плана
        for day_key in sorted(plan_data.keys(), key=lambda x: int(x.split()[1]) if len(x.split()) > 1 else 0):
            day_plan = plan_data[day_key]
            result += f"📍 {day_key}:\n"
            
            if isinstance(day_plan, dict):
                for meal_type in ['завтрак', 'обед', 'ужин', 'перекус']:
                    meal = day_plan.get(meal_type, '')
                    if meal:
                        result += f"   • {meal_type.capitalize()}: {meal}\n"
            else:
                result += f"   {day_plan}\n"
            
            result += "\n"
        
        is_fallback = meal_plan.get('is_fallback', False)
        if is_fallback:
            result += "_⚠️ Это резервный план, сгенерированный автоматически._"
        
        return result
        
    except Exception as e:
        return f"❌ Ошибка при получении плана питания: {str(e)}"


@tool
def delete_meal_plan(
    user_id: int
) -> str:
    """
    Удаляет текущий план питания пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
    
    Returns:
        Сообщение о результате удаления
    """
    try:
        meal_plan = main_db.meal_plans.get_active_plan(user_id)
        
        if not meal_plan:
            return "❌ Нет активного плана питания для удаления."
        
        # Архивируем план перед удалением
        main_db.meal_plans.archive_plan(user_id)
        
        # Удаляем активный план
        data = main_db.meal_plans._load_data()
        user_str = str(user_id)
        if user_str in data.get("meal_plans", {}):
            del data["meal_plans"][user_str]
            main_db.meal_plans._save_data(data)
        
        goal = meal_plan.get('goal', 'план питания')
        return f"✅ План питания '{goal}' удален и архивирован."
        
    except Exception as e:
        return f"❌ Ошибка при удалении плана питания: {str(e)}"


@tool
def generate_shopping_list(
    user_id: int
) -> str:
    """
    Генерирует список покупок на основе активного плана питания.
    Объединяет все продукты из всех блюд на все дни.
    
    Args:
        user_id: ID пользователя в Telegram
    
    Returns:
        Список продуктов с общими количествами в читаемом формате
    """
    try:
        meal_plan = main_db.meal_plans.get_active_plan(user_id)
        
        if not meal_plan:
            return "❌ Нет активного плана питания. Сначала создайте план через 'Составить меню'."
        
        plan_data = meal_plan.get('plan', {})
        
        if not plan_data:
            return "❌ План питания пуст."
        
        # Создаем агента для генерации списка покупок
        agent = AgentWithMemory(llm_client=mistral_llm_client, user_id=user_id)
        
        # Формируем текст плана для AI
        plan_text = "\n".join([f"{day}: {meals}" for day, meals in plan_data.items()])
        
        system_prompt = """Ты — эксперт по покупкам. Создавай списки покупок ТОЛЬКО в формате JSON.
Без объяснений, без комментариев, без markdown. Только JSON объект."""
        
        prompt = f"""
На основе этого плана питания создай ОДИН общий список покупок (НЕ по вариантам, а ОДИН список с общим количеством всех продуктов).
Объедини одинаковые продукты и просумми их количества.

План питания:
{plan_text}

ФОРМАТ ОТВЕТА (СТРОГО JSON БЕЗ КОММЕНТАРИЕВ):
{{
  "items": [
    {{"name": "Куриное филе", "quantity": "1.5 кг"}},
    {{"name": "Рис", "quantity": "800 г"}},
    {{"name": "Помидоры", "quantity": "5 шт"}}
  ]
}}

Объедини все одинаковые ингредиенты и сложи количества!
Не создавай варианты, только ОДИН общий список!"""
        
        result = agent.ask(prompt, system_prompt=system_prompt, max_tokens=2000)
        
        if not result.get("success", False):
            error_msg = result.get("error", "Ошибка API")
            return f"⚠️ Ошибка при генерации списка покупок: {error_msg}"
        
        try:
            shopping_data = json.loads(result["response"])
            items = shopping_data.get("items", [])
            
            if not items:
                return "❌ Не удалось сгенерировать список покупок"
            
            # Сохраняем список в БД
            items_by_variant = {"Общий список": items}
            main_db.shopping_lists.save_list(user_id, items_by_variant)
            
            # Форматируем результат
            response = "🛒 СПИСОК ПРОДУКТОВ:\n\n"
            
            for item in items:
                name = item.get('name', 'Продукт')
                quantity = item.get('quantity', '1 шт')
                response += f"✓ {name} — {quantity}\n"
            
            return response
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Ошибка парсинга JSON для списка покупок: {e}")
            return f"❌ AI вернул невалидный JSON при генерации списка покупок"
        
    except Exception as e:
        error_text = f"❌ Ошибка при генерации списка покупок: {str(e)}"
        print(error_text)
        return error_text


@tool
def save_user_preferences(
    user_id: int,
    preferences: str
) -> str:
    """
    Сохраняет предпочтения и важную информацию о пользователе в БД.
    Эта информация будет использована для персонализации советов и меню.
    
    Args:
        user_id: ID пользователя в Telegram
        preferences: Строка с предпочтениями пользователя (например:
            "Не люблю помидоры, обожаю куриное филе, предпочитаю блюда на гриле,
            аллергия на молочные продукты, вегетарианец, готовит на скорость")
    
    Returns:
        Сообщение о результате сохранения
    """
    try:
        if not preferences or len(preferences.strip()) < 3:
            return "❌ Пожалуйста, укажите ваши предпочтения подробнее"
        
        # Получаем пользователя или создаем пустого
        user_data = main_db.get_user(user_id)
        if not user_data:
            user_data = {
                "user_id": user_id,
                "name": "Пользователь",
                "registered_at": datetime.now().isoformat()
            }
        
        # Сохраняем или обновляем предпочтения
        user_data["preferences"] = preferences
        user_data["preferences_updated_at"] = datetime.now().isoformat()
        
        main_db.save_user(user_id, user_data)
        
        return f"✅ Ваши предпочтения сохранены! Теперь я буду учитывать это при составлении меню."
        
    except Exception as e:
        error_text = f"❌ Ошибка при сохранении предпочтений: {str(e)}"
        print(error_text)
        return error_text


# ==================== СПИСОК ВСЕХ ИНСТРУМЕНТОВ ====================

ALL_TOOLS = [
    create_reminder,
    get_reminders,
    delete_reminder,
    generate_meal_plan,
    get_meal_plan,
    delete_meal_plan,
    generate_shopping_list,
    save_user_preferences
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
        
        elif name == "generate_meal_plan":
            result = generate_meal_plan.invoke(args)
            return result, False
        
        elif name == "get_meal_plan":
            result = get_meal_plan.invoke(args)
            return result, False
        
        elif name == "delete_meal_plan":
            result = delete_meal_plan.invoke(args)
            return result, False
        
        elif name == "generate_shopping_list":
            result = generate_shopping_list.invoke(args)
            return result, False
        
        elif name == "save_user_preferences":
            result = save_user_preferences.invoke(args)
            return result, False
        
        return f"Выполнен инструмент {name}", True
    
    executors = {}
    for tool in ALL_TOOLS:
        executors[tool.name] = reminder_executor
    
    return executors
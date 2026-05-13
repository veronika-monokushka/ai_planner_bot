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

from database import db
from .meals_generator import create_meal_plan_ai, create_shopping_list_ai


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


# ==================== НАПОМИНАНИЯ CRUD ====================

@tool
def create_reminder(
    user_id: int,
    text: str,
    remind_at: str,
    repeat_type: str = "once",
    from_ai: bool = False
) -> str:
    """
    Создает новое напоминание и сохраняет в БД.
    
    Используй этот инструмент, когда пользователь просит:
    - Напомнить о чем-то (выпить воду, поесть, принять витамины)
    - Поставить таймер или уведомление
    - Не забыть сделать что-то в определенное время
    
    Args:
        user_id: ID пользователя в Telegram
        text: Текст напоминания (например, "Выпить воду")
        remind_at: Время срабатывания (формат: "15:30", "сегодня в 15:30", "завтра в 10:00")
        repeat_type: Тип повторения: "once", "daily", "weekly"
        from_ai: Флаг AI-генерации текста напоминания каждый раз.
            ✅ Ставь True (текст как тема):
            - "Мотивационное напоминание о позитивном настрое"
            - "Совет дня по здоровому питанию"
            - "Напоминание о важности отдыха"
            
            ❌ Ставь False (текст как готовый сценарий):
            - "Выпить воду"
            - "Принять витамины"  
            - "Поесть"
            - "Тренировка в 19:00"
    
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
            "created_at": datetime.now().isoformat(),
            "from_ai": from_ai  # ✅ Добавляем флаг
        }
        
        if repeat_type == "once" and reminder_datetime:
            reminder_data["datetime"] = reminder_datetime.isoformat()
        elif repeat_type in ["daily", "weekly"] and reminder_time:
            reminder_data["time"] = reminder_time
        
        # Сохраняем в БД
        reminder_id = db.reminders.add_reminder(user_id, reminder_data, from_ai=from_ai)
        
        # Формируем ответ
        ai_suffix = " с AI-генерацией" if from_ai else ""
        
        if repeat_type == "once":
            time_str = reminder_datetime.strftime('%d.%m.%Y в %H:%M')
            return f"✅ Напоминание '{text}' создано{ai_suffix}!\n Однократное на {time_str}"
        elif repeat_type == "daily":
            return f"✅ Напоминание '{text}' создано{ai_suffix}!\n Ежедневное в {reminder_time}"
        else:  # weekly
            return f"✅ Напоминание '{text}' создано{ai_suffix}!\n Еженедельное в {reminder_time}"
        
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
            reminder = db.reminders.get_reminder_by_id(user_id, reminder_id)
            reminders = [reminder] if reminder else []
        else:
            if is_active is False:
                reminders = db.reminders.get_all_reminders(user_id)
            else:
                reminders = db.reminders.get_reminders(user_id)
        
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
        existing = db.reminders.get_reminder_by_id(user_id, reminder_id)
        if not existing:
            return f"❌ Напоминание с ID {reminder_id} не найдено."
        
        text = existing.get('name', '')
        db.reminders.delete_reminder(user_id, reminder_id)
        
        return f"✅ Напоминание '{text}' (ID:{reminder_id}) удалено."
        
    except Exception as e:
        return f"❌ Ошибка при удалении напоминания: {str(e)}"

# ==================== MEAL-PLAN CRUD ======================
@tool
def generate_meal_plan(
    user_id: int,
    goal: str,
    preferences_promt: str=None,
    count_days: int = 3,
    use_saved_recipes: bool = True,
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
        preferences_promt: промт для llm с дополнительными пожеланиями пользователя, названные в текущем диалоге (не нужно указывать, те которые записаны в базе данных о пользователе)
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
        
        result = create_meal_plan_ai(user_id, goal, preferences_promt, count_days, use_saved_recipes, daily_calories, budget, language)

    except Exception as e:
        print(f"❌ Ошибка при генерации плана питания: {str(e)}")
        error_text = "❌ Ошибка при генерации плана питания"
        return error_text

    # Форматируем результат для пользователя
    meal_plan_data = db.get_active_meal_plan(user_id)
    plan_data = meal_plan_data['plan']

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
        meal_plan = db.meal_plans.get_active_plan(user_id)
        
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
        meal_plan = db.meal_plans.get_active_plan(user_id)
        
        if not meal_plan:
            return "❌ Нет активного плана питания для удаления."
        
        # Архивируем план перед удалением
        db.meal_plans.archive_plan(user_id)
        
        # Удаляем активный план
        data = db.meal_plans._load_data()
        user_str = str(user_id)
        if user_str in data.get("meal_plans", {}):
            del data["meal_plans"][user_str]
            db.meal_plans._save_data(data)
        
        goal = meal_plan.get('goal', 'план питания')
        return f"✅ План питания '{goal}' удален и архивирован."
        
    except Exception as e:
        return f"❌ Ошибка при удалении плана питания: {str(e)}"


# ==================== SHOP LIST ====================
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
        meal_plan = db.meal_plans.get_active_plan(user_id)
        
        if not meal_plan:
            return "❌ Нет активного плана питания. Сначала создайте план через 'Составить меню'."
        
        plan_data = meal_plan.get('plan', {})
        
        if not plan_data:
            return "❌ План питания пуст."
        
        result = create_shopping_list_ai(user_id, plan_data)
        items = db.get_shopping_list(user_id)['cur_list']
            
        # Форматируем результат
        response = "🛒 СПИСОК ПРОДУКТОВ:\n\n"
        
        for item in items:
            name = item.get('name', 'Продукт')
            quantity = item.get('quantity', '1 шт')
            response += f"✓ {name} — {quantity}\n"
        
        return response
    
    except Exception as e:
        print(f'⚠️ERROR: Ошибка при генерации списка покупок: {str(e)}')
        return (f'Ошибка при генерации списка покупок')


# ==================== РЕЦЕПТЫ CRUD ====================
@tool
def add_recipe(
    user_id: int,
    name: str,
    ingredients: str = "",
    steps: str = "",
    time_category: str = "средне",
    price_category: str = "средне",
    tags: str = "",
    portions: int = 1
) -> str:
    """
    Добавляет новый рецепт в базу данных пользователя. Обязательные параметры: user_id, name.
    Остальное если пользователь не написал не нужно у него спрашивать.
    
    Args:
        user_id: ID пользователя в Telegram
        name: Название рецепта
        ingredients: Список ингредиентов (можно через запятую или с новой строки)
        steps: Пошаговый рецепт приготовления
        time_category: Время приготовления: "быстро", "средне", "долго"
        price_category: Стоимость: "дешево", "средне", "дорого"
        tags: Теги через запятую (например, "завтрак, диетическое")
        portions: Количество порций
    
    Returns:
        Сообщение о результате добавления рецепта
    """
    try:
        # Валидация
        if not name or len(name.strip()) < 2:
            return "❌ Название рецепта должно содержать хотя бы 2 символа"
        
        valid_time_categories = ["быстро", "средне", "долго"]
        if time_category not in valid_time_categories:
            return f"❌ Неверная категория времени. Используйте: {', '.join(valid_time_categories)}"
        
        valid_price_categories = ["дешево", "средне", "дорого"]
        if price_category not in valid_price_categories:
            return f"❌ Неверная категория цены. Используйте: {', '.join(valid_price_categories)}"
        
        # Преобразуем ингредиенты из строки в список
        ingredients_list = []
        if ingredients.strip():
            # Разбиваем по новой строке или по запятой
            if '\n' in ingredients:
                lines = ingredients.strip().split('\n')
            else:
                lines = ingredients.strip().split(',')
            
            for line in lines:
                line = line.strip()
                if line:
                    ingredients_list.append({"name": line, "quantity": "по вкусу"})
        
        # Преобразуем теги из строки в список
        tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []
        
        # Формируем данные для БД
        recipe_data = {
            "name": name.strip(),
            "ingredients": ingredients_list,
            "steps": steps.strip(),
            "time_category": time_category,
            "price_category": price_category,
            "tags": tags_list,
            "portions": portions
        }
        
        # Сохраняем в БД
        recipe_id = db.add_recipe(user_id, recipe_data)
        
        # Формируем ответ
        response = f"Рецепт добавлен!\n\n"
        response += f"📝 {name}\n"
        response += f"⏱️ Время: {time_category}\n"
        response += f"💰 Цена: {price_category}\n"
        
        if ingredients_list:
            response += f"\n🥕 Ингредиенты ({len(ingredients_list)}):\n"
            for ing in ingredients_list[:5]:  # Показываем первые 5
                response += f"  • {ing['name']}\n"
            if len(ingredients_list) > 5:
                response += f"  ... и ещё {len(ingredients_list) - 5}\n"
        
        return response
        
    except Exception as e:
        return f"❌ Ошибка при добавлении рецепта: {str(e)}"


@tool
def get_recipes(
    user_id: int,
    recipe_id: Optional[int] = None,
    time_category: Optional[str] = None,
    price_category: Optional[str] = None,
    tag: Optional[str] = None,
    search_query: Optional[str] = None
) -> str:
    """
    Получает список рецептов пользователя с возможностью фильтрации.
    
    Args:
        user_id: ID пользователя в Telegram
        recipe_id: ID конкретного рецепта (опционально)
        time_category: Фильтр по времени: "быстро", "средне", "долго"
        price_category: Фильтр по цене: "дешево", "средне", "дорого"
        tag: Фильтр по тегу (например, "завтрак")
        search_query: Поиск по названию
    
    Returns:
        Список рецептов в читаемом формате
    """
    try:
        # Если указан конкретный ID
        if recipe_id:
            recipe = db.get_recipe(recipe_id)
            
            if not recipe or recipe.get('user_id') != str(user_id):
                return f"❌ Рецепт с ID {recipe_id} не найден или принадлежит другому пользователю"
            
            # Форматируем детальный вывод
            result += f"🆔 ID: {recipe_id}\n"
            result = f"📖 {recipe.get('name', 'Без названия')}\n\n"
            result += f"⏱️ Время: {recipe.get('time_category', '-')}\n"
            result += f"💰 Цена: {recipe.get('price_category', '-')}\n"
            result += f"🍽️ Порций: {recipe.get('portions', 1)}\n"
            
            tags = recipe.get('tags', [])
            if tags:
                result += f"🏷️ Теги: {', '.join(tags)}\n"
            
            # Ингредиенты
            ingredients = recipe.get('ingredients', [])
            if ingredients:
                result += f"\n🥕 Ингредиенты:\n"
                for ing in ingredients:
                    name = ing.get('name', '')
                    quantity = ing.get('quantity', '')
                    if quantity:
                        result += f"  • {name} — {quantity}\n"
                    else:
                        result += f"  • {name}\n"
            
            # Шаги приготовления
            steps = recipe.get('steps', '')
            """
            if steps:
                result += f"\n👨‍🍳 Приготовление:\n"
                # Разбиваем шаги по точкам или переводам строк
                step_lines = steps.replace('\r', '').split('\n')
                for i, step in enumerate(step_lines, 1):
                    if step.strip():
                        result += f"  {i}. {step.strip()}\n"
            """
            #result += f"\n📅 Создан: {recipe.get('created_at', '?')[:10]}"
            
            return result
        
        # Получаем все рецепты пользователя
        recipes = db.get_user_recipes(user_id)
        
        if not recipes:
            return "📭 У вас пока нет рецептов. Добавьте первый через команду 'Добавить рецепт'!"
        
        # Применяем фильтры
        filtered_recipes = recipes.copy()
        
        if time_category and time_category != "all":
            filtered_recipes = [r for r in filtered_recipes if r.get('time_category') == time_category]
        
        if price_category and price_category != "all":
            filtered_recipes = [r for r in filtered_recipes if r.get('price_category') == price_category]
        
        if tag and tag != "all":
            filtered_recipes = [r for r in filtered_recipes if tag in r.get('tags', [])]
        
        if search_query:
            query = search_query.lower()
            filtered_recipes = [r for r in filtered_recipes if query in r.get('name', '').lower()]
        
        if not filtered_recipes:
            return "📭 Нет рецептов, соответствующих выбранным фильтрам."
        
        # Форматируем вывод
        result = f"📋 МОИ РЕЦЕПТЫ ({len(filtered_recipes)})\n\n"
        
        for i, recipe in enumerate(filtered_recipes[:20], 1):
            name = recipe.get('name', 'Без названия')
            recipe_id_val = recipe.get('id', '?')
            time_cat = recipe.get('time_category', '-')
            price_cat = recipe.get('price_category', '-')
            
            # Сокращаем длинные названия
            if len(name) > 35:
                name = name[:32] + "..."
            
            result += f"ID {recipe_id_val}. {name}\n"
            result += f"⏱️{time_cat} | 💰{price_cat}\n\n"
        
        if len(filtered_recipes) > 20:
            result += f"_Показано 20 из {len(filtered_recipes)} рецептов._\n"
            result += "Используй `recipe_id` для просмотра конкретного рецепта"
        
        return result
        
    except Exception as e:
        return f"❌ Ошибка при получении рецептов: {str(e)}"


@tool
def update_recipe(
    user_id: int,
    recipe_id: int,
    name: Optional[str] = None,
    ingredients: Optional[str] = None,
    steps: Optional[str] = None,
    time_category: Optional[str] = None,
    price_category: Optional[str] = None,
    tags: Optional[str] = None,
    portions: Optional[int] = None
) -> str:
    """
    Обновляет существующий рецепт пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
        recipe_id: ID рецепта для редактирования
        name: Новое название рецепта
        ingredients: Новый список ингредиентов
        steps: Новый пошаговый рецепт
        time_category: Новая категория времени
        price_category: Новая категория цены
        tags: Новые теги через запятую
        portions: Новое количество порций
    
    Returns:
        Сообщение о результате обновления
    """
    try:
        # Получаем существующий рецепт
        existing = db.get_recipe(recipe_id)
        
        if not existing or existing.get('user_id') != str(user_id):
            return f"❌ Рецепт не найден"
        
        # Обновляем только переданные поля
        updated = False
        
        if name is not None:
            if len(name.strip()) < 2:
                return "❌ Название рецепта должно содержать хотя бы 2 символа"
            existing['name'] = name.strip()
            updated = True
        
        if ingredients is not None:
            ingredients_list = []
            if ingredients.strip():
                if '\n' in ingredients:
                    lines = ingredients.strip().split('\n')
                else:
                    lines = ingredients.strip().split(',')
                
                for line in lines:
                    line = line.strip()
                    if line:
                        ingredients_list.append({"name": line, "quantity": "по вкусу"})
            existing['ingredients'] = ingredients_list
            updated = True
        
        if steps is not None:
            existing['steps'] = steps.strip()
            updated = True
        
        if time_category is not None:
            valid = ["быстро", "средне", "долго"]
            if time_category not in valid:
                return f"❌ Неверная категория. Используйте: {', '.join(valid)}"
            existing['time_category'] = time_category
            updated = True
        
        if price_category is not None:
            valid = ["дешево", "средне", "дорого"]
            if price_category not in valid:
                return f"❌ Неверная категория. Используйте: {', '.join(valid)}"
            existing['price_category'] = price_category
            updated = True
        
        if tags is not None:
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []
            existing['tags'] = tags_list
            updated = True
        
        if portions is not None:
            if portions < 1:
                return "❌ Количество порций должно быть больше 0"
            existing['portions'] = portions
            updated = True
        
        if not updated:
            return "❌ Не указано ни одно поле для обновления"
        
        # Сохраняем через add_recipe (перезапись с тем же ID)
        # В текущей реализации RecipeRepository не имеет update_recipe,
        # поэтому используем add_recipe, который создаёт новый, или нужно доработать.
        # Для упрощения: удаляем старый и создаём новый с теми же данными
        
        # Временно: сохраняем через пересоздание
        # Более правильный вариант - добавить метод update_recipe в RecipeRepository
        recipe_data = {
            "name": existing['name'],
            "ingredients": existing.get('ingredients', []),
            "steps": existing.get('steps', ''),
            "time_category": existing.get('time_category', 'средне'),
            "price_category": existing.get('price_category', 'средне'),
            "tags": existing.get('tags', []),
            "portions": existing.get('portions', 1)
        }
        
        # Удаляем старый и добавляем новый
        db.recipes.delete_recipe(user_id, recipe_id)
        new_id = db.add_recipe(user_id, recipe_data)
        
        return f"✅ Рецепт {existing['name']} обновлён"
        
    except Exception as e:
        return f"❌ Ошибка при обновлении рецепта: {str(e)}"


@tool
def delete_recipe(
    user_id: int,
    recipe_id: int
) -> str:
    """
    Удаляет рецепт из базы данных.
    
    Args:
        user_id: ID пользователя в Telegram
        recipe_id: ID рецепта для удаления
    
    Returns:
        Сообщение о результате удаления
    """
    try:
        # Проверяем существование рецепта
        existing = db.get_recipe(recipe_id)
        
        if not existing or existing.get('user_id') != str(user_id):
            return f"❌ Рецепт с ID {recipe_id} не найден или принадлежит другому пользователю"
        
        name = existing.get('name', 'Без названия')
        
        # Удаляем
        success = db.recipes.delete_recipe(user_id, recipe_id)
        
        if success:
            return f"✅ Рецепт {name} удалён."
        else:
            return f"❌ Не удалось удалить рецепт. Попробуйте позже."
        
    except Exception as e:
        return f"❌ Ошибка при удалении рецепта: {str(e)}" 

# ==================== ПРЕДПОЧТЕНИЯ ====================
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
        user_data = db.get_user(user_id)
        if not user_data:
            user_data = {
                "user_id": user_id,
                "name": "Пользователь",
                "registered_at": datetime.now().isoformat()
            }
        
        # Сохраняем или обновляем предпочтения
        user_data["preferences"] = preferences
        user_data["preferences_updated_at"] = datetime.now().isoformat()
        
        db.save_user(user_id, user_data)
        
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
    add_recipe,
    get_recipes,
    update_recipe,
    delete_recipe,
    save_user_preferences
]


# ==================== ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ TOOL_EXECUTORS ====================

def get_tool_executors():
    """
    Возвращает словарь исполнителей для инструментов.
    Используется в ask_with_tools для автоматической обработки.
    """
    
    executors = {}
    for tool in ALL_TOOLS:
        def make_executor(tool_func):
            def executor(tool_call):
                result = tool_func.invoke(tool_call["args"])
                return result, False  # False = не вызывать LLM повторно
            return executor
        
        executors[tool.name] = make_executor(tool)
    
    return executors

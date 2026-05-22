# ai_agent/meals_generator.py

import json
import asyncio
import os
from database import db
from typing import Optional
from datetime import datetime

from .agent_class import AgentWithMemory
from .mistral_llm_api import mistral_llm_client
from .fallback_answers import _fallback_plan, _fallback_shopping_list
from .ai_logger import log_parse_error
from bot_backend.logger import default_logger as logger

async def custom_ai_reminder(user_id: int, topic: str) -> str:
    """
    Генерирует текст напоминания по заданной теме с помощью AI.
    
    Args:
        user_id: ID пользователя (для персонализации)
        topic: Тема напоминания (например, "мотивационное сообщение о позитивном настрое")
    
    Returns:
        Сгенерированный текст напоминания
    """
    agent = AgentWithMemory(llm_client=mistral_llm_client, user_id=user_id)
    
    system_prompt = """Ты — мотивирующий и дружелюбный помощник. Генерируй короткие, позитивные и вдохновляющие сообщения.
    
Правила:
- Отвечай ТОЛЬКО текстом сообщения (без пояснений, без кавычек)
- Сообщение должно быть от 1 до 2 предложений
- Используй эмодзи
- Обращайся к пользователю на "ты"
"""
    
    user_request = f"""Создай сообщение для напоминания на тему: {topic}"""
    
    result = agent.ask(
        user_message=user_request,
        system_prompt=system_prompt,
        max_tokens=200
    )
    fallback_remind = "Хорошего дня, не забывай о своих целях! 💪"
    if result.get("success"):
        return result.get("response", fallback_remind)
    else:
        return fallback_remind

def user_recipe_titles(user_id: int) -> str:
    """
    Возвращает строку с названиями рецептов пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
    
    Returns:
        Строка с перечислением названий рецептов для вставки в промпт
    """
    recipes = db.get_user_recipes(user_id)
    
    if not recipes:
        return "нет пользовательских рецептов"
    
    titles = [recipe.get('name', 'Без названия') for recipe in recipes]
    
    # Вариант 1: простая строка
    return ", ".join(titles)

def create_meal_plan_ai(
    user_id: int,
    goal: str,
    preferences_promt: str=None,
    count_days: int = 3,
    use_saved_recipes: bool = True,
    daily_calories: int = 2000,
    budget: Optional[int] = None,
    language: str = "ru"
) -> int:
    
    """Генерирует план питания на неделю через Mistral AI
    возвращает флаг - 0 сгенрирован, 1 fallback-ответ"""
    
    # Информация о рецептах
    recipe_note = "" if not use_saved_recipes else f"Используй рецепты пользователя, но по 1 разу в неделю каждый: {user_recipe_titles(user_id)}"
    
    # Создаем агента
    agent = AgentWithMemory(llm_client=mistral_llm_client, user_id=user_id)
    
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
Бюджет на 7 дней: {budget if budget else 'среднии траты'} руб.
Язык: {language}
Рецепты: {'из сохраненных' if use_saved_recipes else 'новые'}
Предпочтения: {preferences_promt}
{recipe_note}
ВНИМАНИЕ: Должно быть РОВНО {count_days} дней. Не больше и не меньше!
"""
    
    result = agent.ask(
        user_message=user_request, 
        system_prompt=system_prompt,
        max_tokens=2000
    )
    
    if not result.get("success", False):
        error_msg = result.get("error", "Неизвестная ошибка")
        fallback_plan_data = _fallback_plan(goal, daily_calories, count_days)
        db.meal_plans.save_plan(user_id, {
            "plan": fallback_plan_data,
            "goal": goal,
            "days": count_days,
            "calories": daily_calories,
            "budget": budget,
            "saved_recipes": use_saved_recipes,
            "is_fallback": True
        })
        logger.error(f"ERROR: {error_msg}")
        return 1
    
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
        db.save_meal_plan(user_id, meal_plan_data)
        
        return 0
        
    except json.JSONDecodeError as e:
        log_parse_error(
            user_id=user_id,
            raw_response=result.get('response', ''),
            exception=str(e)
        )
        
        fallback_plan_data = _fallback_plan(goal, daily_calories, count_days)
        db.meal_plans.save_plan(user_id, {
            "plan": fallback_plan_data,
            "goal": goal,
            "days": count_days,
            "calories": daily_calories,
            "budget": budget,
            "saved_recipes": use_saved_recipes,
            "is_fallback": True
        })
        logger.error(f"⚠️ ERROR: Ошибка парсинга JSON: {e}")
        return 1
        
def create_shopping_list_ai(
    user_id: int,
    plan: dict,
    language: str = "ru"
) -> int:
    """
    Генерирует список покупок из плана питания через Mistral AI.
    
    Args:
        user_id: ID пользователя в Telegram
        plan: План питания (словарь с днями и приемами пищи)
        language: Язык ответа (по умолчанию "ru")
    
    Returns:
        0 - список успешно сгенерирован и сохранен
        1 - ошибка, использован fallback-список
    """
    
    plan_data = plan

    # Создаем агента
    agent = AgentWithMemory(llm_client=mistral_llm_client, user_id=user_id)
    
    plan_text = "\n".join([f"{day}: {meals}" for day, meals in plan_data.items()])
        
    system_prompt = """Ты — эксперт по покупкам. Создавай списки покупок ТОЛЬКО в формате JSON.
Без объяснений, без комментариев, без markdown. Только JSON объект."""
        
    user_request = f"""
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
        

    result = agent.ask(
        user_message=user_request,
        system_prompt=system_prompt,
        max_tokens=1000
    )
    
    if not result.get("success", False):
        error_msg = result.get("error", "Неизвестная ошибка API")
        logger.error(f"⚠️ERROR: При генерации списка покупок: {error_msg}")
        
        # Используем fallback
        fallback_items = _fallback_shopping_list(plan)
        db.shopping_lists.save_list(user_id, {"items": fallback_items.get("items", [])})
        return 1
    
    # Парсим ответ
    try:
        shopping_data = json.loads(result["response"])
        items = shopping_data.get("items", [])
        
        if not items:
            raise ValueError("Отсутствует поле 'items' в ответе")
        if not isinstance(items, list):
            raise ValueError("'items' должен быть списком")
        
        # Сохраняем список в БД
        items_by_variant = {"cur_list": items}
        db.save_shopping_list(user_id, items_by_variant)
        
        return 0
        
    except json.JSONDecodeError as e:
        logger.error(f"⚠️ ERROR: Ошибка парсинга JSON для списка покупок: {e}")
        logger.error(f"Ответ AI: {result.get('response', '')[:500]}")

        # Сохраняем ошибку с новыми функциями
        log_parse_error(
            user_id=user_id,
            raw_response=result.get('response', ''),
            exception=str(e)
        )

        fallback_items = _fallback_shopping_list(plan)
        db.shopping_lists.save_list(user_id, {"items": fallback_items.get("items", [])})
        return 1
        
    except Exception as e:
        logger.error(f"⚠️ERROR: Критическая ошибка при генерации списка покупок: {e}")
        
        fallback_items = _fallback_shopping_list(plan)
        db.shopping_lists.save_list(user_id, {"items": fallback_items.get("items", [])})
        return 1



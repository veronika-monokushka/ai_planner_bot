# ai_agent/meals_generator.py

import json
from .agent_class import AgentWithMemory
from .mistral_llm_api import mistral_llm_client
import asyncio
import os
from .fallback_answers import _fallback_plan, _fallback_shopping_list
from database import db
from typing import Optional

    
def create_meal_plan_ai(
    user_id: int,
    goal: str,
    preferences_promt: str=None,
    count_days: int = 3,
    use_saved_recipes: bool = False,
    daily_calories: int = 2000,
    budget: Optional[int] = None,
    language: str = "ru"
) -> int:
    
    """Генерирует план питания на неделю через Mistral AI
    возвращает флаг - 0 сгенрирован, 1 fallback-ответ"""
    
    # Информация о рецептах
    recipe_note = "(с использованием новых рецептов)" if not use_saved_recipes else "(с использованием ваших сохраненных рецептов)"
    
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
Бюджет: {budget if budget else 'без ограничений'} руб.
Язык: {language}
Рецепты: {'из сохраненных' if use_saved_recipes else 'новые'}
Предпочтения: {preferences_promt}

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
        print(f"ERROR: {error_msg}")
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
        os.makedirs("logs", exist_ok=True)
        with open("logs/error_ai_answers.txt", "w", encoding="utf-8") as f:
            f.write(result.get('response', ''))
        
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
        print(f"⚠️ ERROR: Ошибка парсинга JSON: {e}")
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
        print(f"⚠️ERROR: При генерации списка покупок: {error_msg}")
        
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
        print(f"⚠️ERROR: Ошибка парсинга JSON для списка покупок: {e}")
        print(f"Ответ AI: {result.get('response', '')[:500]}")
        
        os.makedirs("logs", exist_ok=True)
        with open("logs/error_shopping_list_ai.txt", "w", encoding="utf-8") as f:
            f.write(result.get('response', ''))
        
        fallback_items = _fallback_shopping_list(plan)
        db.shopping_lists.save_list(user_id, {"items": fallback_items.get("items", [])})
        return 1
        
    except Exception as e:
        print(f"⚠️ERROR: Критическая ошибка при генерации списка покупок: {e}")
        
        fallback_items = _fallback_shopping_list(plan)
        db.shopping_lists.save_list(user_id, {"items": fallback_items.get("items", [])})
        return 1





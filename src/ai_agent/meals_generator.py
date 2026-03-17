"""Сервис для генерации питания через AI"""
import json
from .llm_client import MistralAgent
import asyncio
import os


async def create_meal_plan_ai(
    goal: str,
    budget: int = None,
    daily_calories: int = 2000,
    language: str = "ru",
    count_days = 7) -> dict:
    """Генерирует план питания на неделю через Mistral AI"""
    
    agent = MistralAgent()
    
    system_prompt = """Ты — эксперт по питанию. Создавай планы питания ТОЛЬКО в формате JSON.
Без объяснений, без комментариев, без markdown. Только JSON объект."""
    
    prompt = f"""
Создай план питания на {count_days} дней (ПН,..).

Данные пользователя:
- ЦЕЛЬ: {goal}
- ДНЕВНАЯ КАЛОРИЙНОСТЬ: {daily_calories} ккал
- БЮДЖЕТ НА НЕДЕЛЮ: {budget if budget else 'без ограничений'} руб.
- ЯЗЫК ОТВЕТА: {language}

ФОРМАТА ОТВЕТА (СТРОГО JSON БЕЗ КОММЕНТАРИЕВ):
{{
  "ПН": {{
    "завтрак": "...",
    "обед": "...",
    "ужин": "...",
    "перекус": "..."
  }},
  "ВТ": {{ ... }}
}}
"""
    
    try:
        result = await asyncio.to_thread(agent.ask, prompt, system_prompt=system_prompt)
        
        if not result["success"]:
            return {
                "success": False,
                "plan": _fallback_plan(goal, daily_calories),
                "error": f"Ошибка API: {result['error']}"
            }
        
        # Парсим ответ
        try:
            plan_data = json.loads(result["response"])
            
            # Валидация структуры
            valid_days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
            valid_days = valid_days[:count_days]
            if not all(day in plan_data for day in valid_days):
                raise ValueError("Некорректная структура JSON")
                
            return {
                "success": True,
                "plan": plan_data,
                "tokens": result.get("tokens", 0),
                "model": agent.model
            }
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Ошибка парсинга JSON: {e}")
            
            os.makedirs("logs", exist_ok=True)
            # Сохраняем в файл
            with open("logs/error_ai_answers.txt", "w", encoding="utf-8") as f:
                f.write(result['response'])
            return {
                "success": False,
                "plan": _fallback_plan(goal, daily_calories),
                "error": "AI вернул невалидный JSON"
            }
            
    except Exception as e:
        print(f"❌ Критическая ошибка AI: {e}")
        return {
            "success": False,
            "plan": _fallback_plan(goal, daily_calories),
            "error": str(e)
        }


def generate_shopping_list_ai(plan: dict) -> dict:
    """Генерирует список покупок из плана питания через AI"""
    
    agent = MistralAgent()
    
    plan_text = "\n".join([f"{day}: {meals}" for day, meals in plan.items()])
    
    prompt = f"""
На основе этого плана питания создай готовый список покупок ТОЛЬКО в формате JSON массива.

{plan_text}

ФОРМАТ ОТВЕТА:
[
  {{"name": "Куриное филе", "quantity": "800 г"}},
  {{"name": "Рис", "quantity": "500 г"}}
]

Без комментариев, только JSON."""
    
    try:
        result = agent.ask(prompt)
        
        if result["success"]:
            try:
                items = json.loads(result["response"])
                return {"success": True, "items": items, "tokens": result.get("tokens", 0)}
            except json.JSONDecodeError:
                return _fallback_shopping_list(plan)
        else:
            return {"success": False, "items": [], "error": result.get("error", "Ошибка API")}
            
    except Exception as e:
        return {"success": False, "items": [], "error": str(e)}


def _fallback_plan(goal: str, daily_calories: int) -> dict:
    """Бэкап-план если AI отказался отвечать или API недоступен"""
    breakfasts = [
        "Овсянка с ягодами", "Яичница с овощами", "Творог со сметаной",
        "Гречка с молоком", "Сырники домашние", "Омлет классический"
    ]
    lunches = [
        "Курица с гречкой", "Рыба запечённая", "Борщ постный", 
        "Паста карбонара", "Овощное рагу", "Плов куриный", "Греческий салат"
    ]
    dinners = [
        "Рыба на пару", "Куриное филе гриль", "Омлет белковый",
        "Салат с тунцом", "Запеканка творожная", "Смузи зелёный"
    ]
    snacks = [
        "Яблоко печёное", "Горсть орехов", "Греческий йогурт", "Банан"
    ]
    
    plan = {}
    days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    
    for i, day in enumerate(days):
        plan[day] = {
            "завтрак": breakfasts[i % len(breakfasts)],
            "обед": lunches[i % len(lunches)],
            "ужин": dinners[i % len(dinners)],
            "перекус": snacks[i % len(snacks)]
        }
    
    return plan


def _fallback_shopping_list(plan: dict) -> dict:
    """Бэкап-генератор списка покупок без AI"""
    ingredients_db = {
        "Овсянка с ягодами": [{"name": "Овсянка", "quantity": "500 г"}, {"name": "Ягоды", "quantity": "300 г"}],
        "Яичница с овощами": [{"name": "Яйца", "quantity": "10 шт"}, {"name": "Овощи", "quantity": "500 г"}],
        "Курица с гречкой": [{"name": "Куриное филе", "quantity": "800 г"}, {"name": "Гречка", "quantity": "500 г"}],
    }
    
    aggregated = {}
    
    for day, meals in plan.items():
        for meal_type, dish in meals.items():
            for key, ingredients in ingredients_db.items():
                if key.lower() in dish.lower():
                    for ing in ingredients:
                        name = ing["name"]
                        if name in aggregated:
                            aggregated[name] += f" + {ing['quantity']}"
                        else:
                            aggregated[name] = ing["quantity"]
    
    items = [{"name": name, "quantity": qty} for name, qty in aggregated.items()]
    
    if not items:
        items = [
            {"name": "Яйца", "quantity": "10 шт"},
            {"name": "Куриное филе", "quantity": "800 г"},
            {"name": "Гречка", "quantity": "500 г"},
            {"name": "Рис", "quantity": "500 г"},
            {"name": "Овощи", "quantity": "1 кг"},
            {"name": "Фрукты", "quantity": "1 кг"}
        ]
    
    return {"success": True, "items": items, "tokens": 0}
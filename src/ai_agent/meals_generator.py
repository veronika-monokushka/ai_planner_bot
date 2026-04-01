# ai_agent/meals_generator.py

import json
from .llm_client import MistralAgent
import asyncio
import os
from .fallback_answers import _fallback_plan, _fallback_shopping_list

async def create_meal_plan_ai(
    goal: str,
    budget: int = None,
    daily_calories: int = 2000,
    language: str = "ru",
    count_days = 2) -> dict:
    """Генерирует план питания на неделю через Mistral AI"""
    
    agent = MistralAgent()
    
    system_prompt = """Ты — эксперт по питанию. Создавай планы питания ТОЛЬКО в формате JSON.
Без объяснений, без комментариев, без markdown. Только JSON объект."""
    
    prompt = f"""
Создай план питания {count_days} вариантов (Вариант 1,..).

Данные пользователя:
- ЦЕЛЬ: {goal}
- ДНЕВНАЯ КАЛОРИЙНОСТЬ: {daily_calories} ккал
- БЮДЖЕТ НА НЕДЕЛЮ: {budget if budget else 'без ограничений'} руб.
- ЯЗЫК ОТВЕТА: {language}

ФОРМАТА ОТВЕТА (СТРОГО JSON БЕЗ КОММЕНТАРИЕВ):
{{
  "Вариант 1": {{
    "завтрак": "...",
    "обед": "...",
    "ужин": "...",
    "перекус": "..."
  }},
  "Вариант 2": {{ ... }}
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
            valid_days = ["Вариант 1", "Вариант 2", "Вариант 3"]
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
    """Генерирует список покупок из плана питания через AI с разделением по вариантам"""
    
    agent = MistralAgent()
    
    plan_text = "\n".join([f"{day}: {meals}" for day, meals in plan.items()])
    
    prompt = f"""
На основе этого плана питания создай список покупок ТОЛЬКО в формате JSON.
Раздели продукты по вариантам меню.

{plan_text}

ФОРМАТ ОТВЕТА:
{{
  "Вариант 1": [
    {{"name": "Куриное филе", "quantity": "500 г"}},
    {{"name": "Рис", "quantity": "300 г"}}
  ],
  "Вариант 2": [
    {{"name": "Рыба", "quantity": "400 г"}},
    {{"name": "Гречка", "quantity": "300 г"}}
  ]
}}

Важно: каждый элемент должен быть объектом с полями "name" и "quantity".
Без комментариев, только JSON."""
    
    try:
        result = agent.ask(prompt)
        
        # ✅ Отладочный вывод
        print(f"AI ответ для списка покупок: {result.get('response', '')[:500]}")
        
        if result["success"]:
            try:
                items_by_variant = json.loads(result["response"])
                
                # ✅ Выводим структуру для отладки
                print(f"Распарсенный JSON: {items_by_variant}")
                
                # ✅ Валидируем и приводим к правильному формату
                validated_items = {}
                for variant, items in items_by_variant.items():
                    if isinstance(items, list):
                        validated_list = []
                        for item in items:
                            if isinstance(item, dict):
                                validated_list.append({
                                    "name": item.get("name", str(item)),
                                    "quantity": item.get("quantity", "1 шт")
                                })
                            elif isinstance(item, str):
                                validated_list.append({
                                    "name": item,
                                    "quantity": "1 шт"
                                })
                            else:
                                validated_list.append({
                                    "name": str(item),
                                    "quantity": "1 шт"
                                })
                        validated_items[variant] = validated_list
                    else:
                        validated_items[variant] = [
                            {"name": str(items), "quantity": "1 шт"}
                        ]
                
                return {
                    "success": True, 
                    "items_by_variant": validated_items, 
                    "tokens": result.get("tokens", 0)
                }
            except json.JSONDecodeError as e:
                print(f"⚠️ Ошибка парсинга JSON: {e}")
                print(f"Ответ AI: {result['response']}")
                return _fallback_shopping_list(plan)
        else:
            return {"success": False, "items_by_variant": {}, "error": result.get("error", "Ошибка API")}
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return {"success": False, "items_by_variant": {}, "error": str(e)}




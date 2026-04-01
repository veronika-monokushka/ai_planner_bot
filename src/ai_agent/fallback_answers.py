
def _fallback_plan(goal: str, daily_calories: int, count_days: int = 7) -> dict:
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
    days = [f"Вариант {i+1}" for i in range(count_days)]
    
    for i, day in enumerate(days):
        plan[day] = {
            "завтрак": breakfasts[i % len(breakfasts)],
            "обед": lunches[i % len(lunches)],
            "ужин": dinners[i % len(dinners)],
            "перекус": snacks[i % len(snacks)]
        }
    
    return plan

def _fallback_shopping_list(plan: dict) -> dict:
    """Бэкап-генератор списка покупок без AI с разделением по вариантам"""
    ingredients_db = {
        "Овсянка с ягодами": [{"name": "Овсянка", "quantity": "500 г"}, {"name": "Ягоды", "quantity": "300 г"}],
        "Яичница с овощами": [{"name": "Яйца", "quantity": "10 шт"}, {"name": "Овощи", "quantity": "500 г"}],
        "Творог со сметаной": [{"name": "Творог", "quantity": "500 г"}, {"name": "Сметана", "quantity": "200 г"}],
        "Гречка с молоком": [{"name": "Гречка", "quantity": "500 г"}, {"name": "Молоко", "quantity": "1 л"}],
        "Курица с гречкой": [{"name": "Куриное филе", "quantity": "800 г"}, {"name": "Гречка", "quantity": "500 г"}],
        "Рыба запечённая": [{"name": "Рыба", "quantity": "600 г"}, {"name": "Лимон", "quantity": "1 шт"}],
        "Борщ постный": [{"name": "Свекла", "quantity": "2 шт"}, {"name": "Капуста", "quantity": "500 г"}, {"name": "Морковь", "quantity": "2 шт"}],
        "Паста карбонара": [{"name": "Паста", "quantity": "400 г"}, {"name": "Бекон", "quantity": "200 г"}, {"name": "Сливки", "quantity": "200 мл"}],
        "Овощное рагу": [{"name": "Кабачок", "quantity": "2 шт"}, {"name": "Баклажан", "quantity": "2 шт"}, {"name": "Помидоры", "quantity": "4 шт"}],
    }
    
    items_by_variant = {}
    
    for variant, meals in plan.items():
        variant_items = []
        aggregated = {}
        
        for meal_type, dish in meals.items():
            for key, ingredients in ingredients_db.items():
                if key.lower() in dish.lower():
                    for ing in ingredients:
                        name = ing["name"]
                        if name in aggregated:
                            # Если продукт уже есть, добавляем количество
                            aggregated[name] = f"{aggregated[name]} + {ing['quantity']}"
                        else:
                            aggregated[name] = ing["quantity"]
        
        for name, qty in aggregated.items():
            variant_items.append({"name": name, "quantity": qty})
        
        if not variant_items:
            variant_items = [
                {"name": "Куриное филе", "quantity": "500 г"},
                {"name": "Рис", "quantity": "300 г"},
                {"name": "Овощи", "quantity": "500 г"},
                {"name": "Яйца", "quantity": "6 шт"}
            ]
        
        items_by_variant[variant] = variant_items
    
    return {"success": True, "items_by_variant": items_by_variant, "tokens": 0}
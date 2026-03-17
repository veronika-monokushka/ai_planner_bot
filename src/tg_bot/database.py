import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

class UserDatabase:
    """Класс для работы с JSON файлом пользователей"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Создает файл, если его нет"""
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    def _load_data(self) -> Dict:
        """Загружает данные из файла"""
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                return data
        except:
            return {}
    
    def _save_data(self, data: Dict):
        """Сохраняет данные в файл"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # ==================== ПОЛЬЗОВАТЕЛИ ====================
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получает данные пользователя по ID"""
        data = self._load_data()
        if 'users' not in data:
            return data.get(str(user_id))
        return data["users"].get(str(user_id))
    
    def save_user(self, user_id: int, user_data: Dict):
        """Сохраняет данные пользователя"""
        data = self._load_data()
        
        if 'users' not in data:
            old_data = data.copy()
            data = {"users": old_data, "recipes": {}, "meal_plans": {}, "shopping_lists": {}, "reminders": {}}
        
        user_data['last_active'] = datetime.now().isoformat()
        user_data['weight_history'] = user_data.get('weight_history', [])
        user_data['weighing_settings'] = user_data.get('weighing_settings', {})
        
        data["users"][str(user_id)] = user_data
        self._save_data(data)
    
    def update_user(self, user_id: int, **kwargs):
        """Обновляет данные пользователя"""
        data = self._load_data()
        
        if 'users' not in data:
            return False
            
        if str(user_id) in data["users"]:
            data["users"][str(user_id)].update(kwargs)
            data["users"][str(user_id)]['last_active'] = datetime.now().isoformat()
            self._save_data(data)
            return True
        return False
    
    def user_exists(self, user_id: int) -> bool:
        """Проверяет, существует ли пользователь"""
        data = self._load_data()
        
        if 'users' in data:
            return str(user_id) in data["users"]
        else:
            return str(user_id) in data
    
    def add_weight_record(self, user_id: int, weight: float):
        """Добавляет запись о весе в историю"""
        data = self._load_data()
        
        if 'users' not in data:
            return False
            
        user_str = str(user_id)
        if user_str in data["users"]:
            if 'weight_history' not in data["users"][user_str]:
                data["users"][user_str]['weight_history'] = []
            
            data["users"][user_str]['weight_history'].append({
                'date': datetime.now().isoformat(),
                'weight': weight
            })
            
            data["users"][user_str]['weight'] = weight
            
            self._save_data(data)
            return True
        return False
    
    def get_weight_history(self, user_id: int) -> List[Dict]:
        """Получает историю веса пользователя"""
        user = self.get_user(user_id)
        return user.get('weight_history', []) if user else []
    
    # ==================== РЕЦЕПТЫ ====================
    
    def add_recipe(self, user_id: int, recipe_data: Dict) -> int:
        """Добавляет рецепт пользователя"""
        data = self._load_data()
        
        if 'users' not in data:
            data = {"users": data, "recipes": {}, "meal_plans": {}, "shopping_lists": {}, "reminders": {}}
        
        if 'recipes' not in data:
            data['recipes'] = {}
        
        recipe_id = str(len(data["recipes"]) + 1)
        while recipe_id in data["recipes"]:
            recipe_id = str(int(recipe_id) + 1)
        
        recipe_data['id'] = recipe_id
        recipe_data['user_id'] = str(user_id)
        recipe_data['created_at'] = datetime.now().isoformat()
        
        data["recipes"][recipe_id] = recipe_data
        self._save_data(data)
        return int(recipe_id)
    
    def get_user_recipes(self, user_id: int) -> List[Dict]:
        """Получает все рецепты пользователя"""
        data = self._load_data()
        
        if 'users' not in data or 'recipes' not in data:
            return []
            
        user_str = str(user_id)
        return [r for r in data["recipes"].values() if r.get('user_id') == user_str]
    
    def get_recipe(self, recipe_id: int) -> Optional[Dict]:
        """Получает рецепт по ID"""
        data = self._load_data()
        
        if 'recipes' not in data:
            return None
            
        return data["recipes"].get(str(recipe_id))
    
    def filter_recipes(self, user_id: int, time_category: str = None, price_category: str = None) -> List[Dict]:
        """Фильтрует рецепты по категориям"""
        recipes = self.get_user_recipes(user_id)
        
        if time_category and time_category != "all":
            recipes = [r for r in recipes if r.get('time_category') == time_category]
        
        if price_category and price_category != "all":
            recipes = [r for r in recipes if r.get('price_category') == price_category]
        
        return recipes
    
    def search_recipes(self, user_id: int, query: str) -> List[Dict]:
        """Ищет рецепты по названию"""
        recipes = self.get_user_recipes(user_id)
        query = query.lower()
        return [r for r in recipes if query in r.get('name', '').lower()]
    
    # ==================== ПЛАНЫ ПИТАНИЯ ====================
    
    def get_active_meal_plan(self, user_id: int) -> Optional[Dict]:
        """Получает активный план питания пользователя"""
        data = self._load_data()
        
        if 'users' not in data or 'meal_plans' not in data:
            return None
            
        user_str = str(user_id)
        
        if user_str in data["meal_plans"]:
            plan = data["meal_plans"][user_str]
            plan_date = datetime.fromisoformat(plan.get('created_at', '2000-01-01'))
            if datetime.now() - plan_date < timedelta(days=7):
                return plan
        return None
    
    def save_meal_plan(self, user_id: int, plan_data: Dict):
        """Сохраняет план питания пользователя"""
        data = self._load_data()
        
        if 'users' not in data:
            data = {"users": data, "recipes": {}, "meal_plans": {}, "shopping_lists": {}, "reminders": {}}
        
        if 'meal_plans' not in data:
            data['meal_plans'] = {}
            
        user_str = str(user_id)
        
        plan_data['created_at'] = datetime.now().isoformat()
        plan_data['user_id'] = user_str
        
        data["meal_plans"][user_str] = plan_data
        self._save_data(data)
    
    # ==================== СПИСКИ ПОКУПОК ====================
    
    def get_shopping_list(self, user_id: int) -> Optional[Dict]:
        """Получает список покупок пользователя"""
        data = self._load_data()
        
        if 'users' not in data or 'shopping_lists' not in data:
            return None
            
        return data["shopping_lists"].get(str(user_id))
    
    def save_shopping_list(self, user_id: int, shopping_data: Dict):
        """Сохраняет список покупок"""
        data = self._load_data()
        
        if 'users' not in data:
            data = {"users": data, "recipes": {}, "meal_plans": {}, "shopping_lists": {}, "reminders": {}}
        
        if 'shopping_lists' not in data:
            data['shopping_lists'] = {}
            
        user_str = str(user_id)
        
        shopping_data['updated_at'] = datetime.now().isoformat()
        data["shopping_lists"][user_str] = shopping_data
        self._save_data(data)
    
    def clear_shopping_list(self, user_id: int):
        """Очищает список покупок"""
        data = self._load_data()
        
        if 'users' not in data or 'shopping_lists' not in data:
            return
            
        user_str = str(user_id)
        
        if user_str in data["shopping_lists"]:
            data["shopping_lists"][user_str] = {'items': [], 'updated_at': datetime.now().isoformat()}
            self._save_data(data)
    
    # ==================== НАПОМИНАНИЯ ====================
    
    def get_user_reminders(self, user_id: int) -> List[Dict]:
        """Получает все напоминания пользователя"""
        data = self._load_data()
        
        if 'users' not in data or 'reminders' not in data:
            return []
            
        user_str = str(user_id)
        
        if user_str not in data["reminders"]:
            return []
        
        return [r for r in data["reminders"][user_str].values() if r.get('active', True)]
    
    def add_reminder(self, user_id: int, reminder_data: Dict) -> int:
        """Добавляет напоминание"""
        data = self._load_data()
        
        if 'users' not in data:
            data = {"users": data, "recipes": {}, "meal_plans": {}, "shopping_lists": {}, "reminders": {}}
        
        if 'reminders' not in data:
            data['reminders'] = {}
            
        user_str = str(user_id)
        
        if user_str not in data["reminders"]:
            data["reminders"][user_str] = {}
        
        reminder_id = str(len(data["reminders"][user_str]) + 1)
        while reminder_id in data["reminders"][user_str]:
            reminder_id = str(int(reminder_id) + 1)
        
        reminder_data['id'] = reminder_id
        reminder_data['created_at'] = datetime.now().isoformat()
        reminder_data['active'] = True
        
        data["reminders"][user_str][reminder_id] = reminder_data
        self._save_data(data)
        return int(reminder_id)
    
    def update_reminder(self, user_id: int, reminder_id: int, **kwargs):
        """Обновляет напоминание"""
        data = self._load_data()
        
        if 'users' not in data or 'reminders' not in data:
            return False
            
        user_str = str(user_id)
        rem_id = str(reminder_id)
        
        if user_str in data["reminders"] and rem_id in data["reminders"][user_str]:
            data["reminders"][user_str][rem_id].update(kwargs)
            self._save_data(data)
            return True
        return False
    
    def delete_reminder(self, user_id: int, reminder_id: int):
        """Удаляет напоминание"""
        data = self._load_data()
        
        if 'users' not in data or 'reminders' not in data:
            return False
            
        user_str = str(user_id)
        rem_id = str(reminder_id)
        
        if user_str in data["reminders"] and rem_id in data["reminders"][user_str]:
            del data["reminders"][user_str][rem_id]
            self._save_data(data)
            return True
        return False
    
    def pause_reminder(self, user_id: int, reminder_id: int, days: int):
        """Приостанавливает напоминание на указанное количество дней"""
        data = self._load_data()
        
        if 'users' not in data or 'reminders' not in data:
            return False
            
        user_str = str(user_id)
        rem_id = str(reminder_id)
        
        if user_str in data["reminders"] and rem_id in data["reminders"][user_str]:
            pause_until = (datetime.now() + timedelta(days=days)).isoformat()
            data["reminders"][user_str][rem_id]['paused_until'] = pause_until
            self._save_data(data)
            return True
        return False

# Создаем глобальный экземпляр базы данных
db = UserDatabase("users_data.json")

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def calculate_bmi(weight: float, height: float) -> float:
    """Расчет ИМТ"""
    height_m = height / 100
    return round(weight / (height_m ** 2), 1)

def calculate_calories(gender: str, weight: float, height: float, age: int) -> int:
    """Расчет калорий по формуле Миффлина-Сан Жеора"""
    if "Мужской" in gender:
        calories = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        calories = (10 * weight) + (6.25 * height) - (5 * age) - 161
    
    return round(calories)

def get_bmi_category(bmi: float) -> str:
    """Определение категории ИМТ"""
    if bmi < 18.5:
        return "Недостаточный вес"
    elif bmi < 25:
        return "Нормальный вес"
    elif bmi < 30:
        return "Избыточный вес"
    else:
        return "Ожирение"

def recalculate_user_data(user_data: Dict) -> Dict:
    """Пересчет ИМТ и калорий после изменения данных"""
    weight = user_data.get('weight')
    height = user_data.get('height')
    age = user_data.get('age')
    gender = user_data.get('gender')
    goal = user_data.get('goal')
    
    if not all([weight, height, age, gender, goal]):
        return user_data
    
    bmi = calculate_bmi(weight, height)
    bmi_category = get_bmi_category(bmi)
    calories = calculate_calories(gender, weight, height, age)
    
    if goal == "⚖️ Похудеть":
        calories = int(calories * 0.85)
        goal_desc = "дефицит калорий"
    elif goal == "💪 Набрать мышечную массу":
        calories = int(calories * 1.15)
        goal_desc = "профицит калорий"
    else:
        goal_desc = "поддержание формы"
    
    return {
        'bmi': bmi,
        'bmi_category': bmi_category,
        'daily_calories': calories,
        'goal_description': goal_desc
    }

def generate_meal_plan(goal: str, budget: int = None, daily_calories: int = 2000) -> Dict:
    """Генерирует план питания на неделю"""
    
    breakfasts = [
        "Овсянка с фруктами", "Яичница с помидорами", "Сырники со сметаной",
        "Гречка с молоком", "Творог с ягодами", "Омлет с сыром", "Смузи боул"
    ]
    lunches = [
        "Курица с гречкой", "Рыба с рисом", "Борщ со сметаной", 
        "Паста с курицей", "Овощное рагу", "Плов", "Греческий салат"
    ]
    dinners = [
        "Творог", "Рыба на пару", "Куриное филе с овощами",
        "Омлет", "Салат с тунцом", "Запеканка", "Кефир"
    ]
    snacks = [
        "Яблоко", "Орехи", "Йогурт", "Банан", "Протеиновый батончик"
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
    
    if budget and budget < 3000:
        for day in plan:
            plan[day]["завтрак"] = plan[day]["завтрак"].replace("с фруктами", "").replace("с ягодами", "")
            plan[day]["обед"] = plan[day]["обед"].replace("с курицей", "").replace("с рыбой", "")
    
    return plan

def generate_shopping_list(meal_plan: Dict) -> Dict:
    """Генерирует список покупок из плана питания"""
    
    ingredients_db = {
        "Овсянка с фруктами": [{"name": "Овсянка", "quantity": "500 г"}, {"name": "Фрукты", "quantity": "500 г"}],
        "Яичница с помидорами": [{"name": "Яйца", "quantity": "10 шт"}, {"name": "Помидоры", "quantity": "500 г"}],
        "Сырники со сметаной": [{"name": "Творог", "quantity": "500 г"}, {"name": "Сметана", "quantity": "200 г"}],
        "Гречка с молоком": [{"name": "Гречка", "quantity": "500 г"}, {"name": "Молоко", "quantity": "1 л"}],
        "Творог с ягодами": [{"name": "Творог", "quantity": "400 г"}, {"name": "Ягоды", "quantity": "300 г"}],
        "Омлет с сыром": [{"name": "Яйца", "quantity": "8 шт"}, {"name": "Сыр", "quantity": "200 г"}],
        "Смузи боул": [{"name": "Фрукты", "quantity": "500 г"}, {"name": "Йогурт", "quantity": "300 г"}],
        "Курица с гречкой": [{"name": "Куриное филе", "quantity": "800 г"}, {"name": "Гречка", "quantity": "500 г"}],
        "Рыба с рисом": [{"name": "Рыба", "quantity": "600 г"}, {"name": "Рис", "quantity": "500 г"}],
        "Борщ со сметаной": [{"name": "Свекла", "quantity": "300 г"}, {"name": "Капуста", "quantity": "500 г"}, {"name": "Мясо", "quantity": "400 г"}],
        "Паста с курицей": [{"name": "Паста", "quantity": "500 г"}, {"name": "Куриное филе", "quantity": "400 г"}],
        "Овощное рагу": [{"name": "Овощи", "quantity": "1 кг"}],
        "Плов": [{"name": "Рис", "quantity": "500 г"}, {"name": "Мясо", "quantity": "500 г"}],
        "Греческий салат": [{"name": "Овощи", "quantity": "800 г"}, {"name": "Сыр фета", "quantity": "200 г"}],
        "Рыба на пару": [{"name": "Рыба", "quantity": "400 г"}],
        "Куриное филе с овощами": [{"name": "Куриное филе", "quantity": "500 г"}, {"name": "Овощи", "quantity": "500 г"}],
        "Салат с тунцом": [{"name": "Тунец", "quantity": "200 г"}, {"name": "Овощи", "quantity": "400 г"}],
        "Запеканка": [{"name": "Творог", "quantity": "500 г"}, {"name": "Яйца", "quantity": "3 шт"}],
    }
    
    aggregated = {}
    
    for day, meals in meal_plan.items():
        for meal_type, dish in meals.items():
            if dish in ingredients_db:
                for ingredient in ingredients_db[dish]:
                    name = ingredient["name"]
                    quantity = ingredient["quantity"]
                    
                    if name in aggregated:
                        aggregated[name] = f"{aggregated[name]} + {quantity}"
                    else:
                        aggregated[name] = quantity
    
    if not aggregated:
        return {
            "items": [
                {"name": "Яйца", "quantity": "10 шт"},
                {"name": "Куриное филе", "quantity": "800 г"},
                {"name": "Гречка", "quantity": "500 г"},
                {"name": "Рис", "quantity": "500 г"},
                {"name": "Овощи", "quantity": "1 кг"},
                {"name": "Фрукты", "quantity": "1 кг"},
                {"name": "Йогурт", "quantity": "4 шт"},
                {"name": "Творог", "quantity": "400 г"}
            ]
        }
    
    items = [{"name": name, "quantity": qty} for name, qty in aggregated.items()]
    
    return {"items": items}

def get_motivational_message(goal: str, weight_change: float, total_lost: float = None, remaining: float = None) -> str:
    """Генерирует мотивирующее сообщение на основе изменения веса"""
    
    if goal == "⚖️ Похудеть":
        if weight_change < 0:
            abs_change = abs(weight_change)
            return (
                f"🔥 ОТЛИЧНЫЙ РЕЗУЛЬТАТ!\n"
                f"Ты сбросил(а) {abs_change:.1f} кг за неделю. Так держать! "
                f"Твоя дисциплина приносит плоды.\n\n"
                f"Потеряно за всё время: {total_lost:.1f} кг\n"
                f"Осталось до цели: {remaining:.1f} кг\n\n"
            )
        elif weight_change == 0:
            return (
                f"⏸️ ПЛАТО — ЭТО НОРМАЛЬНО!\n"
                f"Вес остался на месте. Организм адаптируется. "
                f"Попробуй добавить активность или изменить рацион.\n\n"
                f"Не сдавайся! У тебя получится 💪"
            )
        else:
            return (
                f"😊 НЕ ПЕРЕЖИВАЙ!\n"
                f"Небольшие колебания — это нормально. Возможно, задержка воды.\n\n"
                f"Вспомни, был ли вчера плотный ужин? Давай вернёмся к плану питания!"
            )
    
    elif goal == "💪 Набрать мышечную массу":
        if weight_change > 0:
            return (
                f"💪 МАССА РАСТЁТ!\n"
                f"+{weight_change:.1f} кг за неделю. Отличный результат!\n\n"
                f"Продолжай соблюдать режим тренировок и профицит калорий!"
            )
        elif weight_change < 0:
            return (
                f"⚠️ ВНИМАНИЕ!\n"
                f"Ты потерял {abs(weight_change):.1f} кг, а твоя цель — набор массы.\n\n"
                f"Возможно, стоит увеличить калорийность рациона или пересмотреть тренировки."
            )
        else:
            return (
                f"📊 СТАБИЛЬНОСТЬ\n"
                f"Вес не изменился. Для набора массы нужно небольшое увеличение калорий."
            )
    
    else:
        if abs(weight_change) < 0.5:
            return (
                f"✅ СТАБИЛЬНОСТЬ — ПРИЗНАК МАСТЕРСТВА!\n"
                f"Вес в норме. Ты отлично поддерживаешь форму.\n"
                f"Так держать! 💪"
            )
        else:
            return (
                f"📊 НЕБОЛЬШИЕ КОЛЕБАНИЯ\n"
                f"Вес изменился на {abs(weight_change):.1f} кг. "
                f"Это нормально, просто продолжай следовать плану."
            )
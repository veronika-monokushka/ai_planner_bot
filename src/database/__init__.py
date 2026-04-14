#src/database/__init__.py
"""Модуль для работы с базой данных"""

from .base import BaseRepository
from .users import UserRepository
from .recipes import RecipeRepository
from .meal_plans import MealPlanRepository
from .shopping_lists import ShoppingListRepository
from .reminders import ReminderRepository
from .calculators import (
    calculate_bmi,
    calculate_calories,
    get_bmi_category,
    recalculate_user_data,
    get_motivational_message
)


class Database:
    """Главный класс для работы с БД, объединяет все репозитории"""
    
    def __init__(self, filename: str = "users_data.json"):
        self.filename = filename
        self.users = UserRepository(filename)
        self.recipes = RecipeRepository(filename)
        self.meal_plans = MealPlanRepository(filename)
        self.shopping_lists = ShoppingListRepository(filename)
        self.reminders = ReminderRepository(filename)
    
    # ==================== ПОЛЬЗОВАТЕЛИ ====================
    
    def get_user(self, user_id: int):
        """Получает пользователя"""
        return self.users.get_user(user_id)
    
    def save_user(self, user_id: int, user_data: dict):
        """Сохраняет пользователя"""
        return self.users.save_user(user_id, user_data)
    
    def update_user(self, user_id: int, **kwargs):
        """Обновляет пользователя"""
        return self.users.update_user(user_id, **kwargs)
    
    def user_exists(self, user_id: int) -> bool:
        """Проверяет существование пользователя"""
        return self.users.user_exists(user_id)
    
    def add_weight_record(self, user_id: int, weight: float):
        """Добавляет запись о весе"""
        return self.users.add_weight_record(user_id, weight)
    
    def get_weight_history(self, user_id: int):
        """Получает историю веса"""
        return self.users.get_weight_history(user_id)
    
    # ==================== ПЛАНЫ ПИТАНИЯ ====================
    
    def save_meal_plan(self, user_id: int, plan_data: dict):
        """Сохраняет план питания"""
        return self.meal_plans.save_plan(user_id, plan_data)
    
    def get_active_meal_plan(self, user_id: int):
        """Получает активный план"""
        return self.meal_plans.get_active_plan(user_id)
    
    # ==================== РЕЦЕПТЫ ====================
    
    def add_recipe(self, user_id: int, recipe_data: dict) -> int:
        """Добавляет рецепт"""
        return self.recipes.add_recipe(user_id, recipe_data)
    
    def get_user_recipes(self, user_id: int):
        """Получает рецепты пользователя"""
        return self.recipes.get_user_recipes(user_id)
    
    def get_recipe(self, recipe_id: int):
        """Получает рецепт по ID"""
        return self.recipes.get_recipe(recipe_id)
    
    def filter_recipes(self, user_id: int, time_category: str = None, price_category: str = None):
        """Фильтрует рецепты"""
        return self.recipes.filter_recipes(user_id, time_category, price_category)
    
    def search_recipes(self, user_id: int, query: str):
        """Ищет рецепты"""
        return self.recipes.search_recipes(user_id, query)
    
    # ==================== СПИСКИ ПОКУПОК ====================
    
    def get_shopping_list(self, user_id: int):
        """Получает список покупок"""
        return self.shopping_lists.get_list(user_id)
    
    def save_shopping_list(self, user_id: int, items_by_variant: dict):
        """Сохраняет список покупок"""
        return self.shopping_lists.save_list(user_id, items_by_variant)
    
    def clear_shopping_list(self, user_id: int):
        """Очищает список покупок"""
        return self.shopping_lists.clear_list(user_id)
    
    # ==================== НАПОМИНАНИЯ ====================
    
    def get_user_reminders(self, user_id: int):
        """Получает напоминания"""
        return self.reminders.get_reminders(user_id)
    
    def add_reminder(self, user_id: int, reminder_data: dict) -> int:
        """Добавляет напоминание"""
        return self.reminders.add_reminder(user_id, reminder_data)
    
    def update_reminder(self, user_id: int, reminder_id: int, **kwargs):
        """Обновляет напоминание"""
        return self.reminders.update_reminder(user_id, reminder_id, **kwargs)
    
    def delete_reminder(self, user_id: int, reminder_id: int):
        """Удаляет напоминание"""
        return self.reminders.delete_reminder(user_id, reminder_id)
    
    def pause_reminder(self, user_id: int, reminder_id: int, days: int):
        """Приостанавливает напоминание"""
        return self.reminders.pause_reminder(user_id, reminder_id, days)


# Создаем глобальный экземпляр базы данных
db = Database("users_data.json")


# Экспортируем все для удобства
__all__ = [
    'Database',
    'UserRepository',
    'RecipeRepository',
    'MealPlanRepository',
    'ShoppingListRepository',
    'ReminderRepository',
    'BaseRepository',
    'calculate_bmi',
    'calculate_calories',
    'get_bmi_category',
    'recalculate_user_data',
    'get_motivational_message',
    'db'
]
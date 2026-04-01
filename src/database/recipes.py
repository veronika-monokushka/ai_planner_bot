"""Работа с рецептами"""

from typing import Optional, Dict, List
from datetime import datetime

from .base import BaseRepository


class RecipeRepository(BaseRepository):
    """Репозиторий для работы с рецептами"""
    
    def add_recipe(self, user_id: int, recipe_data: Dict) -> int:
        """Добавляет рецепт пользователя"""
        data = self._load_data()
        
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
        user_str = str(user_id)
        return [r for r in data["recipes"].values() if r.get('user_id') == user_str]
    
    def get_recipe(self, recipe_id: int) -> Optional[Dict]:
        """Получает рецепт по ID"""
        data = self._load_data()
        return data["recipes"].get(str(recipe_id))
    
    def filter_recipes(
        self, 
        user_id: int, 
        time_category: str = None, 
        price_category: str = None
    ) -> List[Dict]:
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
    
    def delete_recipe(self, user_id: int, recipe_id: int) -> bool:
        """Удаляет рецепт"""
        data = self._load_data()
        user_str = str(user_id)
        rec_id = str(recipe_id)
        
        if rec_id in data["recipes"] and data["recipes"][rec_id].get('user_id') == user_str:
            del data["recipes"][rec_id]
            self._save_data(data)
            return True
        return False
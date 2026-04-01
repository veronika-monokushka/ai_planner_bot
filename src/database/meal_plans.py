"""Работа с планами питания"""

from typing import Optional, Dict
from datetime import datetime, timedelta

from .base import BaseRepository


class MealPlanRepository(BaseRepository):
    """Репозиторий для работы с планами питания"""
    
    def get_active_plan(self, user_id: int) -> Optional[Dict]:
        """Получает активный план питания пользователя"""
        data = self._load_data()
        user_str = str(user_id)
        
        if user_str in data["meal_plans"]:
            plan = data["meal_plans"][user_str]
            plan_date = datetime.fromisoformat(plan.get('created_at', '2000-01-01'))
            if datetime.now() - plan_date < timedelta(days=7):
                return plan
        return None
    
    def save_plan(self, user_id: int, plan_data: Dict):
        """Сохраняет план питания пользователя"""
        data = self._load_data()
        user_str = str(user_id)
        
        plan_data['created_at'] = datetime.now().isoformat()
        plan_data['user_id'] = user_str
        
        data["meal_plans"][user_str] = plan_data
        self._save_data(data)
    
    def archive_plan(self, user_id: int):
        """Архивирует текущий план (создает копию с меткой времени)"""
        data = self._load_data()
        user_str = str(user_id)
        
        if user_str in data["meal_plans"]:
            plan = data["meal_plans"][user_str]
            archive_key = f"{user_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if 'archived_plans' not in data:
                data['archived_plans'] = {}
            
            data['archived_plans'][archive_key] = plan
            self._save_data(data)
            return True
        return False
    
    def get_all_plans(self, user_id: int) -> list:
        """Получает все планы пользователя (включая архивные)"""
        data = self._load_data()
        user_str = str(user_id)
        plans = []
        
        if user_str in data["meal_plans"]:
            plans.append(data["meal_plans"][user_str])
        
        if 'archived_plans' in data:
            for key, plan in data['archived_plans'].items():
                if plan.get('user_id') == user_str:
                    plans.append(plan)
        
        return plans
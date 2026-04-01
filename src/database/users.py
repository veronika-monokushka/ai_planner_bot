"""Работа с пользователями"""

import json
import os
from typing import Optional, Dict, List
from datetime import datetime

from .base import BaseRepository


class UserRepository(BaseRepository):
    """Репозиторий для работы с пользователями"""
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получает данные пользователя по ID"""
        data = self._load_data()
        return data["users"].get(str(user_id))
    
    def save_user(self, user_id: int, user_data: Dict):
        """Сохраняет данные пользователя"""
        data = self._load_data()
        
        user_data['last_active'] = datetime.now().isoformat()
        user_data['weight_history'] = user_data.get('weight_history', [])
        user_data['weighing_settings'] = user_data.get('weighing_settings', {})
        
        data["users"][str(user_id)] = user_data
        self._save_data(data)
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Обновляет данные пользователя"""
        data = self._load_data()
        user_str = str(user_id)
        
        if user_str in data["users"]:
            data["users"][user_str].update(kwargs)
            data["users"][user_str]['last_active'] = datetime.now().isoformat()
            self._save_data(data)
            return True
        return False
    
    def user_exists(self, user_id: int) -> bool:
        """Проверяет, существует ли пользователь"""
        data = self._load_data()
        return str(user_id) in data["users"]
    
    def add_weight_record(self, user_id: int, weight: float) -> bool:
        """Добавляет запись о весе в историю"""
        data = self._load_data()
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
    
    def get_all_users(self) -> Dict:
        """Получает всех пользователей"""
        data = self._load_data()
        return data["users"]
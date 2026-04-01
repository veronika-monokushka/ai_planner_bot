"""Работа с напоминаниями"""

from typing import Optional, Dict, List
from datetime import datetime, timedelta

from .base import BaseRepository


class ReminderRepository(BaseRepository):
    """Репозиторий для работы с напоминаниями"""
    
    def get_reminders(self, user_id: int) -> List[Dict]:
        """Получает все активные напоминания пользователя"""
        data = self._load_data()
        user_str = str(user_id)
        
        if user_str not in data["reminders"]:
            return []
        
        reminders = []
        for r in data["reminders"][user_str].values():
            if not r.get('active', True):
                continue
            
            # Проверяем, не на паузе ли напоминание
            paused_until = r.get('paused_until')
            if paused_until:
                if datetime.now().isoformat() < paused_until:
                    continue
            
            reminders.append(r)
        
        return reminders
    
    def get_all_reminders(self, user_id: int) -> List[Dict]:
        """Получает все напоминания пользователя (включая неактивные)"""
        data = self._load_data()
        user_str = str(user_id)
        
        if user_str not in data["reminders"]:
            return []
        
        return list(data["reminders"][user_str].values())
    
    def add_reminder(self, user_id: int, reminder_data: Dict) -> int:
        """Добавляет напоминание"""
        data = self._load_data()
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
    
    def update_reminder(self, user_id: int, reminder_id: int, **kwargs) -> bool:
        """Обновляет напоминание"""
        data = self._load_data()
        user_str = str(user_id)
        rem_id = str(reminder_id)
        
        if user_str in data["reminders"] and rem_id in data["reminders"][user_str]:
            data["reminders"][user_str][rem_id].update(kwargs)
            self._save_data(data)
            return True
        return False
    
    def delete_reminder(self, user_id: int, reminder_id: int) -> bool:
        """Удаляет напоминание"""
        data = self._load_data()
        user_str = str(user_id)
        rem_id = str(reminder_id)
        
        if user_str in data["reminders"] and rem_id in data["reminders"][user_str]:
            del data["reminders"][user_str][rem_id]
            self._save_data(data)
            return True
        return False
    
    def pause_reminder(self, user_id: int, reminder_id: int, days: int) -> bool:
        """Приостанавливает напоминание на указанное количество дней"""
        data = self._load_data()
        user_str = str(user_id)
        rem_id = str(reminder_id)
        
        if user_str in data["reminders"] and rem_id in data["reminders"][user_str]:
            pause_until = (datetime.now() + timedelta(days=days)).isoformat()
            data["reminders"][user_str][rem_id]['paused_until'] = pause_until
            self._save_data(data)
            return True
        return False
    
    def activate_reminder(self, user_id: int, reminder_id: int) -> bool:
        """Активирует напоминание (снимает паузу)"""
        data = self._load_data()
        user_str = str(user_id)
        rem_id = str(reminder_id)
        
        if user_str in data["reminders"] and rem_id in data["reminders"][user_str]:
            data["reminders"][user_str][rem_id]['active'] = True
            data["reminders"][user_str][rem_id].pop('paused_until', None)
            self._save_data(data)
            return True
        return False
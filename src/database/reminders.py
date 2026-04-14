#src/database/reminders.py
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
    
    

    def get_due_reminders(self, current_time: datetime) -> List[Dict]:
        """
        Получает все напоминания, которые должны сработать в текущий момент.
        Абстрагирует логику проверки от формата хранения.
        
        Args:
            current_time: Текущее время для проверки
            
        Returns:
            List[Dict]: Список напоминаний, которые нужно отправить
        """
        data = self._load_data()
        due_reminders = []
        
        current_time_str = current_time.strftime("%H:%M")
        current_weekday_ru = self._get_weekday_ru(current_time)
        
        if 'reminders' not in data:
            return []
        
        for user_id_str, user_reminders in data['reminders'].items():
            user_id = int(user_id_str)
            
            for reminder_id, reminder in user_reminders.items():
                if not self._is_reminder_active(reminder, current_time):
                    continue
                
                if self._is_reminder_due(reminder, current_time, current_time_str, current_weekday_ru):
                    reminder['user_id'] = user_id
                    reminder['id'] = int(reminder_id)
                    due_reminders.append(reminder)
        
        return due_reminders
    
    def mark_reminder_sent(self, user_id: int, reminder_id: int, sent_time: datetime):
        """Отмечает напоминание как отправленное (обновляет last_sent)"""
        reminder = self.get_reminder_by_id(user_id, reminder_id)
        if reminder and reminder.get('periodicity') == 'interval':
            self.update_reminder(user_id, reminder_id, last_sent=sent_time.isoformat())
        elif reminder and reminder.get('periodicity') == 'once':
            self.update_reminder(user_id, reminder_id, active=False)
    
    def get_reminder_by_id(self, user_id: int, reminder_id: int) -> Optional[Dict]:
        """Получает напоминание по ID"""
        data = self._load_data()
        user_str = str(user_id)
        rem_id = str(reminder_id)
        
        if user_str in data.get('reminders', {}) and rem_id in data['reminders'][user_str]:
            reminder = data['reminders'][user_str][rem_id].copy()
            reminder['id'] = int(reminder_id)
            reminder['user_id'] = user_id
            return reminder
        return None
    
    # ==================== ПРИВАТНЫЕ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    def _is_reminder_active(self, reminder: dict, current_time: datetime) -> bool:
        """Проверяет, активно ли напоминание (не отключено и не на паузе)"""
        if not reminder.get('active', True):
            return False
        
        paused_until = reminder.get('paused_until')
        if paused_until:
            if current_time < datetime.fromisoformat(paused_until):
                return False
        
        return True
    
    def _is_reminder_due(self, reminder: dict, current_time: datetime, 
                         current_time_str: str, current_weekday_ru: str) -> bool:
        """Проверяет, должно ли напоминание сработать сейчас"""
        periodicity = reminder.get('periodicity')
        
        # Ежедневные
        if periodicity == 'daily' or periodicity == 'Каждый день':
            return reminder.get('time') == current_time_str
        
        # Интервальные
        elif periodicity == 'interval' or periodicity == 'Раз в несколько часов':
            return self._is_interval_reminder_due(reminder, current_time)
        
        # Еженедельные
        elif periodicity == 'weekly' or periodicity == 'По дням недели':
            weekdays = reminder.get('weekdays', [])
            return current_weekday_ru in weekdays and reminder.get('time') == current_time_str
        
        # Одноразовые
        elif periodicity == 'once' or periodicity == 'Один раз':
            return self._is_once_reminder_due(reminder, current_time)
        
        return False
    
    def _is_interval_reminder_due(self, reminder: dict, current_time: datetime) -> bool:
        """Проверяет интервальное напоминание"""
        if 'last_sent' in reminder:
            last_sent = datetime.fromisoformat(reminder['last_sent'])
            interval = reminder.get('interval', 1)
            if (current_time - last_sent).total_seconds() >= interval * 3600:
                return self._check_start_time(reminder, current_time)
        else:
            return self._check_start_time(reminder, current_time)
        return False
    
    def _is_once_reminder_due(self, reminder: dict, current_time: datetime) -> bool:
        """Проверяет одноразовое напоминание"""
        if 'datetime' in reminder:
            reminder_dt = datetime.fromisoformat(reminder['datetime'])
            return (reminder_dt.year == current_time.year and
                    reminder_dt.month == current_time.month and
                    reminder_dt.day == current_time.day and
                    reminder_dt.hour == current_time.hour and
                    reminder_dt.minute == current_time.minute)
        return False
    
    def _check_start_time(self, reminder: dict, current_time: datetime) -> bool:
        """Проверяет, прошло ли время старта"""
        if reminder.get('time'):
            start_time = datetime.strptime(reminder['time'], "%H:%M").time()
            return current_time.time() >= start_time
        return True
    
    def _get_weekday_ru(self, dt: datetime) -> str:
        """Возвращает название дня недели на русском"""
        weekday_map = {
            'Monday': 'ПН', 'Tuesday': 'ВТ', 'Wednesday': 'СР',
            'Thursday': 'ЧТ', 'Friday': 'ПТ', 'Saturday': 'СБ', 'Sunday': 'ВС'
        }
        return weekday_map.get(dt.strftime("%A"), '')
    
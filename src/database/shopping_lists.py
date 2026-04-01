"""Работа со списками покупок"""

from typing import Dict

from .base import BaseRepository


class ShoppingListRepository(BaseRepository):
    """Репозиторий для работы со списками покупок"""
    
    def get_list(self, user_id: int) -> Dict:
        """Получает список покупок пользователя"""
        data = self._load_data()
        user_str = str(user_id)
        result = data["shopping_lists"].get(user_str, {})
        
        if not result:
            return {}
        
        # Если это список (старый формат), конвертируем в словарь по вариантам
        if isinstance(result, list):
            return {"Вариант 1": result}
        
        # Если это словарь с ключом 'items' (старый формат)
        if 'items' in result:
            return {"Вариант 1": result['items']}
        
        return result
    
    def save_list(self, user_id: int, items_by_variant: Dict):
        """Сохраняет список покупок пользователя (с разделением по вариантам)"""
        data = self._load_data()
        user_str = str(user_id)
        
        # Убеждаемся, что данные в правильном формате
        validated_items = self._validate_items(items_by_variant)
        
        data["shopping_lists"][user_str] = validated_items
        self._save_data(data)
    
    def clear_list(self, user_id: int):
        """Очищает список покупок"""
        data = self._load_data()
        user_str = str(user_id)
        
        if user_str in data["shopping_lists"]:
            data["shopping_lists"][user_str] = {}
            self._save_data(data)
    
    def _validate_items(self, items_by_variant: Dict) -> Dict:
        """Валидирует и приводит данные к правильному формату"""
        validated_items = {}
        
        for variant, items in items_by_variant.items():
            if isinstance(items, list):
                validated_list = []
                for item in items:
                    if isinstance(item, dict):
                        validated_list.append({
                            "name": item.get('name', str(item)),
                            "quantity": item.get('quantity', '1 шт')
                        })
                    elif isinstance(item, str):
                        validated_list.append({"name": item, "quantity": "1 шт"})
                    else:
                        validated_list.append({"name": str(item), "quantity": "1 шт"})
                validated_items[variant] = validated_list
            else:
                validated_items[variant] = [{"name": str(items), "quantity": "1 шт"}]
        
        return validated_items
    
    def add_item(self, user_id: int, variant: str, name: str, quantity: str):
        """Добавляет товар в список покупок"""
        shopping_list = self.get_list(user_id)
        
        if variant not in shopping_list:
            shopping_list[variant] = []
        
        shopping_list[variant].append({"name": name, "quantity": quantity})
        self.save_list(user_id, shopping_list)
    
    def remove_item(self, user_id: int, variant: str, index: int):
        """Удаляет товар из списка покупок"""
        shopping_list = self.get_list(user_id)
        
        if variant in shopping_list and 0 <= index < len(shopping_list[variant]):
            del shopping_list[variant][index]
            self.save_list(user_id, shopping_list)
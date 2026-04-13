from langchain_core.tools import tool
from datetime import datetime


#создать, удалить, отредактировать, посмотреть

@tool
def create_reminder(user_id: int,
                    text: str,
                    remind_at: datetime,
                    repeat_type: str = "once",
                    repeat_days: list = None,
                    timezone: str = "Europe/Moscow"
                    ) -> int:
    """Создает напоминание, возвращает ID"""
    id = 0
    return id


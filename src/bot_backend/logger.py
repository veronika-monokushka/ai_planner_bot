# bot_backend/logger.py
import logging
import os

# Создаём директорию для логов, если её нет
os.makedirs("logs", exist_ok=True)

def setup_logger(name: str = None) -> logging.Logger:
    """
    Настраивает и возвращает логгер.
    
    Args:
        name: Имя логгера (обычно __name__)
    
    Returns:
        logging.Logger: Настроенный логгер
    """
    logger = logging.getLogger(name)
    
    # Чтобы не добавлять обработчики повторно
    if logger.hasHandlers():
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Формат для сообщений
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 1. Файловый обработчик (только WARNING и выше)
    file_handler = logging.FileHandler(
        "logs/bot_logs.log", 
        encoding="utf-8"
    )
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(formatter)
    
    # 2. Консольный обработчик (DEBUG и выше)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# Глобальный логгер по умолчанию (можно использовать в любом модуле)
default_logger = setup_logger("ai_planner_bot")
import os
import json
from datetime import datetime
from typing import Literal, Optional


def log_error(
    user_id: int,
    error_text: str,
    log_type: Literal["ai_response", "parse_error", "api_error", "general"] = "general",
    mode: Literal["append", "overwrite"] = "append",
    additional_data: Optional[dict] = None
) -> str:
    """
    Логирует ошибку в JSON-файл с разделением по пользователям.
    
    Args:
        user_id: ID пользователя, у которого произошла ошибка
        error_text: Текст ошибки или ответа AI (если log_type="ai_response")
        log_type: Тип ошибки
            - "ai_response": невалидный ответ от AI
            - "parse_error": ошибка парсинга JSON
            - "api_error": ошибка API
            - "general": общая ошибка
        mode: Режим записи
            - "append": дозаписать в файл (по умолчанию)
            - "overwrite": перезаписать файл
        additional_data: Дополнительные данные для логирования (опционально)
    
    Returns:
        str: Путь к файлу, куда была сохранена ошибка
    """
    # Создаем директорию logs, если её нет
    os.makedirs("logs", exist_ok=True)
    
    # Формируем имя файла с user_id
    filename = f"logs/errors_{user_id}.json"
    
    # Создаем запись об ошибке
    error_record = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "log_type": log_type,
        "error_text": error_text,
        "additional_data": additional_data or {}
    }
    
    # Читаем существующие ошибки
    existing_errors = []
    if mode == "append" and os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                existing_errors = json.load(f)
                if not isinstance(existing_errors, list):
                    existing_errors = []
        except (json.JSONDecodeError, FileNotFoundError):
            existing_errors = []
    
    # Добавляем новую ошибку
    existing_errors.append(error_record)
    
    # Сохраняем в файл
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(existing_errors, f, ensure_ascii=False, indent=2)
    
    return filename


def log_ai_response_error(
    user_id: int,
    response_text: str,
    error_details: Optional[str] = None
) -> str:
    """
    Логирует невалидный ответ от AI.
    
    Args:
        user_id: ID пользователя
        response_text: Текст ответа от AI
        error_details: Детали ошибки (например, "Невалидный JSON")
    
    Returns:
        str: Путь к файлу
    """
    return log_error(
        user_id=user_id,
        error_text=response_text,
        log_type="ai_response",
        mode="append",
        additional_data={"error_details": error_details} if error_details else None
    )


def log_parse_error(
    user_id: int,
    raw_response: str,
    exception: str
) -> str:
    """
    Логирует ошибку парсинга JSON.
    
    Args:
        user_id: ID пользователя
        raw_response: Сырой ответ от AI
        exception: Текст исключения
    
    Returns:
        str: Путь к файлу
    """
    return log_error(
        user_id=user_id,
        error_text=raw_response,
        log_type="parse_error",
        mode="append",
        additional_data={"exception": exception}
    )


def log_api_error(
    user_id: int,
    error_message: str,
    status_code: Optional[int] = None
) -> str:
    """
    Логирует ошибку API.
    
    Args:
        user_id: ID пользователя
        error_message: Текст ошибки
        status_code: HTTP статус код (опционально)
    
    Returns:
        str: Путь к файлу
    """
    return log_error(
        user_id=user_id,
        error_text=error_message,
        log_type="api_error",
        mode="append",
        additional_data={"status_code": status_code} if status_code else None
    )
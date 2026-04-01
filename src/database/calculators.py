"""Вспомогательные функции для расчетов"""

from typing import Dict


def calculate_bmi(weight: float, height: float) -> float:
    """Расчет ИМТ"""
    height_m = height / 100
    return round(weight / (height_m ** 2), 1)


def calculate_calories(gender: str, weight: float, height: float, age: int) -> int:
    """Расчет калорий по формуле Миффлина-Сан Жеора"""
    if "Мужской" in gender:
        calories = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        calories = (10 * weight) + (6.25 * height) - (5 * age) - 161
    
    return round(calories)


def get_bmi_category(bmi: float) -> str:
    """Определение категории ИМТ"""
    if bmi < 18.5:
        return "Недостаточный вес"
    elif bmi < 25:
        return "Нормальный вес"
    elif bmi < 30:
        return "Избыточный вес"
    else:
        return "Ожирение"


def recalculate_user_data(user_data: Dict) -> Dict:
    """Пересчет ИМТ и калорий после изменения данных"""
    weight = user_data.get('weight')
    height = user_data.get('height')
    age = user_data.get('age')
    gender = user_data.get('gender')
    goal = user_data.get('goal')
    
    if not all([weight, height, age, gender, goal]):
        return user_data
    
    bmi = calculate_bmi(weight, height)
    bmi_category = get_bmi_category(bmi)
    calories = calculate_calories(gender, weight, height, age)
    
    if goal == "⚖️ Похудеть":
        calories = int(calories * 0.85)
        goal_desc = "дефицит калорий"
    elif goal == "💪 Набрать мышечную массу":
        calories = int(calories * 1.15)
        goal_desc = "профицит калорий"
    else:
        goal_desc = "поддержание формы"
    
    return {
        'bmi': bmi,
        'bmi_category': bmi_category,
        'daily_calories': calories,
        'goal_description': goal_desc
    }


def get_motivational_message(
    goal: str, 
    weight_change: float, 
    total_lost: float = None, 
    remaining: float = None
) -> str:
    """Генерирует мотивирующее сообщение на основе изменения веса"""
    
    if goal == "⚖️ Похудеть":
        if weight_change < 0:
            abs_change = abs(weight_change)
            return (
                f"🔥 ОТЛИЧНЫЙ РЕЗУЛЬТАТ!\n"
                f"Ты сбросил(а) {abs_change:.1f} кг за неделю. Так держать! "
                f"Твоя дисциплина приносит плоды.\n\n"
                f"Потеряно за всё время: {total_lost:.1f} кг\n"
                f"Осталось до цели: {remaining:.1f} кг\n\n"
            )
        elif weight_change == 0:
            return (
                f"⏸️ ПЛАТО — ЭТО НОРМАЛЬНО!\n"
                f"Вес остался на месте. Организм адаптируется. "
                f"Попробуй добавить активность или изменить рацион.\n\n"
                f"Не сдавайся! У тебя получится 💪"
            )
        else:
            return (
                f"😊 НЕ ПЕРЕЖИВАЙ!\n"
                f"Небольшие колебания — это нормально. Возможно, задержка воды.\n\n"
                f"Вспомни, был ли вчера плотный ужин? Давай вернёмся к плану питания!"
            )
    
    elif goal == "💪 Набрать мышечную массу":
        if weight_change > 0:
            return (
                f"💪 МАССА РАСТЁТ!\n"
                f"+{weight_change:.1f} кг за неделю. Отличный результат!\n\n"
                f"Продолжай соблюдать режим тренировок и профицит калорий!"
            )
        elif weight_change < 0:
            return (
                f"⚠️ ВНИМАНИЕ!\n"
                f"Ты потерял {abs(weight_change):.1f} кг, а твоя цель — набор массы.\n\n"
                f"Возможно, стоит увеличить калорийность рациона или пересмотреть тренировки."
            )
        else:
            return (
                f"📊 СТАБИЛЬНОСТЬ\n"
                f"Вес не изменился. Для набора массы нужно небольшое увеличение калорий."
            )
    
    else:
        if abs(weight_change) < 0.5:
            return (
                f"✅ СТАБИЛЬНОСТЬ — ПРИЗНАК МАСТЕРСТВА!\n"
                f"Вес в норме. Ты отлично поддерживаешь форму.\n"
                f"Так держать! 💪"
            )
        else:
            return (
                f"📊 НЕБОЛЬШИЕ КОЛЕБАНИЯ\n"
                f"Вес изменился на {abs(weight_change):.1f} кг. "
                f"Это нормально, просто продолжай следовать плану."
            )
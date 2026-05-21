# bot_backend/handlers/shopping.py

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from bot_backend.states import UserState
from bot_backend.keyboards import get_shopping_list_keyboard, get_main_menu_keyboard
from database import db

from ai_agent.meals_generator import create_shopping_list_ai
from ai_agent.ai_logger import log_error
from bot_backend.logger import default_logger as logger


async def handle_shopping_list_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню списка покупок - кэширует список если план не менялся"""
    import hashlib
    
    user_id = update.effective_user.id
    
    # Получаем активный план питания
    active_plan = db.get_active_meal_plan(user_id)
    
    if not active_plan:
        await update.message.reply_text(
            "❌ Сначала создайте план питания в разделе 'План на неделю'!",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    # Проверяем кэш списка покупок
    cached_shopping = active_plan.get('shopping_list')
    cached_plan_hash = active_plan.get('plan_hash')
    
    # Вычисляем хеш текущего плана для проверки изменений
    plan_str = str(active_plan.get('plan', {}))
    current_plan_hash = hashlib.md5(plan_str.encode()).hexdigest()
    
    # Если кэш есть и план не менялся - показываем кэшированный список
    if cached_shopping and cached_plan_hash == current_plan_hash:
        await update.message.reply_text(
            cached_shopping,
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    # Если план менялся или нет кэша - регенерируем список
    # Показываем индикатор загрузки
    loading_message = await update.message.reply_text(
        "🤖 AI составляет список покупок...\n"
        "Это займет немного времени!",
        reply_markup=None
    )
    
    try:
        result = create_shopping_list_ai(user_id, active_plan)
        items = db.get_shopping_list(user_id)['cur_list']
            
        # Форматируем результат
        response = "🛒 СПИСОК ПРОДУКТОВ:\n\n"
        
        for item in items:
            name = item.get('name', 'Продукт')
            quantity = item.get('quantity', '1 шт')
            response += f"✓ {name} — {quantity}\n"

        # Сохраняем результат в кэш вместе с хешем плана
        db.save_shopping_list_cache(user_id, response, current_plan_hash)
        
        # Удаляем сообщение о загрузке
        await loading_message.delete()
        
        # Выводим результат
        await update.message.reply_text(
            response,
            reply_markup=get_main_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"ERROR: Ошибка при генерации списка покупок: {e}")
        await loading_message.delete()

        log_error(
            user_id=user_id,
            error_text=e,
            log_type='general'
        )
            
        if '429' in e:
            response_text = "Превышен лимит запросов в минуту, пожалуйста пишите не так быстро ❄"
        else:
            response_text = 'Неизвестная ошибка. Попробуйте пожалуйста снова или введите /start 😇'

        await update.message.reply_text(
            response_text,
            reply_markup=get_main_menu_keyboard()
        )
        
    
    return UserState.MAIN_MENU
# bot_backend/handlers/shopping.py

import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from bot_backend.states import UserState
from bot_backend.keyboards import get_shopping_list_keyboard, get_main_menu_keyboard
from database import db
from ai_agent.meals_generator import generate_shopping_list_ai

logger = logging.getLogger(__name__)


async def handle_shopping_list_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню списка покупок"""
    await update.message.reply_text(
        "🛒 СПИСОК ПОКУПОК\n\n"
        "Выбери действие:",
        reply_markup=get_shopping_list_keyboard()
    )
    return UserState.SHOPPING_LIST_MENU


async def handle_shopping_list_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действия со списком покупок"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "📝 Собрать список на неделю":
        active_plan = db.get_active_meal_plan(user_id)
        
        if not active_plan:
            await update.message.reply_text(
                "❌ Сначала создай план питания в разделе 'План на неделю'!",
                reply_markup=get_shopping_list_keyboard()
            )
            return UserState.SHOPPING_LIST_MENU
        
        # ✅ Показываем индикатор загрузки
        loading_message = await update.message.reply_text(
            "🤖 AI составляет список покупок...\n"
            "Это займет немного времени!",
            reply_markup=None
        )
        
        # ✅ Вызываем AI для генерации списка покупок
        result = generate_shopping_list_ai(active_plan.get('plan', {}))
        
        # ✅ Удаляем сообщение о загрузке
        await loading_message.delete()
        
        # ✅ Сохраняем результат в БД
        items_by_variant = result.get("items_by_variant", {})
        db.save_shopping_list(user_id, items_by_variant)
        
        # ✅ Форматируем вывод по вариантам
        list_text = "🛒 СПИСОК ПОКУПОК ПО ВАРИАНТАМ МЕНЮ:\n\n"
        
        for variant, items in items_by_variant.items():
            list_text += f"📋 {variant}:\n"
            for item in items:
                list_text += f"  • {item.get('name', '-')} — {item.get('quantity', '-')}\n"
            list_text += "\n"
        
        await update.message.reply_text(list_text, reply_markup=get_shopping_list_keyboard())
    
    elif text == "📋 Разделить по рецептам":
        active_plan = db.get_active_meal_plan(user_id)
        
        if not active_plan:
            await update.message.reply_text(
                "❌ Сначала создай список покупок!",
                reply_markup=get_shopping_list_keyboard()
            )
            return UserState.SHOPPING_LIST_MENU
        
        text_response = "📋 СПИСОК ПО РЕЦЕПТАМ:\n\n"
        
        for variant, meals in active_plan.get('plan', {}).items():
            text_response += f"📋 {variant}:\n"
            text_response += f"  🍳 Завтрак: {meals.get('завтрак', '-')}\n"
            text_response += f"  🍲 Обед: {meals.get('обед', '-')}\n"
            text_response += f"  🍽️ Ужин: {meals.get('ужин', '-')}\n"
            text_response += f"  🥗 Перекус: {meals.get('перекус', '-')}\n\n"
        
        await update.message.reply_text(
            text_response,
            reply_markup=get_shopping_list_keyboard()
        )
    
    elif text == "🗑️ Очистить список":
        db.clear_shopping_list(user_id)
        await update.message.reply_text(
            "✅ Список покупок очищен!",
            reply_markup=get_shopping_list_keyboard()
        )
    elif text == "🔙 Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    return UserState.SHOPPING_LIST_MENU


async def handle_create_shopping_list_from_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание списка покупок из последнего созданного плана"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "✅ Да, создать список":
        # Получаем сохраненный план из context.user_data
        plan_data = context.user_data.get('last_created_plan')
        
        if not plan_data:
            await update.message.reply_text(
                "❌ Не найден план питания. Пожалуйста, создай план заново.",
                reply_markup=get_main_menu_keyboard()
            )
            return UserState.MAIN_MENU
        
        # ✅ Показываем индикатор загрузки
        loading_message = await update.message.reply_text(
            "🤖 AI составляет список покупок...\n"
            "Это займет немного времени!",
            reply_markup=None
        )
        
        # ✅ Вызываем AI для генерации списка покупок
        result = generate_shopping_list_ai(plan_data['plan'])
        
        # ✅ Удаляем сообщение о загрузке
        await loading_message.delete()
        
        # ✅ Сохраняем результат в БД
        items_by_variant = result.get("items_by_variant", {})
        db.save_shopping_list(user_id, items_by_variant)
        
        # ✅ Форматируем вывод по вариантам
        list_text = "🛒 СПИСОК ПОКУПОК СОЗДАН!\n\n"
        
        for variant, items in items_by_variant.items():
            list_text += f"📋 {variant}:\n"
            for item in items:
                list_text += f"  • {item.get('name', '-')} — {item.get('quantity', '-')}\n"
            list_text += "\n"
        
        await update.message.reply_text(
            list_text,
            reply_markup=get_shopping_list_keyboard()
        )
        
        # Очищаем временные данные
        context.user_data.pop('last_created_plan', None)
        
        return UserState.SHOPPING_LIST_MENU
    
    elif text == "🔙 Остаться в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    else:
        await update.message.reply_text(
            "Пожалуйста, используй кнопки 👆",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("✅ Да, создать список")],
                [KeyboardButton("🔙 Остаться в меню")]
            ], resize_keyboard=True)
        )
        return UserState.MAIN_MENU
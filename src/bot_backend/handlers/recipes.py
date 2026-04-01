"""Обработчики рецептов"""

import logging
import re
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ИСПРАВЛЕНО: убрал ai_planner_bot.
from bot_backend.states import UserState, UserData
from bot_backend.keyboards import get_back_to_menu_keyboard, get_main_menu_keyboard, get_recipe_actions_inline
from database import db

logger = logging.getLogger(__name__)


async def handle_recipes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню рецептов"""
    await update.message.reply_text(
        "🍳 МОИ РЕЦЕПТЫ\n\n"
        "Выбери категорию по времени приготовления:",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("🥚 Быстрые (до 30 мин)")],
            [KeyboardButton("⏲️ Средние (30-60 мин)")],
            [KeyboardButton("🔥 Сложные (более 1 часа)")],
            [KeyboardButton("📚 Все рецепты")],
            [KeyboardButton("➕ Добавить рецепт")],
            [KeyboardButton("🔍 Поиск")],
            [KeyboardButton("🔙 Назад в меню")]
        ], resize_keyboard=True)
    )
    return UserState.RECIPES_MENU


async def handle_recipes_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Навигация по меню рецептов"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "🥚 Быстрые (до 30 мин)":
        await update.message.reply_text(
            "🥚 БЫСТРЫЕ РЕЦЕПТЫ (до 30 мин)\n\n"
            "Теперь выбери ценовую категорию:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💚 Бюджетные", callback_data="price_budget_fast")],
                [InlineKeyboardButton("💛 Средние", callback_data="price_medium_fast")],
                [InlineKeyboardButton("❤️ Дорогие", callback_data="price_expensive_fast")],
                [InlineKeyboardButton("🎲 Все быстрые", callback_data="price_all_fast")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_recipes_time")]
            ])
        )
        return UserState.RECIPES_MENU
    
    elif text == "⏲️ Средние (30-60 мин)":
        await update.message.reply_text(
            "⏲️ СРЕДНИЕ РЕЦЕПТЫ (30-60 мин)\n\n"
            "Теперь выбери ценовую категорию:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💚 Бюджетные", callback_data="price_budget_medium")],
                [InlineKeyboardButton("💛 Средние", callback_data="price_medium_medium")],
                [InlineKeyboardButton("❤️ Дорогие", callback_data="price_expensive_medium")],
                [InlineKeyboardButton("🎲 Все средние", callback_data="price_all_medium")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_recipes_time")]
            ])
        )
        return UserState.RECIPES_MENU
    
    elif text == "🔥 Сложные (более 1 часа)":
        await update.message.reply_text(
            "🔥 СЛОЖНЫЕ РЕЦЕПТЫ (более 1 часа)\n\n"
            "Теперь выбери ценовую категорию:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💚 Бюджетные", callback_data="price_budget_hard")],
                [InlineKeyboardButton("💛 Средние", callback_data="price_medium_hard")],
                [InlineKeyboardButton("❤️ Дорогие", callback_data="price_expensive_hard")],
                [InlineKeyboardButton("🎲 Все сложные", callback_data="price_all_hard")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_recipes_time")]
            ])
        )
        return UserState.RECIPES_MENU
    
    elif text == "📚 Все рецепты":
        recipes = db.get_user_recipes(user_id)
        if not recipes:
            await update.message.reply_text(
                "📚 У тебя пока нет рецептов. Добавь первый! ➕",
                reply_markup=ReplyKeyboardMarkup([
                    [KeyboardButton("🥚 Быстрые (до 30 мин)")],
                    [KeyboardButton("⏲️ Средние (30-60 мин)")],
                    [KeyboardButton("🔥 Сложные (более 1 часа)")],
                    [KeyboardButton("📚 Все рецепты")],
                    [KeyboardButton("➕ Добавить рецепт")],
                    [KeyboardButton("🔍 Поиск")],
                    [KeyboardButton("🔙 Назад в меню")]
                ], resize_keyboard=True)
            )
        else:
            await show_recipes_list(update, context, recipes, "all")
        return UserState.RECIPES_MENU
    
    elif text == "➕ Добавить рецепт":
        UserData.init_recipe(context)
        await update.message.reply_text(
            "🍳 ДОБАВЛЕНИЕ РЕЦЕПТА\n\n"
            "Шаг 1 из 7: Отправь название блюда:",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.ADD_RECIPE_NAME
    
    elif text == "🔍 Поиск":
        await update.message.reply_text(
            "🔍 Введи название блюда для поиска:",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.SEARCH_RECIPE
    
    elif text == "🔙 Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard()
        )
        return UserState.MAIN_MENU
    
    else:
        await update.message.reply_text(
            "Используй кнопки меню 👆",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("🥚 Быстрые (до 30 мин)")],
                [KeyboardButton("⏲️ Средние (30-60 мин)")],
                [KeyboardButton("🔥 Сложные (более 1 часа)")],
                [KeyboardButton("📚 Все рецепты")],
                [KeyboardButton("➕ Добавить рецепт")],
                [KeyboardButton("🔍 Поиск")],
                [KeyboardButton("🔙 Назад в меню")]
            ], resize_keyboard=True)
        )
        return UserState.RECIPES_MENU


async def handle_recipe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback кнопок рецептов"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data.startswith("price_"):
        parts = data.split('_')
        price_category = parts[1]
        time_category = parts[2]
        
        recipes = db.filter_recipes(user_id, time_category=time_category, price_category=price_category)
        
        if not recipes:
            await query.edit_message_text(
                f"❌ Рецепты не найдены в этой категории.\nПопробуй другие фильтры.",
                reply_markup=None
            )
        else:
            await show_recipes_list(query, context, recipes, f"{time_category}_{price_category}")
    
    elif data.startswith("recipe_"):
        recipe_id = int(data.split('_')[1])
        recipe = db.get_recipe(recipe_id)
        
        if recipe:
            await show_recipe_card(query, context, recipe)
    
    elif data.startswith("increase_portions_"):
        recipe_id = int(data.split('_')[2])
        current_portions = context.user_data.get('current_portions', 4)
        context.user_data['current_portions'] = current_portions + 1
        recipe = db.get_recipe(recipe_id)
        if recipe:
            await show_recipe_card(query, context, recipe, update=True)
    
    elif data.startswith("decrease_portions_"):
        recipe_id = int(data.split('_')[2])
        current_portions = context.user_data.get('current_portions', 4)
        if current_portions > 1:
            context.user_data['current_portions'] = current_portions - 1
            recipe = db.get_recipe(recipe_id)
            if recipe:
                await show_recipe_card(query, context, recipe, update=True)
    
    elif data.startswith("add_to_plan_"):
        recipe_id = int(data.split('_')[3])
        await query.edit_message_text(
            f"✅ Рецепт добавлен в план питания!",
            reply_markup=None
        )
    
    elif data.startswith("add_to_shopping_"):
        recipe_id = int(data.split('_')[3])
        await query.edit_message_text(
            f"✅ Ингредиенты добавлены в список покупок!",
            reply_markup=None
        )
    
    elif data.startswith("recipes_page_"):
        parts = data.split('_')
        page = int(parts[2])
        filter_key = context.user_data.get('current_filter', 'all')
        recipes = context.user_data.get('cached_recipes', [])
        await show_recipes_list(query, context, recipes, filter_key, page)
    
    elif data == "back_to_recipes_time":
        await query.edit_message_text(
            "🍳 МОИ РЕЦЕПТЫ\n\n"
            "Выбери категорию по времени приготовления:",
            reply_markup=None
        )
        await query.message.reply_text(
            "Выбери категорию:",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("🥚 Быстрые (до 30 мин)")],
                [KeyboardButton("⏲️ Средние (30-60 мин)")],
                [KeyboardButton("🔥 Сложные (более 1 часа)")],
                [KeyboardButton("📚 Все рецепты")],
                [KeyboardButton("➕ Добавить рецепт")],
                [KeyboardButton("🔍 Поиск")],
                [KeyboardButton("🔙 Назад в меню")]
            ], resize_keyboard=True)
        )
    
    elif data == "back_to_recipes_list":
        filter_key = context.user_data.get('current_filter', 'all')
        recipes = context.user_data.get('cached_recipes', [])
        await show_recipes_list(query, context, recipes, filter_key)


async def show_recipes_list(update, context, recipes, filter_key, page=0):
    """Показывает список рецептов"""
    items_per_page = 5
    start = page * items_per_page
    end = start + items_per_page
    current_recipes = recipes[start:end]
    total_pages = (len(recipes) + items_per_page - 1) // items_per_page
    
    context.user_data['cached_recipes'] = recipes
    context.user_data['current_filter'] = filter_key
    
    text = f"📚 Найдено рецептов: {len(recipes)}\n\n"
    for i, recipe in enumerate(current_recipes, start=start+1):
        time_emoji = "🥚" if recipe.get('time_category') == 'fast' else "⏲️" if recipe.get('time_category') == 'medium' else "🔥"
        price_emoji = "💚" if recipe.get('price_category') == 'budget' else "💛" if recipe.get('price_category') == 'medium' else "❤️"
        text += f"{i}. {time_emoji} {recipe['name']} {price_emoji}\n"
    
    keyboard = []
    for i, recipe in enumerate(current_recipes):
        keyboard.append([InlineKeyboardButton(
            f"{i+start+1}. {recipe['name']}", 
            callback_data=f"recipe_{recipe['id']}"
        )])
    
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("◀️", callback_data=f"recipes_page_{page-1}"))
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="no_action"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("▶️", callback_data=f"recipes_page_{page+1}"))
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_recipes")])
    
    if hasattr(update, 'edit_message_text'):
        await update.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def show_recipe_card(update, context, recipe, update_message=False):
    """Показывает карточку рецепта"""
    portions = context.user_data.get('current_portions', 4)
    original_portions = recipe.get('portions', 4)
    multiplier = portions / original_portions
    
    time_emoji = {
        'fast': '🥚',
        'medium': '⏲️',
        'hard': '🔥'
    }.get(recipe.get('time_category'), '⏱️')
    
    price_emoji = {
        'budget': '💚',
        'medium': '💛',
        'expensive': '❤️'
    }.get(recipe.get('price_category'), '💰')
    
    time_text = {
        'fast': 'Быстрое (до 30 мин)',
        'medium': 'Среднее (30-60 мин)',
        'hard': 'Сложное (более 1 часа)'
    }.get(recipe.get('time_category'), 'Не указано')
    
    price_text = {
        'budget': 'Бюджетный',
        'medium': 'Средний',
        'expensive': 'Дорогой'
    }.get(recipe.get('price_category'), 'Не указано')
    
    text = (
        f"*{recipe['name']}*\n"
        f"{time_emoji} Время: {time_text}\n"
        f"{price_emoji} Цена: {price_text}\n"
        f"🏷️ Теги: {', '.join(recipe.get('tags', ['нет']))}\n\n"
        f"*Ингредиенты (на {portions} порций):*\n"
    )
    
    for ingredient in recipe.get('ingredients', []):
        if isinstance(ingredient, dict):
            name = ingredient.get('ingredient', '')
            quantity = ingredient.get('quantity', 0) * multiplier
            unit = ingredient.get('unit', '')
            text += f"— {name} — {quantity:.1f} {unit}\n"
        else:
            text += f"— {ingredient}\n"
    
    text += f"\n*Приготовление:*\n{recipe.get('steps', 'Нет описания')}"
    
    if hasattr(update, 'edit_message_text') and update_message:
        await update.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=get_recipe_actions_inline(recipe['id'])
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=get_recipe_actions_inline(recipe['id'])
        )


async def add_recipe_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление названия рецепта"""
    if update.message.text == "🔙 Вернуться в меню":
        await update.message.reply_text("Главное меню:", reply_markup=get_main_menu_keyboard())
        return UserState.MAIN_MENU
    
    context.user_data['new_recipe']['name'] = update.message.text
    
    await update.message.reply_text(
        "Шаг 2 из 7: Сколько порций получается? (введи число)",
        reply_markup=get_back_to_menu_keyboard()
    )
    return UserState.ADD_RECIPE_PORTIONS


async def add_recipe_portions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление количества порций"""
    try:
        portions = int(update.message.text)
        if portions < 1 or portions > 50:
            raise ValueError
        
        context.user_data['new_recipe']['portions'] = portions
        
        keyboard = [
            [KeyboardButton("🥚 Быстрый (до 30 мин)")],
            [KeyboardButton("⏲️ Средний (30-60 мин)")],
            [KeyboardButton("🔥 Сложный (более 1 часа)")],
            [KeyboardButton("🔙 Вернуться в меню")]
        ]
        
        await update.message.reply_text(
            "Шаг 3 из 7: Выбери категорию по времени:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return UserState.ADD_RECIPE_TIME
    except:
        await update.message.reply_text(
            "❌ Введи корректное число порций (от 1 до 50):",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.ADD_RECIPE_PORTIONS


async def add_recipe_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление категории времени"""
    text = update.message.text
    
    time_map = {
        "🥚 Быстрый (до 30 мин)": "fast",
        "⏲️ Средний (30-60 мин)": "medium",
        "🔥 Сложный (более 1 часа)": "hard"
    }
    
    if text in time_map:
        context.user_data['new_recipe']['time_category'] = time_map[text]
        
        keyboard = [
            [KeyboardButton("💰 Бюджетный")],
            [KeyboardButton("💰💰 Средний")],
            [KeyboardButton("💰💰💰 Дорогой")],
            [KeyboardButton("🔙 Вернуться в меню")]
        ]
        
        await update.message.reply_text(
            "Шаг 4 из 7: Выбери ценовую категорию:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return UserState.ADD_RECIPE_PRICE
    else:
        await update.message.reply_text(
            "Пожалуйста, используй кнопки для выбора 👆"
        )
        return UserState.ADD_RECIPE_TIME


async def add_recipe_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление ценовой категории"""
    text = update.message.text
    
    price_map = {
        "💰 Бюджетный": "budget",
        "💰💰 Средний": "medium",
        "💰💰💰 Дорогой": "expensive"
    }
    
    if text in price_map:
        context.user_data['new_recipe']['price_category'] = price_map[text]
        
        await update.message.reply_text(
            "Шаг 5 из 7: Добавь теги через запятую\n"
            "(например: завтрак, диетическое, мясное)\n"
            "Или отправь '-' чтобы пропустить",
            reply_markup=get_back_to_menu_keyboard()
        )
        return UserState.ADD_RECIPE_TAGS
    else:
        await update.message.reply_text(
            "Пожалуйста, используй кнопки для выбора 👆"
        )
        return UserState.ADD_RECIPE_PRICE


async def add_recipe_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление тегов"""
    text = update.message.text
    
    if text == "-":
        context.user_data['new_recipe']['tags'] = []
    else:
        tags = [tag.strip() for tag in text.split(',')]
        context.user_data['new_recipe']['tags'] = tags
    
    await update.message.reply_text(
        "Шаг 6 из 7: Отправь список ингредиентов\n"
        "Каждый ингредиент с новой строки\n"
        "Например:\n"
        "Куриное филе — 500 г\n"
        "Яйца — 3 шт\n"
        "Соль — по вкусу",
        reply_markup=get_back_to_menu_keyboard()
    )
    return UserState.ADD_RECIPE_INGREDIENTS


async def add_recipe_ingredients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление ингредиентов"""
    ingredients = update.message.text.split('\n')
    parsed_ingredients = []
    
    for ingredient in ingredients:
        ingredient = ingredient.strip()
        if ingredient:
            if '—' in ingredient:
                parts = ingredient.split('—')
                name = parts[0].strip()
                rest = parts[1].strip()
                
                match = re.match(r'([\d.]+)\s*([а-яА-Яa-zA-Z]+)', rest)
                if match:
                    quantity = float(match.group(1))
                    unit = match.group(2)
                    parsed_ingredients.append({
                        'ingredient': name,
                        'quantity': quantity,
                        'unit': unit
                    })
                else:
                    parsed_ingredients.append(ingredient)
            else:
                parsed_ingredients.append(ingredient)
    
    context.user_data['new_recipe']['ingredients'] = parsed_ingredients
    
    await update.message.reply_text(
        "Шаг 7 из 7: Опиши шаги приготовления:",
        reply_markup=get_back_to_menu_keyboard()
    )
    return UserState.ADD_RECIPE_STEPS


async def add_recipe_steps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление шагов приготовления"""
    steps = update.message.text
    user_id = update.effective_user.id
    
    context.user_data['new_recipe']['steps'] = steps
    
    recipe_id = db.add_recipe(user_id, context.user_data['new_recipe'])
    
    await update.message.reply_text(
        f"✅ Рецепт успешно сохранен!\n\n"
        f"Ты можешь найти его в разделе 'Все мои рецепты'",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("🥚 Быстрые (до 30 мин)")],
            [KeyboardButton("⏲️ Средние (30-60 мин)")],
            [KeyboardButton("🔥 Сложные (более 1 часа)")],
            [KeyboardButton("📚 Все рецепты")],
            [KeyboardButton("➕ Добавить рецепт")],
            [KeyboardButton("🔍 Поиск")],
            [KeyboardButton("🔙 Назад в меню")]
        ], resize_keyboard=True)
    )
    
    return UserState.RECIPES_MENU


async def search_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск рецептов"""
    query = update.message.text
    user_id = update.effective_user.id
    
    if query == "🔙 Вернуться в меню":
        await update.message.reply_text("Главное меню:", reply_markup=get_main_menu_keyboard())
        return UserState.MAIN_MENU
    
    recipes = db.search_recipes(user_id, query)
    
    if not recipes:
        await update.message.reply_text(
            f"❌ Рецепты с названием '{query}' не найдены.\nПопробуй другой запрос.",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("🥚 Быстрые (до 30 мин)")],
                [KeyboardButton("⏲️ Средние (30-60 мин)")],
                [KeyboardButton("🔥 Сложные (более 1 часа)")],
                [KeyboardButton("📚 Все рецепты")],
                [KeyboardButton("➕ Добавить рецепт")],
                [KeyboardButton("🔍 Поиск")],
                [KeyboardButton("🔙 Назад в меню")]
            ], resize_keyboard=True)
        )
    else:
        await show_recipes_list(update, context, recipes, "search")
    
    return UserState.RECIPES_MENU
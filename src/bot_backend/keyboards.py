from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

MAIN_MENU_BUTTON = "Главное меню"
END_CHAT_BUTTON = "🤖 Закончить диалог"
CREATE_PLAN_BUTTON = "🥗 Создать меню"
SHOW_PLAN_BUTTON = "🍎 Моё питание"
BACK_BUTTON = "🔙 Назад"


# Главное меню
def get_main_menu_keyboard():
    """Постоянная клавиатура главного меню"""
    keyboard = [
        #[KeyboardButton("📅 План на неделю")],
        [KeyboardButton(SHOW_PLAN_BUTTON)],
        [KeyboardButton("📝 Мои рецепты"), KeyboardButton("📋 Список покупок")],
        [KeyboardButton("💧 Напоминалки"), KeyboardButton("📊 Профиль"), KeyboardButton("🤖 Спросить агента")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_quick_menu_keyboard():
    keyboard = [
        #[InlineKeyboardButton(CREATE_PLAN_BUTTON, callback_data="quick_create_plan")],
        [InlineKeyboardButton(SHOW_PLAN_BUTTON, callback_data="quick_show_plan")],
        [InlineKeyboardButton("⏰ Добавить напоминание", callback_data="quick_add_reminder")],
        [InlineKeyboardButton("💬 Чат с Ами", callback_data="quick_chat")],
    ]
    return InlineKeyboardMarkup(keyboard)

# Кнопки для выбора пола
def get_gender_keyboard():
    """Клавиатура для выбора пола"""
    keyboard = [
        [KeyboardButton("👨 М")],
        [KeyboardButton("👩 Ж")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# Кнопки для выбора цели
def get_goal_keyboard():
    """Клавиатура для выбора цели"""
    keyboard = [
        [KeyboardButton("⚖️ Похудеть")],
        [KeyboardButton("💪 Набрать мышечную массу")],
        [KeyboardButton("😊 Поддерживать вес")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# Инлайн кнопки для подтверждения
def get_confirmation_keyboard():
    """Инлайн клавиатура для подтверждения"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Нет", callback_data="confirm_no")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_activity_keyboard():
    """Клавиатура для выбора уровня активности"""
    keyboard = [
        [KeyboardButton("Сидячий и малоподвижный")],
        [KeyboardButton("Легкая активность (1-3 раза в неделю)")],
        [KeyboardButton("Средняя активность (3-5 раз в неделю)")],
        [KeyboardButton("Высокая активность (6-7 раз в неделю)")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Кнопки для плана питания
def get_plan_actions_keyboard():
    """Кнопки действий с планом"""
    keyboard = [
        [KeyboardButton(CREATE_PLAN_BUTTON)],
        [KeyboardButton(MAIN_MENU_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_days_keyboard():
    """Клавиатура для выбора количества дней"""
    keyboard = [
        [KeyboardButton("1"), KeyboardButton("2"), KeyboardButton("3")],
        [KeyboardButton("4"), KeyboardButton("5"), KeyboardButton("6")],
        [KeyboardButton("7")],
        [KeyboardButton(MAIN_MENU_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# Кнопка для бюджета
def get_budget_keyboard():
    """Клавиатура для ввода бюджета"""
    keyboard = [
        [KeyboardButton("⏭️ Пропустить")],
        [KeyboardButton(MAIN_MENU_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Кнопка возврата в меню
def get_back_to_menu_keyboard():
    """Клавиатура с кнопкой возврата"""
    keyboard = [
        [KeyboardButton(MAIN_MENU_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Клавиатура для редактирования профиля
def get_edit_profile_keyboard():
    """Клавиатура для выбора что редактировать"""
    keyboard = [
        [KeyboardButton("👤 Изменить имя")],
        [KeyboardButton("⚥ Изменить пол")],
        [KeyboardButton("📅 Изменить возраст")],
        [KeyboardButton("⚖️ Изменить вес")],
        [KeyboardButton("📏 Изменить рост")],
        [KeyboardButton("🎯 Изменить цель")],
        [KeyboardButton("🔙 Вернуться в профиль")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Клавиатура для действий с профилем
def get_profile_actions_keyboard():
    """Кнопки действий в профиле"""
    keyboard = [
        [KeyboardButton("✏️ Редактировать профиль")],
        [KeyboardButton("📊 Пересчитать ИМТ")],
        [KeyboardButton("⚖️ Настроить взвешивание")],
        [KeyboardButton(MAIN_MENU_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ======================== КЛАВИАТУРЫ ДЛЯ РЕЦЕПТОВ ========================

def get_recipes_main_keyboard():
    """Главное меню рецептов"""
    keyboard = [
        [KeyboardButton("🥪 Быстрые")],
        [KeyboardButton("🍛 Средние")],
        #[KeyboardButton("🔥 Сложные (более 1 часа)")],
        [KeyboardButton("📚 Все рецепты")],
        [KeyboardButton("➕ Добавить рецепт")],
        #[KeyboardButton("🔍 Поиск")],
        [KeyboardButton(MAIN_MENU_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_price_category_inline(time_category):
    """Инлайн кнопки для выбора ценовой категории после времени"""
    keyboard = [
        [
            InlineKeyboardButton("💚 Бюджетные", callback_data=f"price_budget_{time_category}"),
            InlineKeyboardButton("💛 Средние", callback_data=f"price_medium_{time_category}"),
            InlineKeyboardButton("❤️ Дорогие", callback_data=f"price_expensive_{time_category}")
        ],
        [InlineKeyboardButton("🎲 Все", callback_data=f"price_all_{time_category}")],
        [InlineKeyboardButton(BACK_BUTTON, callback_data="back_to_recipes")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_recipe_actions_inline(recipe_id):
    """Инлайн кнопки для действий с рецептом"""
    keyboard = [
            #[InlineKeyboardButton("➖", callback_data=f"decrease_portions_{recipe_id}"),
            #InlineKeyboardButton("4", callback_data="no_action"),
            #InlineKeyboardButton("➕", callback_data=f"increase_portions_{recipe_id}")],
        [
            InlineKeyboardButton("✅ В план", callback_data=f"add_to_plan_{recipe_id}"),
            InlineKeyboardButton("📋 В список", callback_data=f"add_to_shopping_{recipe_id}")
        ],
        [InlineKeyboardButton(BACK_BUTTON, callback_data="back_to_recipes_list")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_pagination_keyboard(page, total_pages, prefix):
    """Кнопки пагинации"""
    keyboard = []
    row = []
    
    if page > 0:
        row.append(InlineKeyboardButton("◀️", callback_data=f"{prefix}_page_{page-1}"))
    
    row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="no_action"))
    
    if page < total_pages - 1:
        row.append(InlineKeyboardButton("▶️", callback_data=f"{prefix}_page_{page+1}"))
    
    keyboard.append(row)
    keyboard.append([InlineKeyboardButton(BACK_BUTTON, callback_data="back_to_recipes")])
    
    return InlineKeyboardMarkup(keyboard)

# ======================== КЛАВИАТУРЫ ДЛЯ НАПОМИНАНИЙ ========================

def get_reminders_main_keyboard():
    """Главное меню напоминалок"""
    keyboard = [
        [KeyboardButton("💧 Пить воду")],
        #[KeyboardButton("🍎 Поесть")],
        [KeyboardButton("🏋️ Тренировка")],
        #[KeyboardButton("💊 Принять витамины")],
        #[KeyboardButton("🛏️ Проснуться")],
        [KeyboardButton("🌙 Лечь спать")],
        [KeyboardButton("➕ Создать своё")],
        [KeyboardButton("📋 Мои напоминания")],
        [KeyboardButton("❌ Отключить все")],
        [KeyboardButton(MAIN_MENU_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_reminder_periodicity_keyboard():
    """Клавиатура выбора периодичности"""
    keyboard = [
        [KeyboardButton("Каждый день")],
        [KeyboardButton("Раз в несколько часов")],
        [KeyboardButton("По дням недели")],
        [KeyboardButton("Один раз")],
        [KeyboardButton(BACK_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_weekdays_inline():
    """Инлайн кнопки для выбора дней недели"""
    keyboard = [
        [
            InlineKeyboardButton("ПН", callback_data="weekday_mon"),
            InlineKeyboardButton("ВТ", callback_data="weekday_tue"),
            InlineKeyboardButton("СР", callback_data="weekday_wed"),
            InlineKeyboardButton("ЧТ", callback_data="weekday_thu"),
            InlineKeyboardButton("ПТ", callback_data="weekday_fri")
        ],
        [
            InlineKeyboardButton("СБ", callback_data="weekday_sat"),
            InlineKeyboardButton("ВС", callback_data="weekday_sun"),
            InlineKeyboardButton("✅ Готово", callback_data="weekday_done")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_reminder_actions_inline(reminder_id):
    """Инлайн кнопки для управления напоминанием"""
    keyboard = [
        [
            InlineKeyboardButton("❌ Удалить", callback_data=f"reminder_delete_{reminder_id}"),
            InlineKeyboardButton("⏸️ Пауза", callback_data=f"reminder_pause_{reminder_id}")
        ],
        [
            InlineKeyboardButton("✏️ Изменить", callback_data=f"reminder_edit_{reminder_id}"),
            InlineKeyboardButton("🔕 Отключить", callback_data=f"reminder_disable_{reminder_id}")
        ],
        [InlineKeyboardButton(BACK_BUTTON, callback_data="back_to_reminders")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_pause_options_inline(reminder_id):
    """Кнопки для выбора периода паузы"""
    keyboard = [
        [
            InlineKeyboardButton("1 день", callback_data=f"pause_1d_{reminder_id}"),
            InlineKeyboardButton("3 дня", callback_data=f"pause_3d_{reminder_id}")
        ],
        [
            InlineKeyboardButton("1 неделя", callback_data=f"pause_1w_{reminder_id}"),
            InlineKeyboardButton("1 месяц", callback_data=f"pause_1m_{reminder_id}")
        ],
        [InlineKeyboardButton(BACK_BUTTON, callback_data=f"back_to_reminder_{reminder_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_food_time_keyboard():
    keyboard = [
        [KeyboardButton("08:00, 13:00, 19:00")],
        [KeyboardButton("09:00, 14:00, 20:00")],
        [KeyboardButton(BACK_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ======================== КЛАВИАТУРЫ ДЛЯ СПИСКА ПОКУПОК ========================

def get_confirm_generate_list_keyboard():
    keyboard = [
            [KeyboardButton("✅ Да, создать список")],
            [KeyboardButton(MAIN_MENU_BUTTON)]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_shopping_list_keyboard():
    """Клавиатура для списка покупок"""
    keyboard = [
        [KeyboardButton("📝 Собрать список на неделю")],
        [KeyboardButton("📋 Разделить по рецептам")],
        [KeyboardButton("🗑️ Очистить список")],
        [KeyboardButton(MAIN_MENU_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ======================== КЛАВИАТУРЫ ДЛЯ ВЗВЕШИВАНИЯ ========================

def get_weighing_days_keyboard():
    """Клавиатура для выбора дня взвешивания"""
    keyboard = [
        [KeyboardButton("ПН"), KeyboardButton("ВТ"), KeyboardButton("СР")],
        [KeyboardButton("ЧТ"), KeyboardButton("ПТ"), KeyboardButton("СБ")],
        [KeyboardButton("ВС")],
        [KeyboardButton("⏭️ Пропустить")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_weighing_actions_keyboard():
    """Кнопки для пропуска взвешивания"""
    keyboard = [
        [KeyboardButton("🔔 Напомнить позже")],
        [KeyboardButton("⏭️ Пропустить эту неделю")],
        [KeyboardButton(BACK_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_agent_chat_keyboard():
    """Клавиатура для режима общения с AI агентом"""
    from telegram import KeyboardButton, ReplyKeyboardMarkup
    keyboard = [
        [KeyboardButton(END_CHAT_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)



def get_nutrition_menu_keyboard():
    """Клавиатура меню питания"""
    keyboard = [
        [KeyboardButton("📅 План на неделю")],
        [KeyboardButton(CREATE_PLAN_BUTTON)],
        [KeyboardButton(MAIN_MENU_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_reminder_type_keyboard():
    """Клавиатура выбора типа напоминания"""
    keyboard = [
        [KeyboardButton("💧 Пить воду")],
        [KeyboardButton("🍽️ Приём пищи")],
        [KeyboardButton("💊 Витамины")],
        [KeyboardButton("🏃 Тренировка")],
        [KeyboardButton("✏️ Своё напоминание")],
        [KeyboardButton(BACK_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
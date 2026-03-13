from telegram.ext import ContextTypes

class UserState:
    """Класс для хранения состояний пользователя"""
    # Состояния регистрации
    REGISTRATION_START = 1
    REGISTRATION_NAME = 2
    REGISTRATION_GENDER = 3
    REGISTRATION_AGE = 4
    REGISTRATION_WEIGHT = 5
    REGISTRATION_HEIGHT = 6
    REGISTRATION_GOAL = 7
    REGISTRATION_CONFIRM = 8
    MAIN_MENU = 9
    
    # Состояния для плана питания
    AWAITING_BUDGET = 10
    AWAITING_PLAN_GOAL_CHANGE = 11
    
    # Состояния для рецептов
    RECIPES_MENU = 20
    ADD_RECIPE_NAME = 21
    ADD_RECIPE_PORTIONS = 22
    ADD_RECIPE_TIME = 23
    ADD_RECIPE_PRICE = 24
    ADD_RECIPE_TAGS = 25
    ADD_RECIPE_INGREDIENTS = 26
    ADD_RECIPE_STEPS = 27
    ADD_RECIPE_CONFIRM = 28
    SEARCH_RECIPE = 29
    
    # Состояния для напоминаний
    REMINDERS_MENU = 30
    ADD_REMINDER_NAME = 31
    ADD_REMINDER_PERIODICITY = 32
    ADD_REMINDER_TIME = 33
    ADD_REMINDER_INTERVAL = 34
    ADD_REMINDER_START_TIME = 35
    ADD_REMINDER_WEEKDAYS = 36
    ADD_REMINDER_DATETIME = 37
    REMINDER_ACTION = 38
    REMINDER_PAUSE = 39
    
    # Состояния для взвешивания
    WEIGHING_SETUP_DAY = 40
    WEIGHING_SETUP_TIME = 41
    WEIGHING_INPUT = 42
    
    # Состояния для редактирования профиля
    EDIT_PROFILE_MENU = 50
    EDIT_NAME = 51
    EDIT_GENDER = 52
    EDIT_AGE = 53
    EDIT_WEIGHT = 54
    EDIT_HEIGHT = 55
    EDIT_GOAL = 56
    
    # Состояние для списка покупок
    SHOPPING_LIST_MENU = 60

class UserData:
    """Вспомогательный класс для работы с данными пользователя в контексте"""
    
    @staticmethod
    def init_registration(context: ContextTypes.DEFAULT_TYPE):
        """Инициализация данных регистрации"""
        context.user_data['registration'] = {
            'name': None,
            'gender': None,
            'age': None,
            'weight': None,
            'height': None,
            'goal': None
        }
    
    @staticmethod
    def get_registration_data(context: ContextTypes.DEFAULT_TYPE):
        """Получить данные регистрации"""
        return context.user_data.get('registration', {})
    
    @staticmethod
    def set_registration_field(context: ContextTypes.DEFAULT_TYPE, field, value):
        """Установить поле в данных регистрации"""
        if 'registration' not in context.user_data:
            context.user_data['registration'] = {}
        context.user_data['registration'][field] = value
    
    @staticmethod
    def init_recipe(context: ContextTypes.DEFAULT_TYPE):
        """Инициализация данных нового рецепта"""
        context.user_data['new_recipe'] = {
            'name': None,
            'portions': None,
            'time_category': None,
            'price_category': None,
            'tags': [],
            'ingredients': [],
            'steps': []
        }
    
    @staticmethod
    def init_reminder(context: ContextTypes.DEFAULT_TYPE):
        """Инициализация данных нового напоминания"""
        context.user_data['new_reminder'] = {
            'name': None,
            'periodicity': None,
            'time': None,
            'interval': None,
            'weekdays': [],
            'datetime': None,
            'active': True
        }
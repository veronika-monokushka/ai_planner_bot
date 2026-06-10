"""Пакет обработчиков команд бота"""

from .registration import (
    handle_name, handle_gender, handle_age, handle_weight,
    handle_height, handle_goal, handle_confirmation, handle_activity
)

from .profile import (
    show_profile, edit_profile_menu, handle_edit_profile,
    edit_name, edit_gender, edit_age, edit_weight, edit_height,
    edit_goal
)

from .nutrition import (
    handle_plan_generation, handle_nutrition, handle_create_plan, handle_budget,
    handle_nutrition_callback, handle_plan_generation_callback, handle_days_count, handle_confirm_generation_plan,
    handle_confirm_meal_plan_changes, handle_modify_meal_plan_input
)

from .recipes import (
    handle_recipes_menu, handle_recipes_navigation, handle_recipe_callback,
    add_recipe_name, add_recipe_portions, add_recipe_time, add_recipe_price,
    add_recipe_tags, add_recipe_ingredients, add_recipe_steps, search_recipe
)

from .reminders import (
    handle_reminders_menu, handle_reminders_navigation, handle_reminder_callback,
    add_reminder_name, add_reminder_periodicity, add_reminder_time,
    add_reminder_interval, add_reminder_start_time, add_reminder_datetime,
    handle_weekday_callback, test_reminder_command, setup_reminder_jobs,
    handle_reminders_menu_callback, handle_motivation_reminder, handle_motivation_topic, admin_broadcast
)

from .weighing import (
    setup_weighing, handle_weighing_day, handle_weighing_time, handle_weighing_input
)

from .shopping import (
    handle_shopping_list_menu
)

from .common import (
    handle_main_menu, recalculate_profile, cancel, handle_unknown, start
)

__all__ = [
    'start', 'handle_name', 'handle_gender', 'handle_age', 'handle_weight',
    'handle_height', 'handle_goal', 'handle_confirmation',
    'show_profile', 'edit_profile_menu', 'handle_edit_profile',
    'edit_name', 'edit_gender', 'edit_age', 'edit_weight', 'edit_height',
    'edit_goal',
    'handle_plan_generation', 'handle_nutrition', 'handle_create_plan', 'handle_budget',
    'handle_nutrition_callback', 'handle_plan_generation_callback', 'handle_confirm_meal_plan_changes', 'handle_modify_meal_plan_input',
    'handle_recipes_menu', 'handle_recipes_navigation', 'handle_recipe_callback',
    'add_recipe_name', 'add_recipe_portions', 'add_recipe_time', 'add_recipe_price',
    'add_recipe_tags', 'add_recipe_ingredients', 'add_recipe_steps', 'search_recipe',
    'handle_reminders_menu', 'handle_reminders_navigation', 'handle_reminder_callback',
    'add_reminder_name', 'add_reminder_periodicity', 'add_reminder_time',
    'add_reminder_interval', 'add_reminder_start_time', 'add_reminder_datetime',
    'handle_weekday_callback', 'test_reminder_command', 'setup_reminder_jobs',
    'handle_reminders_menu_callback', 'handle_motivation_reminder', 'handle_motivation_topic',
    'setup_weighing', 'handle_weighing_day', 'handle_weighing_time', 'handle_weighing_input',
    'handle_shopping_list_menu', 'handle_confirm_generation_plan',
    'handle_main_menu', 'recalculate_profile', 'cancel', 'handle_unknown', 'handle_days_count', 'handle_activity', 'admin_broadcast'
]
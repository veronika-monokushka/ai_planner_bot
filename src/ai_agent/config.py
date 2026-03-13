import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота (обязательно смените на новый!)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8745953888:AAEDEbxuIsidFoyUADRB-PDnedg-Epn7mwY")

# Файл для хранения данных
USERS_DATA_FILE = "users_data.json"
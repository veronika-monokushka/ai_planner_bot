import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота 
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Файл для хранения данных
USERS_DATA_FILE = "users_data.json"
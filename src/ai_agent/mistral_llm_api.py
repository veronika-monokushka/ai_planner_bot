# mistral_llm_api.py

import os
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI


load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")
if not api_key:
    raise ValueError("MISTRAL_API_KEY не найден в .env")

mistral_llm_client = ChatMistralAI(
    api_key=api_key, 
    model="mistral-small-latest",
    temperature=0
)
import os
from dotenv import load_dotenv
from mistralai.client import Mistral

load_dotenv()  # Загружает переменные из .env

def test_mistral():
    """Тестирует подключение к Mistral API"""
    
    api_key = os.getenv("MISTRAL_API_KEY")
    model = "mistral-medium-latest"  # или "open-mixtral-8x7b", "codestral-latest"
    
    if not api_key:
        print("❌ Ошибка: MISTRAL_API_KEY не найден!")
        return
    
    client = Mistral(api_key=api_key)
    
    messages = [
        {
            "role": "user",
            "content": """Я подключилась к тебе по API. Моя подписка на mistral.ai - Current plan
            Experiment
            Access without paying. API requests may be used to train our models.
            Access frontier AI models
            Create and deploy agents
            Start experimenting quickly
            Ты знвешь какой у меня лимит запросов и токенов и на какое время?"""
        }
        #Привет! Ты - ИИ-помощник по планированию задач. Представься.
    ]
    
    try:
        response = client.chat.complete(
            model=model,
            messages=messages
        )
        
        # Печатаем ответ
        print("✅ Ответ от Mistral:")
        response_text = response.choices[0].message.content
        print(response_text)

        with open('ai_response.md', 'w', encoding='utf-8') as file:
            file.write(response_text)
            print("✅ Ответ сохранен в файл ai_response.md")

    except Exception as e:
        print(f"❌ Ошибка API: {e}")

if __name__ == "__main__":
    test_mistral()
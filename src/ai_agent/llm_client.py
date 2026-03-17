"""Минимальный клиент для работы с Mistral AI API"""
import os
from dotenv import load_dotenv
from mistralai.client import Mistral

load_dotenv()

class MistralAgent:
    """Агент Mistral с памятью диалога и подсчетом токенов"""
    
    def __init__(self, model: str = "mistral-medium-latest"):
        self.api_key = os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("❌ MISTRAL_API_KEY не найден в .env!")
        
        self.client = Mistral(api_key=self.api_key)
        self.model = model
        self.messages = []
        self.tokens_used = 0
        
        self.system_prompt = """Ты — умный ИИ-помощник по планированию задач и питания.
Помогаешь создавать задачи, меню, списки покупок.
Отвечай кратко, дружелюбно, на русском языке."""
    
    def ask(self, user_message: str, system_prompt: str = None) -> dict:
        """Запрос к агенту с сохранением контекста"""
        system_prompt = system_prompt or self.system_prompt
        
        if len(self.messages) == 0:
            self.messages.append({"role": "system", "content": system_prompt})
        
        self.messages.append({"role": "user", "content": user_message})
        
        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=self.messages,
                temperature=0.7,
                max_tokens=512,
                response_format={"type": "json_object"}  # Требует строгого JSON
            )
            
            ai_response = response.choices[0].message.content
            
            # Если это не JSON, очищаем ответ
            ai_response = self._clean_json_response(ai_response)
            
            self.messages.append({"role": "assistant", "content": ai_response})
            
            estimated_tokens = len(user_message + ai_response) // 4
            self.tokens_used += estimated_tokens
            
            return {
                "success": True,
                "response": ai_response,
                "tokens": estimated_tokens
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tokens": 0
            }
    
    def _clean_json_response(self, response: str) -> str:
        """Очищает ответ от markdown блоков и лишних символов"""
        # Убираем ```json ... ```
        response = response.strip()
        if response.startswith("```json"):
            response = response.replace("```json", "").strip()
        elif response.startswith("```"):
            response = response.replace("```", "").strip()
        
        # Находим первое и последнее "{" и "}"
        start = response.find("{")
        end = response.rfind("}")
        
        if start != -1 and end != -1 and end > start:
            response = response[start:end+1]
        
        return response
    
    def clear_history(self):
        """Очистить историю диалога"""
        self.messages = [m for m in self.messages if m["role"] == "system"]
    
    def get_usage_stats(self) -> dict:
        """Информация об использовании токенов"""
        return {
            "model": self.model,
            "tokens_used": self.tokens_used,
            "messages_count": len([m for m in self.messages if m["role"] != "system"]),
            "history_length": len(self.messages)
        }
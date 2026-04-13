from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from config_promts import SYSTEM_PROMPT

class AgentWithMemory:
    """Агент Mistral с памятью диалога и подсчетом токенов"""
    
    def __init__(self, llm_client, default_max_tokens: int = 300):
        self.client = llm_client
        self.model = llm_client.model
        self.messages = []  # Храним объекты BaseMessage
        self.tokens_used = 0
        self.default_max_tokens = default_max_tokens
        
        self.system_prompt = SYSTEM_PROMPT
    
    def ask(self, user_message: str, system_prompt: str = None, max_tokens: int = None) -> dict:
        """Запрос к агенту с сохранением контекста"""
        
        system_prompt = system_prompt or self.system_prompt
        tokens_limit = max_tokens if max_tokens is not None else self.default_max_tokens
        
        if len(self.messages) == 0:
            self.messages.append(SystemMessage(content=system_prompt))
        self.messages.append(HumanMessage(content=user_message))
        
        try:
            response = self.client.invoke(self.messages, max_tokens=tokens_limit)
            
            ai_response = response.content
            
            # Если требуется JSON, очищаем ответ
            ai_response = self._clean_json_response(ai_response)
            
            # Сохраняем ответ ассистента
            self.messages.append(AIMessage(content=ai_response))
            
            estimated_tokens = response.response_metadata["token_usage"]["total_tokens"]
            #example token_usage = {'prompt_tokens': 17, 'total_tokens': 30, 'completion_tokens': 13, 'prompt_tokens_details': {'cached_tokens': 0}}
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
    
    def ask_with_tools(
            self, 
            user_message: str, 
            tools: list, 
            system_prompt: str = None, max_tokens: int = None) -> dict:
        """Запрос с возможностью вызова инструментов (function calling)
    
        Args:
            user_message: Сообщение пользователя
            tools: Список инструментов
            system_prompt: Системный промпт (опционально)
            skip_llm_after_tools: Если True - после выполнения инструментов не вызывать LLM,
                                а сразу вернуть результат инструмента пользователю
        """
        
        system_prompt = system_prompt or self.system_prompt
        tokens_limit = max_tokens if max_tokens is not None else self.default_max_tokens
        
        if len(self.messages) == 0:
            self.messages.append(SystemMessage(content=system_prompt))
        
        self.messages.append(HumanMessage(content=user_message))
        
        # Привязываем инструменты
        llm_with_tools = self.client.bind_tools(tools)
        
        try:
            response = llm_with_tools.invoke(self.messages, max_tokens=tokens_limit)
            
            # Проверяем, есть ли вызов инструментов
            if hasattr(response, 'tool_calls') and response.tool_calls:
                return {
                    "success": True,
                    "tool_calls": response.tool_calls,
                    "content": response.content,
                    "tokens": 0
                }
            
            ai_response = response.content
            ai_response = self._clean_json_response(ai_response)
            self.messages.append(AIMessage(content=ai_response))
            
            estimated_tokens = response.response_metadata["token_usage"]["total_tokens"]
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
    
    def add_tool_result(self, tool_call_id: str, result: str):
        """Добавляет результат выполнения инструмента в историю"""
        self.messages.append(ToolMessage(content=result, tool_call_id=tool_call_id))

    def _clean_json_response(self, response: str) -> str:
        """Очищает ответ от markdown блоков и лишних символов"""
        response = response.strip()
        if response.startswith("```json"):
            response = response.replace("```json", "").strip()
        elif response.startswith("```"):
            response = response.replace("```", "").strip()
        
        start = response.find("{")
        end = response.rfind("}")
        
        if start != -1 and end != -1 and end > start:
            response = response[start:end+1]
        
        return response
    
    def clear_history(self):
        """Очистить историю диалога (сохраняет только system)"""
        system_messages = [m for m in self.messages if isinstance(m, SystemMessage)]
        self.messages = system_messages
    
    def get_usage_stats(self) -> dict:
        """Информация об использовании токенов"""
        return {
            "model": self.model,
            "tokens_used": self.tokens_used,
            "messages_count": len([m for m in self.messages if not isinstance(m, SystemMessage)]),
            "history_length": len(self.messages)
        }
    

import os
import json
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from .config_promts import SYSTEM_PROMPT
from typing import Optional, Dict, Callable, Any



class AgentWithMemory:
    """Агент Mistral с памятью диалога и подсчетом токенов"""
    
    def __init__(self, llm_client, default_max_tokens: int = 500):
        self.client = llm_client
        self.model = llm_client.model
        self.messages = []  # Храним объекты BaseMessage
        self.tokens_used = 0
        self.default_max_tokens = default_max_tokens
        
        self.system_prompt = SYSTEM_PROMPT
    
    def ask(self, user_message: str, system_prompt: str = None, max_tokens: int = None) -> dict:
        """Запрос к агенту с сохранением контекста"""
        
        system_prompt = system_prompt or self.system_prompt
        token_limit = max_tokens if max_tokens is not None else self.default_max_tokens
        
        if len(self.messages) == 0:
            self.messages.append(SystemMessage(content=system_prompt))
        self.messages.append(HumanMessage(content=user_message))
        
        try:
            response = self.client.invoke(self.messages, max_tokens=token_limit)
            
            ai_response = response.content
            
            # Если требуется JSON, очищаем ответ
            ai_response = self._clean_json_response(ai_response)
            
            # Сохраняем ответ ассистента
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
    
    def ask_with_tools(
        self, 
        user_message: str, 
        tools: list, 
        system_prompt: str = None,
        max_tokens: int = None,
        tool_executors: Optional[Dict[str, Callable]] = None
    ) -> dict:
        
        system_prompt = system_prompt or self.system_prompt
        token_limit = max_tokens if max_tokens is not None else self.default_max_tokens
        
        if len(self.messages) == 0:
            self.messages.append(SystemMessage(content=system_prompt))
            self._save_history_to_file()
        
        self.messages.append(HumanMessage(content=user_message))
        self._save_history_to_file()
        
        llm_with_tools = self.client.bind_tools(tools)
        
        try:
            response = llm_with_tools.invoke(self.messages, max_tokens=token_limit)
            
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # ✅ Сохраняем AIMessage с tool_calls
                ai_message_with_tools = AIMessage(content=response.content, tool_calls=response.tool_calls)
                self.messages.append(ai_message_with_tools)
                self._save_history_to_file()
                
                if tool_executors:
                    final_result = None
                    should_continue_to_llm = False
                    
                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        
                        if tool_name in tool_executors:
                            executor = tool_executors[tool_name]
                            result_message, continue_to_llm = executor(tool_call)
                            
                            self.add_tool_result(tool_call["id"], result_message)
                            self._save_history_to_file()
                            
                            if continue_to_llm:
                                should_continue_to_llm = True
                            else:
                                final_result = result_message
                        else:
                            self.add_tool_result(tool_call["id"], f"Выполнен инструмент {tool_name}")
                            self._save_history_to_file()
                            should_continue_to_llm = True
                    
                    if should_continue_to_llm:
                        second_response = self.client.invoke(self.messages, max_tokens=token_limit)
                        ai_response = second_response.content
                        self.messages.append(AIMessage(content=ai_response))
                        self._save_history_to_file()
                        
                        estimated_tokens = second_response.response_metadata["token_usage"]["total_tokens"]
                        self.tokens_used += estimated_tokens
                        
                        return {
                            "success": True,
                            "response": ai_response,
                            "tokens": estimated_tokens,
                            "tool_calls_processed": True
                        }
                    else:
                        # ✅ Добавляем финальный AIMessage от имени LLM
                        final_ai_message = AIMessage(content=final_result)
                        self.messages.append(final_ai_message)
                        self._save_history_to_file()
                        
                        return {
                            "success": True,
                            "response": final_result,
                            "tokens": 0,
                            "tool_calls_processed": True,
                            "direct_response": True
                        }
                
                return {
                    "success": True,
                    "tool_calls": response.tool_calls,
                    "content": response.content,
                    "tokens": 0
                }
            
            # Нет вызовов инструментов
            ai_response = response.content
            ai_response = self._clean_json_response(ai_response)
            self.messages.append(AIMessage(content=ai_response))
            self._save_history_to_file()
            
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

    def _save_history_to_file(self, filename: str = "agent_history.json"):
        """
        Сохраняет историю сообщений в файл.
        
        Args:
            filename: Имя файла для сохранения (по умолчанию agent_history.json)
        """
        
        
        # Создаем директорию logs, если её нет
        os.makedirs("logs", exist_ok=True)
        
        filepath = os.path.join("logs", filename)
        
        # Преобразуем сообщения в сериализуемый формат
        history_data = []
        for msg in self.messages:
            msg_data = {
                "type": type(msg).__name__,
                "content": msg.content,
                "timestamp": datetime.now().isoformat()
            }
            
            # Добавляем tool_call_id если есть
            if hasattr(msg, 'tool_call_id') and msg.tool_call_id:
                msg_data["tool_call_id"] = msg.tool_call_id
            
            # Добавляем tool_calls если есть
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                msg_data["tool_calls"] = msg.tool_calls
            
            history_data.append(msg_data)
        
        # Сохраняем в файл
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения истории: {e}")

    
    def ask_with_tools_simple(
        self, 
        user_message: str, 
        tools: list, 
        system_prompt: str = None,
        max_tokens: int = None
    ) -> dict:
        """
        Упрощенная версия ask_with_tools без автоматического выполнения.
        Только возвращает tool_calls, которые нужно обработать вручную.
        """
        return self.ask_with_tools(
            user_message=user_message,
            tools=tools,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            tool_executors=None  # Явно отключаем автоматическое выполнение
        )
    
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
    
    def clear_history(self, save_before_clear: bool = True):
        """
        Очистить историю диалога (сохраняет только system)
        
        Args:
            save_before_clear: Сохранить историю в файл перед очисткой
        """
        if save_before_clear and len(self.messages) > 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._save_history_to_file(f"agent_history_{timestamp}.json")
        
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
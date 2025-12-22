from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from exodus.logs import logger

@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime

    ### Tool calling
    tool_calls: Optional[Any] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    #### Metadata
    session_id: Optional[str] = None
    agent_name: Optional[str] = None

    def to_openai_format(self) -> Dict[str, Any]:
        payload = {
            "role": self.role,
            "content": self.content
        }

        if self.tool_calls is not None:
            payload["tool_calls"] = self.tool_calls

        if self.role == "tool":
            if self.tool_call_id is not None:
                payload["tool_call_id"] = self.tool_call_id
            if self.name is not None:
                payload["name"] = self.name

        return payload

    def to_dict(self) -> Dict[str, Any]:
        result =  {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }

        if self.agent_name is not None:
            result["agent_name"] = self.agent_name

        if self.tool_calls is not None:
            try:
                tool_calls_list = []
                for tc in self.tool_calls:
                    if hasattr(tc, 'model_dump'):
                        tool_calls_list.append(tc.model_dump(mode='json'))
                    elif hasattr(tc, 'dict'):
                        tool_calls_list.append(tc.dict())
                    else:
                        tool_calls_list.append({
                            'id': getattr(tc, 'id', None),
                            'type': getattr(tc, 'type', 'function'),
                            'function': {
                                'name': getattr(tc.function, 'name', None) if hasattr(tc, 'function') else None,
                                'arguments': getattr(tc.function, 'arguments', None) if hasattr(tc, 'function') else None
                            }
                        })
                result["tool_calls"] = tool_calls_list
            except Exception as e:
                result["tool_calls"] = []
                logger.error(f"Failed to convert tool calls to dictionary: {e}")

        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            result["name"] = self.name

        return result

class MemoryManager(ABC):
    def __init__(self):
        self._short_term_memory: List[Message] = []

    @abstractmethod
    def add_memory(self, message: Message) -> None:
        pass

    @abstractmethod
    def get_memory(self) -> List[Message]:
        pass

    @abstractmethod
    def clear_memory(self) -> None:
        pass

    @abstractmethod
    def load_memory(self, *args: Any, **kwargs: Any) -> None:
        pass

    def compact_memory(self) -> None:
        self._short_term_memory = self._short_term_memory[-10:]

    def get_llm_context(self) -> List[Dict[str, Any]]:
        return [message.to_openai_format() for message in self._short_term_memory]
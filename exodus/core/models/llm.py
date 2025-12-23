from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, TypeVar, Generic, List, AsyncIterator, Any, Dict

@dataclass
class LLMConfig:
    api_key: str
    model: str
    provider: str = "litellm"
    max_tokens: Optional[int] = 100000
    temperature: float = 0.7
    custom_api_base: Optional[str] = None

T = TypeVar('T')

class LLMProviderResponse(ABC, Generic[T]):
    def __init__(self, response: T):
        self.response = response
    
    @abstractmethod
    def get_content(self) -> str:
        pass

    @abstractmethod
    def is_tool_call(self) -> bool:
        pass

    @abstractmethod
    def get_tool_calls(self) -> Dict[str, Any]:
        pass

class LLMProvider(ABC, Generic[T]):
    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def generate(self, messages: List[Any], tools_schema: Optional[List[Dict[str, Any]]] = [], **kwargs) -> LLMProviderResponse[T]:
        """
        Generates a complete response asynchronously.
        Accepts extra kwargs for provider-specific options.
        """
        pass

    @abstractmethod
    async def generate_stream(self, messages: List[Any], tools_schema: Optional[List[Dict[str, Any]]] = [], **kwargs) -> AsyncIterator[Any]:
        """
        Generates a streaming response asynchronously.
        """
        pass

    @abstractmethod
    def rebuild_response(self, chunks: List[Any]) -> LLMProviderResponse[T]:
        """Rebuilds a complete response from a list of stream chunks."""
        pass
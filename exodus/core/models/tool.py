from abc import ABC, abstractmethod
from typing import Any, Callable


class ToolExecutionDriver(ABC):
    @abstractmethod
    async def execute(self, tool_type: str, tool_function: Callable, **tool_args) -> Any:
        pass

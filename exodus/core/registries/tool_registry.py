from typing import Dict, Callable
from exodus.logs import logger

class ToolPluginRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
    
    def register_tool(self, tool_name: str, func: Callable):
        self._tools[tool_name] = func

    def load_from_plugins(self):
        import importlib.metadata
        for entry_point in importlib.metadata.entry_points(group='exodus.plugins.tools'):
            logger.debug(f"Loading tool plugin {entry_point.name}")
            try:
                plugin = entry_point.load()
                for tool_name, tool_func in plugin.get_tools().items():
                    logger.debug(f"Registering tool {tool_name} from plugin {entry_point.name}")
                    self.register_tool(tool_name, tool_func)
            except Exception as e:
                logger.error(f"Failed to load tool plugin {entry_point.name}: {e}")

    def get_tool(self, tool_name: str) -> Callable:
        if not tool_name in self._tools:
            raise ValueError(f"Tool {tool_name} not found")
        return self._tools[tool_name]
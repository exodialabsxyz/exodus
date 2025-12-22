from .tool_registry import ToolPluginRegistry
from .agent_registry import AgentRegistry

# Global singleton instances
tool_registry = ToolPluginRegistry()
agent_registry = AgentRegistry()

# Export both classes and singletons
__all__ = [
    "ToolPluginRegistry",
    "AgentRegistry",
    "tool_registry",
    "agent_registry"
]

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class StreamEvent:
    """Base class for streaming events"""
    pass


@dataclass
class TextChunk(StreamEvent):
    """Text content from the agent"""
    text: str


@dataclass
class ToolCallEvent(StreamEvent):
    """Indicates tools are about to be called"""
    tool_calls: list


@dataclass
class ToolResultEvent(StreamEvent):
    """Tool execution results"""
    tool_name: str
    tool_args: Dict[str, Any]
    result: str


@dataclass
class AgentChange(StreamEvent):
    """Agent handoff occurred"""
    new_agent_name: str
    reason: str


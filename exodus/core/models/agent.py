import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from exodus.core.models.llm import LLMConfig
from exodus.settings import settings


@dataclass
class HandoffRequest:
    """Represents a request to handoff control to another agent"""

    target_agent_name: str
    reason: str
    preserve_memory: bool = True


@dataclass
class AgentDefinition:
    name: str
    description: str
    system_prompt: str
    tools: List[str]
    config: Dict[str, Any]
    llm_config: Optional[LLMConfig] = None
    handoffs: List[str] = field(
        default_factory=list
    )  ### List of agent names this agent can transfer to

    @classmethod
    def from_toml(cls, file: Path) -> "AgentDefinition":
        """Load an agent definition from a TOML file."""
        if isinstance(file, str):
            file = Path(file)

        with open(file, "rb") as f:
            data = tomllib.load(f)

        agent_data = data.get("agent", {})

        name = agent_data.get("name", "unnamed_agent")
        description = agent_data.get("description", "")
        system_prompt = agent_data.get("system_prompt", "")
        tools = agent_data.get("tools", [])
        handoffs = agent_data.get("handoffs", [])

        llm_data = agent_data.get("llm", {})

        llm_config = LLMConfig(
            api_key=llm_data.get("api_key") or settings.get("llm.default_provider_config.api_key"),
            model=llm_data.get("model") or settings.get("llm.default_model"),
            provider=llm_data.get("provider") or settings.get("llm.default_provider", "litellm"),
            temperature=llm_data.get("temperature", settings.get("llm.default_temperature", 0.7)),
            max_tokens=llm_data.get("max_tokens", settings.get("llm.default_max_tokens", 100000)),
            custom_api_base=llm_data.get(
                "custom_api_base", settings.get("llm.custom_api_base", None)
            ),
        )

        known_keys = {"name", "description", "system_prompt", "tools", "llm", "handoffs"}

        config = {
            "max_iterations": settings.get("agent.max_iterations", 10),
            "execution_mode": settings.get("agent.execution_mode", "local"),
        }

        config.update({k: v for k, v in agent_data.items() if k not in known_keys})

        return cls(
            name=name,
            description=description,
            system_prompt=system_prompt,
            tools=tools,
            config=config,
            llm_config=llm_config,
            handoffs=handoffs,
        )


@dataclass
class SwarmDefinition:
    name: str
    description: str
    agents: List[AgentDefinition]

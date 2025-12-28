import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from exodus.core.models.llm import LLMConfig
from exodus.logs import logger
from exodus.settings import settings


@dataclass
class HandoffRequest:
    """Represents a request to handoff control to another agent"""

    target_agent_name: str
    reason: str
    preserve_memory: bool = True


@dataclass
class AgentDefinition:
    """Class responsible for loading the agents available in the TOML files to create agent definitions with prompts,
    tools, and so on, which will then be used at runtime.

    .. note::

    - Prompts could be added in other parts of the system, even via URL.
    If it is not one of the default ones, it is looked for in the project's prompts folder. (TODO)

    - Some type of cache could be implemented with a “prompts” dictionary in the class. This avoids repeated disk reads for common prompts.
    For example, “common.md” would be read by each agent.
    With this strategy, it would already be in memory directly, and if not, it would be searched for on disk. (TODO)
    """

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
    def _get_prompt_from_paths(cls, config_file_path: Optional[Path], paths: List[str]) -> str:
        PROMPTS_BASE_PATH = config_file_path.parent.parent / "prompts"
        final_system_prompt = ""
        for path in paths:
            prompt_path = PROMPTS_BASE_PATH / path
            if prompt_path.exists():
                logger.debug(f"Loading prompt from: {prompt_path}")
                try:
                    with open(prompt_path, "r", encoding="utf-8") as file:
                        content = file.read().strip()
                        if content:
                            if final_system_prompt:
                                final_system_prompt += "\n\n"
                            final_system_prompt += content
                except Exception as read_error:
                    logger.error(
                        f"There was an error reading the prompt on {prompt_path}: {read_error}"
                    )
            else:
                logger.warning(f"The prompt {prompt_path} does not exists. Please check it")

        ### Fallback with minimal default system prompt
        if not final_system_prompt:
            logger.warning("No valid prompt loaded for agent; using default prompt.")
            final_system_prompt = (
                "You are an agent part of EXODUS a Swarm Intelligence Cybersecurity framework"
            )

        return final_system_prompt

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
        tools = agent_data.get("tools", [])
        handoffs = agent_data.get("handoffs", [])

        system_prompt_from_config = agent_data.get("system_prompt", [])
        system_prompt = (
            system_prompt_from_config
            if isinstance(system_prompt_from_config, str)
            else cls._get_prompt_from_paths(config_file_path=file, paths=system_prompt_from_config)
        )

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

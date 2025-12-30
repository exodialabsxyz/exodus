from pathlib import Path
from typing import Dict, Optional, Union

from exodus.core.models.agent import AgentDefinition
from exodus.logs import logger
from exodus.settings import BASE_DIR


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, AgentDefinition] = {}

    def register_agent(self, agent_definition: AgentDefinition):
        self._agents[agent_definition.name] = agent_definition

    def load_from_path(self, path: Optional[Union[str, Path]] = None):
        if path is None:
            logger.debug(f"Loading agents from {BASE_DIR / 'exodus' / 'agents' / 'single'}")
            path = BASE_DIR / "exodus" / "agents" / "single"
        else:
            path = Path(path) if isinstance(path, str) else path

        for file in path.glob("*.toml"):
            agent_definition = AgentDefinition.from_toml(file)
            self.register_agent(agent_definition)

    def get_agent(self, agent_name: str) -> AgentDefinition:
        if agent_name not in self._agents:
            raise ValueError(f"Agent {agent_name} not found")
        return self._agents[agent_name]

from typing import Dict, Optional, Union
from pathlib import Path
from exodus.core.models.agent import AgentDefinition

class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, AgentDefinition] = {}

    def register_agent(self, agent_definition: AgentDefinition):
        self._agents[agent_definition.name] = agent_definition

    def load_from_path(self, path: Optional[Union[str, Path]] = None):
        if path is None:
            current_file = Path(__file__).resolve()
            parent_dir = current_file.parent
            path = parent_dir / "agents" / "single"
        else:
            path = Path(path) if isinstance(path, str) else path
        
        for file in path.glob("*.toml"):
            agent_definition = AgentDefinition.from_toml(file)
            self.register_agent(agent_definition)

    def get_agent(self, agent_name: str) -> AgentDefinition:
        if not agent_name in self._agents:
            raise ValueError(f"Agent {agent_name} not found")
        return self._agents[agent_name]

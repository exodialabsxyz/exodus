import pytest
import tempfile
from pathlib import Path
from exodus.core.registries import agent_registry, AgentRegistry
from exodus.core.models.agent import AgentDefinition


class TestAgentRegistry:
    """Test AgentRegistry functionality"""

    @pytest.fixture
    def clean_registry(self):
        """Fixture to provide a clean registry for each test"""
        registry = AgentRegistry()
        yield registry
        # Cleanup
        registry._agents.clear()

    @pytest.fixture
    def temp_agents_dir(self):
        """Create a temporary directory with sample agent TOML files"""
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        
        # Create first agent
        agent1_toml = """
[agent]
name = "agent_alpha"
description = "First test agent"
system_prompt = "You are Alpha"
tools = ["tool1", "tool2"]

[agent.llm]
temperature = 0.7
"""
        (temp_path / "agent_alpha.toml").write_text(agent1_toml)
        
        # Create second agent
        agent2_toml = """
[agent]
name = "agent_beta"
description = "Second test agent"
system_prompt = "You are Beta"
tools = ["tool3"]
max_iterations = 15

[agent.llm]
temperature = 0.9
model = "gpt-4"
"""
        (temp_path / "agent_beta.toml").write_text(agent2_toml)
        
        # Create third agent
        agent3_toml = """
[agent]
name = "agent_gamma"
description = "Third test agent"
system_prompt = "You are Gamma"
tools = []
verbose = true
custom_param = "test_value"
"""
        (temp_path / "agent_gamma.toml").write_text(agent3_toml)
        
        yield temp_path
        
        # Cleanup
        for file in temp_path.glob("*.toml"):
            file.unlink()
        temp_path.rmdir()

    def test_register_and_get_agent(self, clean_registry):
        """Test manually registering an agent and retrieving it"""
        agent_def = AgentDefinition(
            name="manual_agent",
            description="Manually created agent",
            system_prompt="Test prompt",
            tools=["tool1"],
            config={"max_iterations": 10}
        )
        
        # Register the agent
        clean_registry.register_agent(agent_def)
        
        # Retrieve and verify
        retrieved = clean_registry.get_agent("manual_agent")
        assert retrieved.name == "manual_agent"
        assert retrieved.description == "Manually created agent"
        assert retrieved.system_prompt == "Test prompt"
        assert retrieved.tools == ["tool1"]

    def test_get_nonexistent_agent_raises_error(self, clean_registry):
        """Test that getting a non-existent agent raises ValueError"""
        with pytest.raises(ValueError) as excinfo:
            clean_registry.get_agent("nonexistent_agent")
        
        assert "not found" in str(excinfo.value)

    def test_load_from_path_loads_all_agents(self, clean_registry, temp_agents_dir):
        """Test loading all agents from a directory"""
        # Load agents from temp directory
        clean_registry.load_from_path(temp_agents_dir)
        
        # Verify all three agents were loaded
        assert len(clean_registry._agents) == 3
        
        # Verify we can retrieve each agent
        alpha = clean_registry.get_agent("agent_alpha")
        beta = clean_registry.get_agent("agent_beta")
        gamma = clean_registry.get_agent("agent_gamma")
        
        assert alpha.name == "agent_alpha"
        assert beta.name == "agent_beta"
        assert gamma.name == "agent_gamma"

    def test_loaded_agents_have_correct_properties(self, clean_registry, temp_agents_dir):
        """Test that loaded agents have all their properties correctly set"""
        clean_registry.load_from_path(temp_agents_dir)
        
        # Test agent_alpha
        alpha = clean_registry.get_agent("agent_alpha")
        assert alpha.description == "First test agent"
        assert alpha.system_prompt == "You are Alpha"
        assert alpha.tools == ["tool1", "tool2"]
        assert alpha.llm_config.temperature == 0.7
        
        # Test agent_beta with custom config
        beta = clean_registry.get_agent("agent_beta")
        assert beta.description == "Second test agent"
        assert beta.tools == ["tool3"]
        assert beta.config["max_iterations"] == 15
        assert beta.llm_config.temperature == 0.9
        assert beta.llm_config.model == "gpt-4"
        
        # Test agent_gamma with extra fields
        gamma = clean_registry.get_agent("agent_gamma")
        assert gamma.system_prompt == "You are Gamma"
        assert gamma.tools == []
        assert gamma.config.get("verbose") is True
        assert gamma.config.get("custom_param") == "test_value"

    def test_load_from_path_with_string(self, clean_registry, temp_agents_dir):
        """Test loading agents using string path instead of Path object"""
        # Convert Path to string
        path_str = str(temp_agents_dir)
        
        clean_registry.load_from_path(path_str)
        
        # Verify agents were loaded
        assert len(clean_registry._agents) == 3
        assert "agent_alpha" in clean_registry._agents
        assert "agent_beta" in clean_registry._agents
        assert "agent_gamma" in clean_registry._agents

    def test_load_from_empty_directory(self, clean_registry):
        """Test loading from an empty directory doesn't fail"""
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        
        try:
            clean_registry.load_from_path(temp_path)
            
            # Should have no agents loaded
            assert len(clean_registry._agents) == 0
        finally:
            temp_path.rmdir()

    def test_multiple_registrations_override(self, clean_registry):
        """Test that registering an agent with the same name overrides the previous one"""
        agent_v1 = AgentDefinition(
            name="versioned_agent",
            description="Version 1",
            system_prompt="V1 prompt",
            tools=[],
            config={}
        )
        
        agent_v2 = AgentDefinition(
            name="versioned_agent",
            description="Version 2",
            system_prompt="V2 prompt",
            tools=["new_tool"],
            config={}
        )
        
        # Register first version
        clean_registry.register_agent(agent_v1)
        assert clean_registry.get_agent("versioned_agent").description == "Version 1"
        
        # Register second version (should override)
        clean_registry.register_agent(agent_v2)
        assert clean_registry.get_agent("versioned_agent").description == "Version 2"
        assert clean_registry.get_agent("versioned_agent").tools == ["new_tool"]
        
        # Should still only have one agent in registry
        assert len(clean_registry._agents) == 1

    def test_load_mixed_files_ignores_non_toml(self, clean_registry):
        """Test that loading a directory with mixed file types only loads .toml files"""
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        
        # Create a valid TOML agent
        agent_toml = """
[agent]
name = "valid_agent"
description = "Valid agent"
system_prompt = "Test"
tools = []
"""
        (temp_path / "valid_agent.toml").write_text(agent_toml)
        
        # Create non-TOML files that should be ignored
        (temp_path / "readme.txt").write_text("This is not an agent")
        (temp_path / "config.json").write_text('{"key": "value"}')
        (temp_path / "script.py").write_text("print('hello')")
        
        try:
            clean_registry.load_from_path(temp_path)
            
            # Should only load the TOML file
            assert len(clean_registry._agents) == 1
            assert "valid_agent" in clean_registry._agents
        finally:
            for file in temp_path.glob("*"):
                file.unlink()
            temp_path.rmdir()

    def test_registry_state_isolation(self):
        """Test that different registry instances maintain separate state"""
        registry1 = AgentRegistry()
        registry2 = AgentRegistry()
        
        agent = AgentDefinition(
            name="isolated_agent",
            description="Test isolation",
            system_prompt="Test",
            tools=[],
            config={}
        )
        
        # Register in first registry only
        registry1.register_agent(agent)
        
        # Verify it's in registry1
        assert "isolated_agent" in registry1._agents
        
        # Verify it's NOT in registry2
        assert "isolated_agent" not in registry2._agents
        
        # Attempting to get from registry2 should fail
        with pytest.raises(ValueError):
            registry2.get_agent("isolated_agent")

    def test_global_registry_singleton(self):
        """Test that the global agent_registry singleton works correctly"""
        # Clear the global registry first
        agent_registry._agents.clear()
        
        # Create a test agent
        agent = AgentDefinition(
            name="global_test_agent",
            description="Test global registry",
            system_prompt="Test",
            tools=[],
            config={}
        )
        
        # Register via global singleton
        agent_registry.register_agent(agent)
        
        # Verify we can retrieve it
        retrieved = agent_registry.get_agent("global_test_agent")
        assert retrieved.name == "global_test_agent"
        
        # Cleanup
        agent_registry._agents.clear()


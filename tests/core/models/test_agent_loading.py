import tempfile
from pathlib import Path

import pytest

from exodus.core.models.agent import AgentDefinition
from exodus.settings import settings


class TestAgentDefinitionLoading:
    """Test AgentDefinition loading from TOML files"""

    def test_load_basic_agent_from_toml(self):
        """Test loading an agent with basic fields only"""
        toml_content = """
[agent]
name = "test_agent"
description = "Test agent for unit testing"
system_prompt = "You are a test agent"
tools = ["tool1", "tool2"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            agent = AgentDefinition.from_toml(temp_path)

            # Verify basic fields
            assert agent.name == "test_agent"
            assert agent.description == "Test agent for unit testing"
            assert agent.system_prompt == "You are a test agent"
            assert agent.tools == ["tool1", "tool2"]

            # Verify config has defaults from settings
            assert "max_iterations" in agent.config
            assert "execution_mode" in agent.config

            # Verify LLM config has defaults from settings
            assert agent.llm_config is not None
            assert agent.llm_config.provider == settings.get("llm.default_provider", "litellm")

        finally:
            temp_path.unlink()

    def test_load_agent_with_custom_llm_config(self):
        """Test loading an agent with custom LLM configuration"""
        toml_content = """
[agent]
name = "custom_llm_agent"
description = "Agent with custom LLM settings"
system_prompt = "Custom prompt"
tools = []

[agent.llm]
model = "gpt-4"
temperature = 0.9
max_tokens = 2000
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            agent = AgentDefinition.from_toml(temp_path)

            # Verify LLM config overrides
            assert agent.llm_config is not None
            assert agent.llm_config.model == "gpt-4"
            assert agent.llm_config.temperature == 0.9
            assert agent.llm_config.max_tokens == 2000

            # Verify fallback for api_key (should come from settings)
            assert agent.llm_config.api_key == settings.get("llm.default_provider_config.api_key")

        finally:
            temp_path.unlink()

    def test_load_agent_with_extra_config(self):
        """Test loading an agent with additional configuration fields"""
        toml_content = """
[agent]
name = "config_agent"
description = "Agent with extra config"
system_prompt = "Test"
tools = ["core.echo"]
max_iterations = 25
verbose = true
custom_field = "custom_value"
retry_count = 3
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            agent = AgentDefinition.from_toml(temp_path)

            # Verify basic fields
            assert agent.name == "config_agent"

            # Verify extra config fields
            assert agent.config["max_iterations"] == 25  # Override default
            assert agent.config["verbose"] is True
            assert agent.config["custom_field"] == "custom_value"
            assert agent.config["retry_count"] == 3
            assert "execution_mode" in agent.config  # Default preserved

        finally:
            temp_path.unlink()

    def test_load_agent_minimal_with_defaults(self):
        """Test loading an agent with minimal config, relying on global defaults"""
        toml_content = """
[agent]
name = "minimal_agent"
description = "Minimal configuration"
system_prompt = "You are helpful"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            agent = AgentDefinition.from_toml(temp_path)

            # Verify basic fields
            assert agent.name == "minimal_agent"

            # Verify tools fallback to settings
            expected_tools = settings.get("cli.default_tools", [])
            assert agent.tools == expected_tools

            # Verify config has defaults
            assert agent.config["max_iterations"] == settings.get("agent.max_iterations", 10)
            assert agent.config["execution_mode"] == settings.get("agent.execution_mode", "local")

            # Verify LLM config uses global settings
            assert agent.llm_config is not None
            assert agent.llm_config.model == settings.get("llm.default_model")
            assert agent.llm_config.provider == settings.get("llm.default_provider", "litellm")

        finally:
            temp_path.unlink()

    def test_load_agent_from_string_path(self):
        """Test loading an agent using string path instead of Path object"""
        toml_content = """
[agent]
name = "string_path_agent"
description = "Test string path"
system_prompt = "Test"
tools = []
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path_str = f.name

        try:
            # Pass string instead of Path
            agent = AgentDefinition.from_toml(temp_path_str)
            assert agent.name == "string_path_agent"

        finally:
            Path(temp_path_str).unlink()

    def test_load_agent_with_partial_llm_config(self):
        """Test loading an agent with partial LLM config (some fields, fallback for others)"""
        toml_content = """
[agent]
name = "partial_llm_agent"
description = "Partial LLM config"
system_prompt = "Test"
tools = []

[agent.llm]
temperature = 0.5
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            agent = AgentDefinition.from_toml(temp_path)

            # Verify custom field
            assert agent.llm_config.temperature == 0.5

            # Verify fallbacks
            assert agent.llm_config.model == settings.get("llm.default_model")
            assert agent.llm_config.provider == settings.get("llm.default_provider", "litellm")
            assert agent.llm_config.api_key == settings.get("llm.default_provider_config.api_key")

        finally:
            temp_path.unlink()

    def test_agent_config_override_priority(self):
        """Test that agent-specific config overrides global settings"""
        toml_content = """
[agent]
name = "priority_agent"
description = "Test config priority"
system_prompt = "Test"
tools = ["custom_tool"]
max_iterations = 99
execution_mode = "remote"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            agent = AgentDefinition.from_toml(temp_path)

            # Verify overrides
            assert agent.config["max_iterations"] == 99  # Not the default
            assert agent.config["execution_mode"] == "remote"  # Not the default
            assert agent.tools == ["custom_tool"]  # Not the default

        finally:
            temp_path.unlink()

    def test_load_real_chat_agent(self):
        """Test loading the actual chat_agent.toml from the project"""
        agent_path = Path("exodus/agents/single/chat_agent.toml")

        if agent_path.exists():
            agent = AgentDefinition.from_toml(agent_path)

            # Verify it loaded successfully
            assert agent.name == "chat_agent"
            assert agent.description != ""
            assert agent.system_prompt != ""
            assert isinstance(agent.tools, list)
            assert agent.llm_config is not None

            # Verify config dict exists
            assert isinstance(agent.config, dict)
        else:
            pytest.skip("chat_agent.toml not found in expected location")

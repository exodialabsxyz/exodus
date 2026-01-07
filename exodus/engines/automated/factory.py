from exodus.core.memory.local_json_memory import LocalJsonMemoryManager
from exodus.core.models.llm import LLMConfig
from exodus.core.providers.litellm import LitellmProvider
from exodus.core.registries import agent_registry, tool_registry
from exodus.core.tools.tool_executor import ToolExecutor
from exodus.engines.automated.engine import AutomatedAgentEngine
from exodus.settings import settings


def create_automated_engine(
    agent_name: str = "triage_agent",
    session_id: str = "default",
    **kwargs,
) -> AutomatedAgentEngine:
    """
    Factory function to create an AutomatedAgentEngine with standard setup.

    Args:
        agent_name: Name of agent from registry
        session_id: Unique session identifier
        **kwargs: Additional arguments to pass to AutomatedAgentEngine

    Returns:
        Configured AutomatedAgentEngine instance

    Example:
        >>> engine = create_automated_engine("recon_agent", "scan_123")
        >>> async for event in engine.run_automated("Scan target"):
        ...     handle_event(event)
    """
    ### Load registries
    tool_registry.load_from_plugins()
    agent_registry.load_from_path()

    ### Get agent
    agent_def = agent_registry.get_agent(agent_name)

    ### Create components
    memory_manager = LocalJsonMemoryManager()

    llm_config = LLMConfig(
        api_key=settings.get("llm.default_provider_config.api_key"),
        model=settings.get("llm.default_model"),
        provider="litellm",
        temperature=0.3,  ### Lower for automation
        max_tokens=settings.get("llm.default_max_tokens"),
    )
    llm_provider = LitellmProvider(llm_config)

    tool_executor = ToolExecutor()

    ### Create engine
    engine = AutomatedAgentEngine(
        llm_provider=llm_provider,
        memory_manager=memory_manager,
        tool_executor=tool_executor,
        agent_definition=agent_def,
        **kwargs,
    )

    return engine

"""
Session management for the Exodus CLI.
Handles AgentEngine initialization and conversation state.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, AsyncIterator, Union

from exodus.agent_engine import AgentEngine
from exodus.core.models.agent import AgentDefinition, HandoffRequest
from exodus.core.models.llm import LLMConfig
from exodus.core.models.events import AgentChange, ToolCallEvent, ToolResultEvent
from exodus.core.registries import tool_registry, agent_registry
from exodus.core.providers.litellm import LitellmProvider
from exodus.core.memory.local_json_memory import LocalJsonMemoryManager
from exodus.core.tools.tool_executor import ToolExecutor
from exodus.settings import settings
from exodus.logs import logger


def _create_fallback_agent() -> AgentDefinition:
    """Create a fallback default chat agent when none is configured."""
    return AgentDefinition(
        name="DefaultChatAgent",
        description="General purpose conversational agent",
        system_prompt="""You are a helpful AI assistant with access to various tools.
When users ask you to perform tasks, use the available tools when appropriate.
Be concise, clear, and helpful in your responses.
Always explain what you're doing when using tools.""",
        tools=[],  # Will be populated from settings/CLI args
        config={
            "max_iterations": settings.get("agent.max_iterations", 10),
            "verbose": False
        }
    )


class ChatSession:
    """Manages a chat session with the agent."""
    
    def __init__(
        self,
        agent_name: Optional[str] = None,
        model: Optional[str] = None,
        tools: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize a chat session.
        
        Args:
            agent_name: Name of the agent to use (from registry or settings)
            model: LLM model name (overrides agent/settings config)
            tools: List of tool names to enable (overrides agent config)
            temperature: Model temperature (overrides agent config)
            max_tokens: Maximum tokens for response
            api_key: API key (overrides settings and env)
        """
        # Configuration priority: CLI args > agent config > settings.toml > env vars > defaults
        self.api_key = api_key or settings.get('llm.default_provider_config.api_key') or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("No API key provided. Set it via --api-key, settings.toml, or GEMINI_API_KEY environment variable")
        
        # Initialize tool registry
        tool_registry.load_from_plugins()
        
        # Load agents from registry
        try:
            agents_path = Path("exodus/agents/single")
            if agents_path.exists():
                agent_registry.load_from_path(agents_path)
                logger.info(f"Loaded {len(agent_registry._agents)} agents from registry")
        except Exception as e:
            logger.warning(f"Failed to load agents from registry: {e}")
        
        # Determine which agent to use
        if agent_name is None:
            # Try to get default agent from settings
            agent_name = settings.get("agent.default_agent")
        
        # Try to load agent from registry
        if agent_name:
            try:
                self.agent_definition = agent_registry.get_agent(agent_name)
                logger.info(f"Using agent from registry: {agent_name}")
            except ValueError:
                logger.warning(f"Agent '{agent_name}' not found in registry, using fallback")
                self.agent_definition = _create_fallback_agent()
        else:
            logger.info("No default agent specified, using fallback")
            self.agent_definition = _create_fallback_agent()
        
        # Override agent config with CLI arguments if provided
        if model:
            if self.agent_definition.llm_config:
                self.agent_definition.llm_config.model = model
            else:
                self.agent_definition.llm_config = LLMConfig(
                    api_key=self.api_key,
                    model=model,
                    provider=settings.get("llm.default_provider", "litellm"),
                    temperature=temperature,
                    max_tokens=max_tokens
                )
        
        # Set model, temperature, max_tokens from agent or defaults
        self.model = model or (self.agent_definition.llm_config.model if self.agent_definition.llm_config else settings.get('llm.default_model', 'gemini-2.5-flash'))
        self.temperature = temperature if model else (self.agent_definition.llm_config.temperature if self.agent_definition.llm_config else 0.7)
        self.max_tokens = max_tokens or (self.agent_definition.llm_config.max_tokens if self.agent_definition.llm_config else settings.get('llm.max_tokens', 4096))
        
        # Determine which tools to use
        if tools is not None:
            self.tools = tools
            self.agent_definition.tools = tools  # Override agent tools
        else:
            # Use agent tools if defined, otherwise from settings or all registered
            if self.agent_definition.tools:
                self.tools = self.agent_definition.tools
            else:
                cli_tools = settings.get('cli.default_tools')
                if cli_tools:
                    self.tools = cli_tools
                else:
                    # Get all registered tools
                    self.tools = list(tool_registry._tools.keys())
                self.agent_definition.tools = self.tools
        
        logger.info(f"Initializing session with agent: {self.agent_definition.name}")
        logger.info(f"Using model: {self.model}")
        logger.info(f"Available tools: {', '.join(self.tools) if self.tools else 'None'}")
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all core components."""
        # Memory manager
        self.memory_manager = LocalJsonMemoryManager()
        
        # LLM provider
        llm_config = LLMConfig(
            api_key=self.api_key,
            model=self.model,
            provider="litellm",
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            custom_api_base=settings.get("llm.custom_api_base", None)
        )
        self.llm_provider = LitellmProvider(llm_config)
        
        # Tool executor
        self.tool_executor = ToolExecutor()
        
        # Agent engine
        self.agent_engine = AgentEngine(
            llm_provider=self.llm_provider,
            memory_manager=self.memory_manager,
            tool_executor=self.tool_executor,
            agent_definition=self.agent_definition
        )
    
    async def send_message_stream(self, user_input: str):
        """
        Send a message to the agent and get a streaming response.
        Supports automatic handoffs between agents.
        
        Args:
            user_input: User's message
            
        Yields:
            Stream events (str, ToolCallEvent, ToolResultEvent, AgentChange)
        """
        current_input = user_input
        
        while True:
            ### Execute current agent and propagate all events
            agent_change = None
            
            async for event in self.agent_engine.run_loop(current_input):
                ### Propagate all events to CLI
                yield event
                
                ### Track if handoff happened
                if isinstance(event, AgentChange):
                    agent_change = event
                    break
            
            ### Handle agent handoff if it occurred
            if agent_change:
                current_agent_name = self.agent_definition.name
                logger.info(f"Handoff: {current_agent_name} -> {agent_change.new_agent_name}")
                logger.info(f"Reason: {agent_change.reason}")
                
                try:
                    ### Load the target agent
                    new_agent = agent_registry.get_agent(agent_change.new_agent_name)
                    
                    ### Add handoff context to memory
                    from exodus.core.models.memory import Message
                    self.memory_manager.add_memory(Message(
                        role="tool",
                        content=f"[Handoff from {current_agent_name} to {agent_change.new_agent_name}: {agent_change.reason}]",
                        timestamp=datetime.now()
                    ))
                    
                    ### Update agent definition
                    self.agent_definition = new_agent
                    
                    ### Update LLM config if agent has custom config
                    if new_agent.llm_config:
                        self.llm_provider.config = new_agent.llm_config
                    
                    ### Preserve loop count across handoffs
                    current_loop_count = self.agent_engine.loop_count
                    
                    ### Recreate agent engine with new agent, preserving loop count
                    self.agent_engine = AgentEngine(
                        llm_provider=self.llm_provider,
                        memory_manager=self.memory_manager,
                        tool_executor=self.tool_executor,
                        agent_definition=self.agent_definition,
                        initial_loop_count=current_loop_count
                    )
                    
                    ### Continue with continuation prompt
                    current_input = "You have been reassigned by the previous agent. Continue with the conversation"
                    
                except ValueError as e:
                    logger.error(f"Handoff failed: Agent '{agent_change.new_agent_name}' not found: {e}")
                    from exodus.core.models.memory import Message
                    self.memory_manager.add_memory(Message(
                        role="tool",
                        content=f"[Error] Cannot transfer to '{agent_change.new_agent_name}': Agent not found.",
                        timestamp=datetime.now()
                    ))
                    break
            else:
                ### Normal completion, no handoff
                break
    
    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.memory_manager.clear_memory()
        
        # Re-add system prompt
        if self.agent_definition.system_prompt:
            from exodus.core.models.memory import Message
            self.memory_manager.add_memory(Message(
                role="system",
                content=self.agent_definition.system_prompt,
                timestamp=datetime.now()
            ))
    
    def save_conversation(self, filename: Optional[str] = None) -> str:
        """
        Save the conversation to a file.
        
        Args:
            filename: Optional filename (default: session.json)
            
        Returns:
            Path to the saved file
        """
        if filename is None:
            filename = "session.json"
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        if not self.memory_manager._workspace.exists():
            self.memory_manager._workspace.mkdir(parents=True, exist_ok=True)
            logger.info(f"Workspace created: {self.memory_manager._workspace}")

        filepath = self.memory_manager._workspace / filename
        self.memory_manager.save_memory(filepath)
        return str(filepath)
    
    def load_conversation(self, filename: Optional[str] = None) -> int:
        """
        Load a conversation from a file.
        
        Args:
            filename: Optional filename (default: session.json)
            
        Returns:
            Number of messages loaded
        """
        if filename is None:
            filename = "session.json"
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        filepath = self.memory_manager._workspace / filename
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        self.memory_manager.load_memory(filepath)
        messages = self.memory_manager.get_memory()
        return len(messages)
    
    def get_memory(self):
        """Get the current conversation memory."""
        return self.memory_manager.get_memory()
    
    def get_tools_info(self) -> List[Dict[str, str]]:
        """Get information about available tools."""
        tools_info = []
        for tool_name in self.tools:
            try:
                tool_func = tool_registry.get_tool(tool_name)
                tools_info.append({
                    "name": tool_name,
                    "description": getattr(tool_func, 'tool_description', 'No description')
                })
            except Exception as e:
                logger.warning(f"Could not get info for tool {tool_name}: {e}")
        return tools_info
    
    def switch_agent(self, agent_name: str) -> bool:
        """
        Switch to a different agent from the registry.
        
        Args:
            agent_name: Name of the agent to switch to
            
        Returns:
            True if switch was successful, False otherwise
        """
        try:
            # Try to get the agent from registry
            new_agent = agent_registry.get_agent(agent_name)
            
            # Update the agent definition
            self.agent_definition = new_agent
            
            # Update tools if the new agent has different tools
            if new_agent.tools:
                self.tools = new_agent.tools
                self.agent_definition.tools = self.tools
            
            # Update LLM config if the agent has custom config
            if new_agent.llm_config:
                self.model = new_agent.llm_config.model or self.model
                self.temperature = new_agent.llm_config.temperature or self.temperature
                self.max_tokens = new_agent.llm_config.max_tokens or self.max_tokens
            
            # Reinitialize the agent engine with new config
            self._initialize_components()
            
            # Clear history and add new system prompt
            # self.clear_history()
            
            logger.info(f"Switched to agent: {agent_name}")
            return True
            
        except ValueError as e:
            logger.warning(f"Agent '{agent_name}' not found: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to switch agent: {e}")
            return False
    
    def get_current_agent_name(self) -> str:
        """Get the name of the currently active agent."""
        return self.agent_definition.name

import json
from datetime import datetime
from typing import List, Dict, Any, Union, Optional

from exodus.core.models.llm import LLMProvider, LLMProviderResponse
from exodus.core.models.memory import MemoryManager, Message
from exodus.core.models.agent import AgentDefinition, HandoffRequest
from exodus.core.tools.tool_executor import ToolExecutor
from exodus.core.registries import agent_registry
from exodus.settings import settings
from exodus.logs import logger


class AgentEngine:

    def __init__(self, 
        llm_provider: LLMProvider, 
        memory_manager: MemoryManager, 
        tool_executor: ToolExecutor,
        agent_definition: AgentDefinition,
        initial_loop_count: int = 0
    ):
        self.llm_provider = llm_provider
        self.memory_manager = memory_manager
        self.tool_executor = tool_executor
        self.agent_definition = agent_definition
        self.tools_schema = self._build_tools_schema()
        self.handoff_tools_schema = self._build_handoff_tools()
        ### Combine regular tools and handoff tools
        self.all_tools_schema = self.tools_schema + self.handoff_tools_schema
        self.loop_count = initial_loop_count

    def _build_tools_schema(self) -> List[Dict[str, Any]]:
        """Build OpenAI-compatible tools schema from registered tools"""
        tools = []
        for tool_name in self.agent_definition.tools:
            try:
                tool_func = self.tool_executor.tool_registry.get_tool(tool_name)
                if hasattr(tool_func, 'openai_tool_def'):
                    tools.append(tool_func.openai_tool_def)
                else:
                    logger.warning(f"Tool {tool_name} does not have openai_tool_def attribute")
            except Exception as e:
                logger.error(f"Failed to get tool schema for {tool_name}: {e}")

        return tools

    def _build_handoff_tools(self) -> List[Dict[str, Any]]:
        """Build handoff tools from agent's allowed handoffs with descriptions from registry"""
        handoff_tools = []
        for target_agent_name in self.agent_definition.handoffs:
            try:
                ### Get agent description from registry
                target_agent = agent_registry.get_agent(target_agent_name)
                agent_description = target_agent.description or f"Agent: {target_agent_name}"
                
                handoff_tools.append({
                    "type": "function",
                    "function": {
                        "name": f"transfer_to_{target_agent_name}",
                        "description": f"Transfer control to {target_agent_name}. {agent_description}",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "reason": {
                                    "type": "string",
                                    "description": "Explanation of why you are transferring to this agent"
                                }
                            },
                            "required": ["reason"]
                        }
                    }
                })
                logger.info(f"Handoff tool created: transfer_to_{target_agent_name}")
            except ValueError as e:
                logger.warning(f"Handoff target agent '{target_agent_name}' not found in registry: {e}")
            except Exception as e:
                logger.error(f"Failed to create handoff tool for {target_agent_name}: {e}")

        return handoff_tools

    async def run_loop(self, user_input: str) -> Optional[HandoffRequest]:
        """
        Execute the agent loop. Returns HandoffRequest if agent transfers control, None otherwise.
        """
        if user_input:  ### Only add user input if provided (may be empty on handoff continuation)
            self.memory_manager.add_memory(Message(
                role="user", 
                content=user_input,
                timestamp=datetime.now()
            ))

        while self.loop_count < settings.get("agent.max_iterations", 100):
            
            context = self.memory_manager.get_llm_context()

            if self.agent_definition.system_prompt is not None:
                context.insert(0, {
                    "role": "system",
                    "content": self.agent_definition.system_prompt
                })
            
            response: LLMProviderResponse = await self.llm_provider.generate(context, tools_schema=self.all_tools_schema)

            if response.is_tool_call():
                tool_calls = response.get_tool_calls()
                
                self.memory_manager.add_memory(Message(
                    role="assistant", 
                    content=response.get_content(),
                    timestamp=datetime.now(),
                    tool_calls=tool_calls,
                    agent_name=self.agent_definition.name
                ))
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    tool_call_id = tool_call.id
                    
                    ### Check if this is a handoff request
                    if function_name.startswith("transfer_to_"):
                        target_agent_name = function_name.replace("transfer_to_", "")
                        reason = function_args.get("reason", "No reason provided")
                        
                        logger.info(f"Handoff requested from {self.agent_definition.name} to {target_agent_name}")
                        logger.info(f"Handoff reason: {reason}")
                        
                        ### Add handoff message to memory
                        self.memory_manager.add_memory(Message(
                            role="tool",
                            content=f"[Transferring to {target_agent_name}]",
                            timestamp=datetime.now(),
                            tool_call_id=tool_call_id,
                            name=function_name,
                            agent_name=self.agent_definition.name
                        ))
                        
                        ### Return handoff request to orchestrator
                        return HandoffRequest(
                            target_agent_name=target_agent_name,
                            reason=reason,
                            preserve_memory=True
                        )
                    
                    ### Regular tool execution
                    logger.info(f"Executing tool: {function_name}.")
                    logger.debug(f"Executing tool: {function_name} with args: {function_args}")
                    
                    try:
                        tool_result = await self.tool_executor.execute(function_name, function_args)
                        
                        self.memory_manager.add_memory(Message(
                            role="tool",
                            content=str(tool_result),
                            timestamp=datetime.now(),
                            tool_call_id=tool_call_id,
                            name=function_name,
                            agent_name=self.agent_definition.name
                        ))
                        
                        logger.debug(f"Tool {function_name} executed successfully")
                    except Exception as e:
                        logger.error(f"Error executing tool {function_name}: {e}")
                        self.memory_manager.add_memory(Message(
                            role="tool",
                            content=f"Error: {str(e)}",
                            timestamp=datetime.now(),
                            tool_call_id=tool_call_id,
                            name=function_name,
                            agent_name=self.agent_definition.name
                        ))
                    
            else:
                self.memory_manager.add_memory(Message(
                    role="assistant", 
                    content=response.get_content(),
                    timestamp=datetime.now(),
                    agent_name=self.agent_definition.name
                ))
                break

            self.loop_count += 1
        
        ### No handoff occurred, normal completion
        return None

        
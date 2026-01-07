import json
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Optional, Union

from exodus.agent_engine import AgentEngine
from exodus.core.models.agent import AgentDefinition
from exodus.core.models.events import AgentChange, AutomatedEvent, ToolCallEvent, ToolResultEvent
from exodus.core.models.llm import LLMProvider
from exodus.core.models.memory import MemoryManager, Message
from exodus.core.models.plan import Plan, ReflectionAction, TaskStatus
from exodus.core.tools.tool_executor import ToolExecutor
from exodus.engines.automated.checkpoint import CheckpointManager
from exodus.engines.automated.evaluator import Evaluator
from exodus.engines.automated.planner import Planner
from exodus.engines.automated.prompts import build_task_prompt
from exodus.logs import logger
from exodus.settings import settings


class AutomatedAgentEngine(AgentEngine):
    """
    Enhanced AgentEngine for autonomous operation with planning, reflection, and replanning.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        memory_manager: MemoryManager,
        tool_executor: ToolExecutor,
        agent_definition: AgentDefinition,
        initial_loop_count: int = 0,
        checkpoint_dir: Optional[Path] = None,
    ):
        super().__init__(
            llm_provider=llm_provider,
            memory_manager=memory_manager,
            tool_executor=tool_executor,
            agent_definition=agent_definition,
            initial_loop_count=initial_loop_count,
        )

        ### Automated mode settings
        self.plan: Optional[Plan] = None

        ### Initialize components
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        self.planner = Planner(llm_provider, self.checkpoint_manager)
        self.evaluator = Evaluator(llm_provider)

        ### Reflection settings
        self.reflection_iteration_interval = settings.get(
            "agent.automated.reflection_iteration_interval", 25
        )
        self.reflection_task_interval = settings.get("agent.automated.reflection_task_interval", 3)
        self.iterations_since_reflection = 0
        self.tasks_since_reflection = 0
        self.allow_replanning = settings.get("agent.automated.allow_replanning", True)

        ### Quality control
        self.min_task_score = settings.get("agent.automated.min_task_score", 0.3)
        self.enable_validation = settings.get("agent.automated.enable_validation", True)

        logger.debug("AutomatedAgentEngine initialized")
        logger.debug(f"Checkpoint dir: {self.checkpoint_manager.checkpoint_dir}")
        logger.debug(f"Reflection iteration interval: {self.reflection_iteration_interval}")
        logger.debug(f"Reflection task interval: {self.reflection_task_interval}")

    async def run_automated(
        self,
        objective: str,
        context: str = "",
        session_id: str = "default",
        resume: bool = False,
    ) -> AsyncIterator[Union[str, AutomatedEvent]]:
        """
        Execute autonomous agent loop with planning, reflection, and validation.

        Args:
            objective: High-level goal to accomplish
            context: Additional context about the objective
            session_id: Unique identifier for this execution session
            resume: If True, attempt to resume from checkpoint

        Yields:
            - str: Text chunks from agent responses
            - AutomatedEvent: Status events (plan_created, task_started, etc.)
        """

        ### Load or create plan
        if resume:
            self.plan = self.checkpoint_manager.load(session_id)
            if not self.plan:
                ### List available checkpoints to help the user
                available = list(self.checkpoint_manager.checkpoint_dir.glob("plan_*.json"))
                available_ids = [f.stem.replace("plan_", "") for f in available]

                error_msg = f"Cannot resume: checkpoint not found for session '{session_id}'."
                if available_ids:
                    error_msg += "\n\nAvailable sessions:\n  " + "\n  ".join(available_ids)
                else:
                    error_msg += "\n\nNo checkpoints found in exodus_checkpoints/"

                raise ValueError(error_msg)

            ### Reset IN_PROGRESS tasks to PENDING (we can't resume mid-task without conversation context)
            for task in self.plan.tasks:
                if task.status == TaskStatus.IN_PROGRESS:
                    logger.info(
                        f"Resetting task {task.id} from IN_PROGRESS to PENDING (resume without context)"
                    )
                    task.status = TaskStatus.PENDING
                    task.started_at = None
                    ### Keep attempts count so we don't retry indefinitely

            ### Clear current_task_id so the loop will pick it up and start it properly
            if self.plan.current_task_id:
                current_task_for_reset = next(
                    (t for t in self.plan.tasks if t.id == self.plan.current_task_id), None
                )
                if current_task_for_reset and current_task_for_reset.status == TaskStatus.PENDING:
                    logger.info(f"Clearing current_task_id (was: {self.plan.current_task_id})")
                    self.plan.current_task_id = None

            ### Clear memory to start fresh (we don't persist conversation history in checkpoints)
            self.memory_manager.clear_memory()

            ### Plan loaded successfully, emit event to show current state
            progress = self.plan.get_progress_summary()
            yield AutomatedEvent(
                event_type="plan_loaded",
                data={
                    "goal": self.plan.goal,
                    "total_tasks": len(self.plan.tasks),
                    "completed": progress["completed"],
                    "failed": progress["failed"],
                    "pending": progress["pending"],
                    "tasks": [
                        {
                            "id": t.id,
                            "description": t.description,
                            "status": t.status.value,
                            "success_criteria": t.success_criteria,
                            "dependencies": t.dependencies,
                        }
                        for t in self.plan.tasks
                    ],
                },
            )
        else:
            ### Create new plan
            self.plan = await self.planner.create_plan(objective, context, session_id)
            yield AutomatedEvent(
                event_type="plan_created",
                data={
                    "goal": self.plan.goal,
                    "total_tasks": len(self.plan.tasks),
                    "tasks": [
                        {
                            "id": t.id,
                            "description": t.description,
                            "success_criteria": t.success_criteria,
                            "dependencies": t.dependencies,
                        }
                        for t in self.plan.tasks
                    ],
                },
            )

        ### Main execution loop
        current_task_tool_results = []  ### Track tool results for evaluation
        max_iterations_per_task = settings.get("agent.max_iterations", 50)
        logger.debug(
            f"=== AutomatedEngine: max_iterations_per_task = {max_iterations_per_task} ==="
        )

        while self.loop_count < max_iterations_per_task:
            ### Increment iteration counter at the start of each loop
            self.loop_count += 1
            self.iterations_since_reflection += 1

            ### Check if reflection is needed (iteration based - stuck protection)
            if self.iterations_since_reflection >= self.reflection_iteration_interval:
                reflection = await self.evaluator.reflect(self.plan)

                yield AutomatedEvent(
                    event_type="reflection",
                    data={
                        "action": reflection.action.value,
                        "reasoning": reflection.reasoning,
                        "confidence": reflection.confidence,
                        "suggestions": reflection.suggestions,
                    },
                )

                self.iterations_since_reflection = 0

                ### Handle reflection actions
                if reflection.action == ReflectionAction.ESCALATE:
                    logger.warning("Agent requested escalation to human")
                    yield AutomatedEvent(
                        event_type="escalation_requested", data={"reason": reflection.reasoning}
                    )
                    break

                elif reflection.action == ReflectionAction.COMPLETE:
                    logger.info("Agent signals objective complete (via iteration check)")
                    ### Mark all pending tasks as skipped so the loop terminates naturally
                    for t in self.plan.tasks:
                        if t.status == TaskStatus.PENDING:
                            t.status = TaskStatus.SKIPPED
                            t.result = "Skipped due to early completion signal from reflection"
                    continue  # Loop will handle next_task logic

                elif reflection.action == ReflectionAction.REPLAN:
                    logger.info("Agent requested REPLAN (via iteration check)")

                    ### Mark current in-progress task as skipped/interrupted
                    current_task = self.plan.get_current_task()
                    if current_task:
                        current_task.status = TaskStatus.SKIPPED
                        current_task.result = (
                            f"Skipped for replanning. Reason: {reflection.reasoning}"
                        )
                        current_task.completed_at = datetime.now()
                        self.plan.current_task_id = None

                    ### Execute replanning
                    self.plan = await self.planner.replan(
                        self.plan, reflection.reasoning, session_id
                    )

                    yield AutomatedEvent(
                        event_type="plan_updated",
                        data={
                            "goal": self.plan.goal,
                            "total_tasks": len(self.plan.tasks),
                            "tasks": [
                                {
                                    "id": t.id,
                                    "description": t.description,
                                    "status": t.status.value,
                                }
                                for t in self.plan.tasks
                            ],
                            "reason": reflection.reasoning,
                        },
                    )

                    ### Reset counters and continue loop to pick up new task
                    self.loop_count = 0
                    self.iterations_since_reflection = 0
                    continue

            ### Get current or next task
            current_task = self.plan.get_current_task()
            if not current_task:
                next_task = self.plan.get_next_task()
                if not next_task:
                    ### All tasks processed
                    progress = self.plan.get_progress_summary()
                    logger.info("═══ PLAN EXECUTION COMPLETE ═══")
                    logger.info(f"Completed: {progress['completed']}/{progress['total_tasks']}")
                    logger.info(f"Failed: {progress['failed']}")
                    logger.info(f"Avg score: {progress['avg_score']:.2f}")

                    yield AutomatedEvent(event_type="plan_completed", data={"progress": progress})
                    break

                ### Start new task
                next_task.status = TaskStatus.IN_PROGRESS
                next_task.started_at = datetime.now()
                next_task.attempts += 1
                self.plan.current_task_id = next_task.id
                current_task = next_task

                ### Reset loop count for new task
                logger.info(
                    f"=== Resetting loop_count from {self.loop_count} to 0 for new task ==="
                )
                self.loop_count = 0
                self.iterations_since_reflection = 0

                logger.info(f"=== Starting Task: {current_task.id} ===")
                logger.debug(f"Description: {current_task.description}")
                logger.debug(f"Attempt {current_task.attempts}/{current_task.max_attempts}")

                ### Reset tool results for new task
                current_task_tool_results = []

                yield AutomatedEvent(
                    event_type="task_started",
                    data={
                        "task_id": current_task.id,
                        "description": current_task.description,
                        "attempt": current_task.attempts,
                    },
                )

                ### Save checkpoint
                self.checkpoint_manager.save(self.plan, session_id)

                ### Add initial task prompt as user message
                task_prompt = build_task_prompt(current_task, self.plan)
                self.memory_manager.add_memory(
                    Message(
                        role="user",
                        content=task_prompt,
                        timestamp=datetime.now(),
                    )
                )

            ### Execute agent loop for this task
            context_messages = self.memory_manager.get_llm_context()

            if self.agent_definition.system_prompt:
                context_messages.insert(
                    0, {"role": "system", "content": self.agent_definition.system_prompt}
                )

            ### Stream response
            chunks = []
            full_content = []

            async for chunk in self.llm_provider.generate_stream(
                context_messages, tools_schema=self.all_tools_schema
            ):
                chunks.append(chunk)
                try:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        full_content.append(delta.content)
                        yield delta.content
                except (AttributeError, IndexError):
                    pass

            ### Rebuild response
            response = self.llm_provider.rebuild_response(chunks)
            response_text = "".join(full_content)

            ### Handle tool calls
            if response.is_tool_call():
                tool_calls = response.get_tool_calls()
                yield ToolCallEvent(tool_calls=tool_calls)

                self.memory_manager.add_memory(
                    Message(
                        role="assistant",
                        content=response.get_content(),
                        timestamp=datetime.now(),
                        tool_calls=tool_calls,
                        agent_name=self.agent_definition.name,
                    )
                )

                handoff_occurred = False
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    tool_call_id = tool_call.id

                    ### Check if this is a handoff request
                    if function_name.startswith("transfer_to_"):
                        target_agent_name = function_name.replace("transfer_to_", "")
                        reason = function_args.get("reason", "No reason provided")

                        logger.info(
                            f"Handoff requested from {self.agent_definition.name} to {target_agent_name}"
                        )
                        logger.debug(f"Handoff reason: {reason}")

                        ### Add handoff message to memory
                        self.memory_manager.add_memory(
                            Message(
                                role="tool",
                                content=f"[Transferring to {target_agent_name}]",
                                timestamp=datetime.now(),
                                tool_call_id=tool_call_id,
                                name=function_name,
                                agent_name=self.agent_definition.name,
                            )
                        )

                        ### Yield AgentChange event
                        yield AgentChange(new_agent_name=target_agent_name, reason=reason)

                        ### Load new agent and continue
                        from exodus.core.registries import agent_registry

                        self.agent_definition = agent_registry.get_agent(target_agent_name)

                        ### Rebuild tools schema for new agent
                        self.tools_schema = self._build_tools_schema()
                        self.handoff_tools_schema = self._build_handoff_tools()
                        self.all_tools_schema = self.tools_schema + self.handoff_tools_schema

                        ### Add a user message for the new agent to continue the task
                        task = self.plan.get_current_task()
                        continuation_msg = f"Continue working on: {task.description}\n\nSuccess criteria: {task.success_criteria}"
                        self.memory_manager.add_memory(
                            Message(
                                role="user",
                                content=continuation_msg,
                                timestamp=datetime.now(),
                            )
                        )

                        logger.info(f"Switched to {target_agent_name}, continuing task execution")
                        handoff_occurred = True
                        break

                    ### Regular tool execution
                    logger.info(f"Executing tool: {function_name}")
                    logger.debug(f"Tool args: {function_args}")

                    try:
                        tool_result = await self.tool_executor.execute(function_name, function_args)

                        ### Yield tool result event for display
                        yield ToolResultEvent(
                            tool_name=function_name,
                            tool_args=function_args,
                            result=str(tool_result),
                        )

                        self.memory_manager.add_memory(
                            Message(
                                role="tool",
                                content=str(tool_result),
                                timestamp=datetime.now(),
                                tool_call_id=tool_call_id,
                                name=function_name,
                                agent_name=self.agent_definition.name,
                            )
                        )

                        ### Track tool result for task evaluation
                        current_task_tool_results.append(
                            f"{function_name}: {str(tool_result)[:200]}"
                        )

                        logger.debug(f"Tool {function_name} executed successfully")
                    except Exception as e:
                        logger.error(f"Error executing tool {function_name}: {e}")
                        error_msg = f"Error: {str(e)}"

                        ### Yield error as tool result
                        yield ToolResultEvent(
                            tool_name=function_name, tool_args=function_args, result=error_msg
                        )

                        self.memory_manager.add_memory(
                            Message(
                                role="tool",
                                content=error_msg,
                                timestamp=datetime.now(),
                                tool_call_id=tool_call_id,
                                name=function_name,
                                agent_name=self.agent_definition.name,
                            )
                        )

                ### If handoff occurred, continue main loop with new agent
                if handoff_occurred:
                    continue

            else:
                ### Non-tool response - evaluate task completion with LLM
                response_text = response.get_content()
                self.memory_manager.add_memory(
                    Message(
                        role="assistant",
                        content=response_text,
                        timestamp=datetime.now(),
                        agent_name=self.agent_definition.name,
                    )
                )

                ### Evaluate task status with structured output
                current_task = self.plan.get_current_task()
                if current_task:
                    evaluation = await self.evaluator.evaluate_task_completion(
                        current_task, response_text, current_task_tool_results
                    )

                    if evaluation:
                        ### Task has completed or failed
                        if evaluation.is_completed:
                            current_task.status = TaskStatus.COMPLETED
                        elif evaluation.is_failed:
                            current_task.status = TaskStatus.FAILED

                        current_task.result = evaluation.result
                        current_task.observations = evaluation.observations
                        current_task.score = evaluation.score
                        current_task.completed_at = datetime.now()
                        self.plan.current_task_id = None

                        logger.info(
                            f"Task {current_task.id} {'COMPLETED' if evaluation.is_completed else 'FAILED'}: {evaluation.result}"
                        )
                        logger.debug(f"Evaluation reasoning: {evaluation.reasoning}")

                        if evaluation.is_completed:
                            yield AutomatedEvent(
                                event_type="task_completed",
                                data={
                                    "task_id": current_task.id,
                                    "result": evaluation.result,
                                    "observations": evaluation.observations,
                                    "score": evaluation.score,
                                },
                            )
                        else:
                            yield AutomatedEvent(
                                event_type="task_failed",
                                data={"task_id": current_task.id, "result": evaluation.result},
                            )

                        ### Increment task counter for reflection
                        self.tasks_since_reflection += 1

                        ### Check if reflection is needed (task based - strategic review)
                        if self.tasks_since_reflection >= self.reflection_task_interval:
                            reflection = await self.evaluator.reflect(self.plan)

                            yield AutomatedEvent(
                                event_type="reflection",
                                data={
                                    "action": reflection.action.value,
                                    "reasoning": reflection.reasoning,
                                    "confidence": reflection.confidence,
                                    "suggestions": reflection.suggestions,
                                },
                            )

                            self.tasks_since_reflection = 0

                            if reflection.action == ReflectionAction.ESCALATE:
                                logger.warning(
                                    "Agent requested escalation to human during task review"
                                )
                                yield AutomatedEvent(
                                    event_type="escalation_requested",
                                    data={"reason": reflection.reasoning},
                                )
                                break

                            elif reflection.action == ReflectionAction.COMPLETE:
                                logger.info("Agent signals objective complete (via task check)")
                                ### Mark all pending tasks as skipped
                                for t in self.plan.tasks:
                                    if t.status == TaskStatus.PENDING:
                                        t.status = TaskStatus.SKIPPED
                                        t.result = (
                                            "Skipped due to early completion signal from reflection"
                                        )
                                ### Continue naturally - loop will find no next tasks and finish

                            elif reflection.action == ReflectionAction.REPLAN:
                                logger.info("Agent requested REPLAN (via task check)")

                                ### Execute replanning
                                self.plan = await self.planner.replan(
                                    self.plan, reflection.reasoning, session_id
                                )

                                yield AutomatedEvent(
                                    event_type="plan_updated",
                                    data={
                                        "goal": self.plan.goal,
                                        "total_tasks": len(self.plan.tasks),
                                        "tasks": [
                                            {
                                                "id": t.id,
                                                "description": t.description,
                                                "status": t.status.value,
                                            }
                                            for t in self.plan.tasks
                                        ],
                                        "reason": reflection.reasoning,
                                    },
                                )
                                ### Continue naturally to pick up next task from new plan

                        ### Save checkpoint after task completion
                        self.checkpoint_manager.save(self.plan, session_id)

                        ### Reset tool results for next task
                        current_task_tool_results = []

                        ### Reset loop count since task is complete (next iteration will be new task)
                        self.loop_count = 0
                        self.iterations_since_reflection = 0
                        continue

        ### Handle max iterations reached
        logger.warning("=== MAX ITERATIONS REACHED ===")

        ### Check if there's an active task and evaluate it
        current_task = self.plan.get_current_task()
        if current_task:
            logger.info(f"Evaluating incomplete task {current_task.id} before stopping")

            ### Get last agent response from memory
            last_messages = self.memory_manager.get_llm_context()[-3:]
            last_response = ""
            for msg in reversed(last_messages):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    last_response = msg.get("content", "")
                    break

            ### Evaluate task one last time
            evaluation = await self.evaluator.evaluate_task_completion(
                current_task, last_response, current_task_tool_results
            )

            if evaluation and (evaluation.is_completed or evaluation.is_failed):
                ### Task finished
                current_task.status = (
                    TaskStatus.COMPLETED if evaluation.is_completed else TaskStatus.FAILED
                )
                current_task.result = evaluation.result
                current_task.observations = evaluation.observations
                current_task.score = evaluation.score
                current_task.completed_at = datetime.now()
                self.plan.current_task_id = None

                logger.info(
                    f"Task {current_task.id} evaluated as {'COMPLETED' if evaluation.is_completed else 'FAILED'}"
                )

                yield AutomatedEvent(
                    event_type="task_completed" if evaluation.is_completed else "task_failed",
                    data={
                        "task_id": current_task.id,
                        "result": evaluation.result,
                        "observations": evaluation.observations,
                        "score": evaluation.score if evaluation.is_completed else 0.0,
                    },
                )
            else:
                ### Task still in progress - mark as incomplete
                logger.warning(f"Task {current_task.id} incomplete at max iterations")
                yield AutomatedEvent(
                    event_type="max_iterations_reached",
                    data={
                        "task_id": current_task.id,
                        "description": current_task.description,
                        "iterations": self.loop_count,
                    },
                )

        ### Save final checkpoint
        self.checkpoint_manager.save(self.plan, session_id)

        ### Show final progress
        progress = self.plan.get_progress_summary()
        logger.info(
            f"Final state: {progress['completed']}/{progress['total_tasks']} completed, {progress['failed']} failed"
        )

        logger.debug("=== AUTOMATED EXECUTION ENDED ===")

from datetime import datetime
from typing import List

from exodus.core.models.llm import LLMProvider
from exodus.core.models.plan import LLMGeneratedPlan, Plan, Task, TaskStatus
from exodus.engines.automated.checkpoint import CheckpointManager
from exodus.engines.automated.prompts import build_planning_prompt, build_replanning_prompt
from exodus.logs import logger


class Planner:
    """Handles plan creation and modification"""

    def __init__(self, llm_provider: LLMProvider, checkpoint_manager: CheckpointManager):
        """
        Initialize planner.

        Args:
            llm_provider: LLM provider for generating plans
            checkpoint_manager: Checkpoint manager for saving plans
        """
        self.llm_provider = llm_provider
        self.checkpoint_manager = checkpoint_manager

    async def create_plan(self, objective: str, context: str = "", session_id: str = "default") -> Plan:
        """
        Create structured plan using LLM with Pydantic validation.

        Args:
            objective: High-level goal to accomplish
            context: Additional context about the objective
            session_id: Unique session identifier for checkpoint saving

        Returns:
            Generated Plan object
        """
        logger.debug("=== PLANNING START ===")
        logger.debug(f"Objective: {objective}")
        logger.debug(f"Context: {context}")

        planning_prompt = build_planning_prompt(objective, context)
        llm_context = [{"role": "user", "content": planning_prompt}]

        try:
            ### Use structured output with Pydantic model
            response = await self.llm_provider.generate(
                llm_context, tools_schema=None, output_schema=LLMGeneratedPlan
            )

            plan_json = response.get_content()

            ### Parse with Pydantic (auto-validated)
            llm_plan = LLMGeneratedPlan.model_validate_json(plan_json)

            ### Convert LLMGeneratedTask to runtime Task with state
            tasks = [
                Task(
                    id=t.id,
                    description=t.description,
                    success_criteria=t.success_criteria,
                    dependencies=t.dependencies,
                    max_attempts=t.max_attempts,
                )
                for t in llm_plan.tasks
            ]

            plan = Plan(goal=llm_plan.goal, context=llm_plan.context or context, tasks=tasks)

            logger.debug(f"=== Plan created with {len(tasks)} tasks ===")
            for i, task in enumerate(tasks, 1):
                deps = f" (deps: {', '.join(task.dependencies)})" if task.dependencies else ""
                logger.debug(f"  {i}. {task.id}: {task.description[:60]}{deps}")

            self.checkpoint_manager.save(plan, session_id)
            return plan

        except Exception as e:
            logger.error("=== PLANNING FAILED ===")
            logger.error(f"Exception: {e}")
            logger.warning("Creating fallback single-task plan")

            return Plan(
                goal=objective,
                context=context,
                tasks=[
                    Task(id="task_1", description=objective, success_criteria="Objective achieved")
                ],
            )

    async def replan(self, plan: Plan, reasoning: str, session_id: str = "default") -> Plan:
        """
        Regenerate plan for remaining tasks based on reflection.

        Args:
            plan: Current plan to be modified
            reasoning: Reason for replanning from reflection
            session_id: Unique session identifier for checkpoint saving

        Returns:
            Updated Plan object with new tasks
        """
        logger.debug("=== REPLANNING START ===")
        logger.debug(f"Reasoning: {reasoning}")

        ### Filter history (completed, failed, skipped tasks)
        completed_tasks = [
            t
            for t in plan.tasks
            if t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED]
        ]

        history_str = "\n".join(
            [
                f"- {t.id} ({t.status.value}): {t.description}\n  Result: {t.result}"
                for t in completed_tasks
            ]
        )

        replanning_prompt = build_replanning_prompt(
            objective=plan.goal,
            context=plan.context,
            history=history_str,
            reasoning=reasoning,
        )

        llm_context = [{"role": "user", "content": replanning_prompt}]

        try:
            ### Generate new tasks
            response = await self.llm_provider.generate(
                llm_context, tools_schema=None, output_schema=LLMGeneratedPlan
            )

            plan_json = response.get_content()
            llm_plan = LLMGeneratedPlan.model_validate_json(plan_json)

            ### Create new task list: Keep history + Append new tasks
            new_tasks: List[Task] = []

            # 1. Keep history
            new_tasks.extend(completed_tasks)

            # 2. Add new tasks (with ID collision prevention)
            for t in llm_plan.tasks:
                # If ID exists in history, append suffix to make it unique
                if any(existing.id == t.id for existing in new_tasks):
                    t.id = f"{t.id}_new"

                new_tasks.append(
                    Task(
                        id=t.id,
                        description=t.description,
                        success_criteria=t.success_criteria,
                        dependencies=t.dependencies,
                        max_attempts=t.max_attempts,
                    )
                )

            plan.tasks = new_tasks
            plan.updated_at = datetime.now()
            plan.version += 1

            logger.info(f"Plan updated. Total tasks: {len(plan.tasks)}")
            self.checkpoint_manager.save(plan, session_id)

            return plan

        except Exception as e:
            logger.error(f"Replanning failed: {e}")
            return plan  # Return original plan on failure

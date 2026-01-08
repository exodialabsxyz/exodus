from typing import List, Optional

from exodus.core.models.llm import LLMProvider
from exodus.core.models.plan import Plan, ReflectionResult, Task, TaskEvaluation
from exodus.engines.automated.prompts import (
    build_reflection_prompt,
    build_task_evaluation_prompt,
)
from exodus.logs import logger


class Evaluator:
    """Handles task evaluation and progress reflection"""

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize evaluator.

        Args:
            llm_provider: LLM provider for evaluation and reflection
        """
        self.llm_provider = llm_provider

    async def evaluate_task_completion(
        self, task: Task, agent_response: str, tool_results: List[str]
    ) -> Optional[TaskEvaluation]:
        """
        Use LLM to evaluate if task is completed with structured output.

        Args:
            task: Task to evaluate
            agent_response: Latest response from the agent
            tool_results: Recent tool execution results

        Returns:
            TaskEvaluation if task status determined (completed/failed), None if still in progress
        """
        evaluation_prompt = build_task_evaluation_prompt(task, agent_response, tool_results)

        try:
            llm_context = [{"role": "user", "content": evaluation_prompt}]

            response = await self.llm_provider.generate(
                llm_context,
                tools_schema=None,
                output_schema=TaskEvaluation,
            )

            eval_json = response.get_content()
            evaluation = TaskEvaluation.model_validate_json(eval_json)

            logger.debug(
                f"Task evaluation: completed={evaluation.is_completed}, failed={evaluation.is_failed}"
            )
            logger.debug(f"Reasoning: {evaluation.reasoning}")

            ### Return None if task is still in progress
            if not evaluation.is_completed and not evaluation.is_failed:
                return None

            return evaluation

        except Exception as e:
            logger.error(f"Task evaluation failed: {e}")
            return None

    async def reflect(self, plan: Plan) -> ReflectionResult:
        """
        Perform reflection/critique on progress.

        Args:
            plan: Current plan to reflect on

        Returns:
            ReflectionResult with action and reasoning
        """
        logger.debug("=== REFLECTION START ===")

        reflection_prompt = build_reflection_prompt(plan)

        context = [{"role": "user", "content": reflection_prompt}]
        response = await self.llm_provider.generate(
            context, tools_schema=None, output_schema=ReflectionResult
        )
        result = ReflectionResult.model_validate_json(response.get_content())

        logger.debug(f"Reflection -> {result.action.value} (confidence: {result.confidence:.2f})")
        logger.debug(f"Reasoning: {result.reasoning}")

        return result

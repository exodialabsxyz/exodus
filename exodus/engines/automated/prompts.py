from exodus.core.models.plan import Plan, Task

planning_prompt_template = """Create an execution plan for this security task:

OBJECTIVE: {objective}

{context}

PLANNING PRINCIPLES:
1. **Decompose systematically**: Break into logical, sequential steps
2. **Define success criteria**: Each task must have clear completion criteria
3. **Set dependencies**: Enforce logical order (e.g., task_2 depends on task_1)
4. **Plan for failure**: Allow 3 attempts per task for resilience

EXAMPLE TASK SEQUENCE FOR CTF:
- task_1: Port scan and service discovery
- task_2: Web/SMB enumeration (depends on task_1 findings)
- task_3: Vulnerability identification
- task_4: Exploit development/selection
- task_5: Exploitation
- task_6: Post-exploitation/flag capture

Generate a structured plan with 5-10 tasks that logically progress toward the objective."""


replanning_prompt_template = """
REPLANNING REQUIRED

OBJECTIVE: {objective}

CONTEXT: {context}

COMPLETED TASKS (HISTORY):
{history}

REASON FOR REPLANNING:
{reasoning}

INSTRUCTIONS:
1. Review the history and the reason for replanning.
2. Generate a NEW sequence of tasks to complete the remaining part of the objective.
3. Do NOT include tasks that are already completed (unless they need to be redone).
4. Ensure new tasks logicaly follow the completed ones.

Generate a structured plan with the necessary tasks to finish the mission."""


task_prompt_template = """
# MISSION: {goal}

PROGRESS: {completed}/{total_tasks} tasks ({completion_rate})

PREVIOUS TASKS:
{previous_tasks}

CURRENT TASK:
    ID: {id}
    TASK: {description}
    SUCCESS CRITERIA: {success_criteria}
    ATTEMPT: {current_attempt}/{max_attempts}

# REACT METHODOLOGY:
1. **THOUGHT**: Analyze what needs to be done and plan your approach
2. **ACTION**: Execute commands/tools to complete the task
3. **OBSERVATION**: Review results and determine if task succeeded

# EXECUTION RULES:
- SPECIALTY CHECK: Before acting, verify if you are the best specialist for THIS specific task. If another agent (e.g., recon, exploit, web_exploit, privesc, triage) is better suited, use the 'transfer_to_<agent_name>' tool immediately to hand off the task.
- FOCUS: Work ONLY on the current task, ignore other tasks
- SINGLE-THREAD: Complete one action before starting another
- VERIFY: Check results match the success criteria
- DOCUMENT: Note key findings in your response
- BE EXPLICIT: When done, state "TASK_COMPLETED: <brief result>" or "TASK_FAILED: <reason>"

# REPORTING

When task succeeds, include:
- TASK_COMPLETED: <one-line summary>
- KEY_FINDINGS: <comma-separated important discoveries>
- SCORE: <0-10, your assessment of success quality>

When task fails, include:
- TASK_FAILED: <specific reason>
- NEXT_STEPS: <what should be tried instead>

Now you are going to begin your reasoning.
"""


reflection_prompt_template = """
REFLECTION CHECKPOINT

MISSION: {goal}
PROGRESS: {completed}/{total_tasks} ({completion_rate})
AVG SCORE: {avg_score}

RECENT TASKS:
{recent_summary}

QUESTIONS:
1. Making meaningful progress toward objective?
2. Current approach effective or pivot needed?
3. Stuck in loops or repeating failures?

RESPONSE FORMAT:

+ ACTION: [CONTINUE|REPLAN|ESCALATE|COMPLETE]
+ REASONING: <brief explanation>
+ CONFIDENCE: <0-10>
"""


task_evaluation_prompt_template = """Evaluate if this task has been completed or failed.

TASK:
ID: {task_id}
Description: {description}
Success Criteria: {success_criteria}
Attempts: {attempts}/{max_attempts}

AGENT'S LATEST RESPONSE:
{agent_response}

RECENT TOOL RESULTS:
{tool_results}

Determine:
1. is_completed: true if success criteria met
2. is_failed: true if task cannot be completed or max attempts reached
3. result: brief summary of outcome
4. observations: key findings (list of strings)
5. score: 0.0-1.0 quality assessment
6. reasoning: why you determined this status
"""


def build_planning_prompt(objective: str, context: str = "") -> str:
    """Build prompt for plan generation"""
    return planning_prompt_template.format(objective=objective, context=context)


def build_replanning_prompt(objective: str, context: str, history: str, reasoning: str) -> str:
    """Build prompt for plan regeneration"""
    return replanning_prompt_template.format(
        objective=objective, context=context, history=history, reasoning=reasoning
    )


def build_task_prompt(task: Task, plan: Plan) -> str:
    """Build focused prompt for task execution using ReACT pattern"""
    from exodus.core.models.plan import TaskStatus

    progress = plan.get_progress_summary()

    ### Previous tasks (history: completed, failed, or skipped)
    history = [
        t
        for t in plan.tasks
        if t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED]
    ]
    previous_tasks = (
        "\n".join(
            [
                f"{t.id} [{t.status.value}]: {t.description}\n  Result: {t.result[:150] if t.result else 'No result'}...\n  Key findings: {', '.join(t.observations[:5]) if t.observations else 'None'}"
                for t in history
            ]
        )
        if history
        else "None yet"
    )

    return task_prompt_template.format(
        goal=plan.goal,
        completed=progress["completed"],
        total_tasks=progress["total_tasks"],
        completion_rate=f"{progress['completion_rate']:.0%}",
        previous_tasks=previous_tasks,
        id=task.id,
        description=task.description,
        success_criteria=task.success_criteria,
        attempts=task.attempts,
        current_attempt=task.attempts + 1,
        max_attempts=task.max_attempts,
    )


def build_reflection_prompt(plan: Plan) -> str:
    """Build prompt for progress reflection"""
    from exodus.core.models.plan import TaskStatus

    progress = plan.get_progress_summary()

    ### Recent task results
    recent = [t for t in plan.tasks if t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]][-5:]
    recent_summary = "\n".join(
        [
            f"{'COMPLETED' if t.status == TaskStatus.COMPLETED else 'FAILED'} {t.id}: {t.description}\n"
            f"  Result: {t.result}\n"
            f"  Score: {t.score:.1f}"
            for t in recent
        ]
    )

    return reflection_prompt_template.format(
        goal=plan.goal,
        completed=progress["completed"],
        total_tasks=progress["total_tasks"],
        completion_rate=f"{progress['completion_rate']:.0%}",
        avg_score=f"{progress['avg_score']:.2f}",
        recent_summary=recent_summary,
    )


def build_task_evaluation_prompt(task: Task, agent_response: str, tool_results: list) -> str:
    """Build prompt for task completion evaluation"""
    tool_results_str = "\n".join(tool_results[-10:]) if tool_results else "No tool results yet"

    return task_evaluation_prompt_template.format(
        task_id=task.id,
        description=task.description,
        success_criteria=task.success_criteria,
        attempts=task.attempts,
        max_attempts=task.max_attempts,
        agent_response=agent_response,
        tool_results=tool_results_str,
    )

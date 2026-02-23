from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from exodus.logs import logger


class TaskStatus(str, Enum):
    """Status of a task in a plan"""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class ReflectionAction(str, Enum):
    """Action to take after reflection"""

    CONTINUE = "CONTINUE"
    REPLAN = "REPLAN"
    ESCALATE = "ESCALATE"
    COMPLETE = "COMPLETE"


class LLMGeneratedTask(BaseModel):
    """Task structure for LLM generation (simpler, no status/attempts)"""

    id: str
    description: str
    success_criteria: str = ""
    dependencies: List[str] = Field(default_factory=list)
    max_attempts: int = 3


class LLMGeneratedPlan(BaseModel):
    """Plan structure for LLM generation"""

    goal: str
    context: str = ""
    tasks: List[LLMGeneratedTask] = Field(default_factory=list)


class ReflectionResult(BaseModel):
    """Result of a reflection/critique cycle"""

    action: ReflectionAction
    reasoning: str
    suggestions: List[str] = Field(default_factory=list)
    confidence: float = 0.5


class TaskEvaluation(BaseModel):
    """Evaluation of task completion status"""

    is_completed: bool
    is_failed: bool = False
    result: str
    observations: List[str] = Field(default_factory=list)
    score: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: str = ""


class Task(BaseModel):
    """A single task in the execution plan (runtime version with state)"""

    id: str
    description: str
    success_criteria: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    score: float = 0.0
    observations: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True

    def can_start(self, completed_task_ids: set) -> bool:
        """Check if all dependencies are satisfied"""
        if not self.dependencies:
            return True
        return all(dep_id in completed_task_ids for dep_id in self.dependencies)

    def is_exhausted(self) -> bool:
        """Check if task has exceeded max attempts"""
        return self.attempts >= self.max_attempts


class Plan(BaseModel):
    """Represents a structured execution plan with tasks"""

    goal: str
    context: str = ""
    tasks: List[Task] = Field(default_factory=list)
    current_task_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: int = 1

    class Config:
        arbitrary_types_allowed = True

    def get_current_task(self) -> Optional[Task]:
        """Get the currently active task"""
        if not self.current_task_id:
            return None
        ### None as next argument in order to avoid an error when no task is found
        return next((t for t in self.tasks if t.id == self.current_task_id), None)

    def get_next_task(self) -> Optional[Task]:
        """Get next pending task with all dependencies completed"""
        completed_ids = {t.id for t in self.tasks if t.status == TaskStatus.COMPLETED}

        ### TODO: Better an Iterator to change PENDING status (avoid one if per execution loop)
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue

            if task.is_exhausted():
                task.status = TaskStatus.FAILED
                logger.warning(f"Task {task.id} exhausted max attempts")
                continue

            if task.can_start(completed_ids):
                return task

        return None

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get summary of plan progress"""

        completed = 0
        failed = 0
        in_progress = 0
        total = 0

        for task in self.tasks:
            total += 1
            match task.status:
                case TaskStatus.COMPLETED:
                    completed += 1
                case TaskStatus.FAILED:
                    failed += 1
                case TaskStatus.IN_PROGRESS:
                    in_progress += 1
                case _:
                    pass

        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": total - completed - failed - in_progress,
            "completion_rate": completed / total if total > 0 else 0,
            "avg_score": completed / max(completed, 1) if completed > 0 else 0,
        }

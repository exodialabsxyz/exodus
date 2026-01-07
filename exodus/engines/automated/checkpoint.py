from pathlib import Path
from typing import Optional

from exodus.core.models.plan import Plan
from exodus.logs import logger


def _sanitize_session_id(session_id: str) -> str:
    """
    Sanitize session_id to prevent path injection or malformed IDs.

    Extracts the actual session ID if user accidentally passes a full path.

    Examples:
        "./exodus_checkpoints/plan_my_session.json" -> "my_session"
        "plan_my_session.json" -> "my_session"
        "my_session" -> "my_session"
    """
    # If it looks like a path, extract just the filename
    if "/" in session_id or "\\" in session_id:
        session_id = Path(session_id).name

    # Remove "plan_" prefix if present
    if session_id.startswith("plan_"):
        session_id = session_id[5:]

    # Remove ".json" extension if present
    if session_id.endswith(".json"):
        session_id = session_id[:-5]

    return session_id


class CheckpointManager:
    """Manages plan checkpoints for automated execution"""

    def __init__(self, checkpoint_dir: Optional[Path] = None):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoints (default: ./exodus_checkpoints)
        """
        self.checkpoint_dir = checkpoint_dir or Path("./exodus_checkpoints")
        self.checkpoint_dir.mkdir(exist_ok=True, parents=True)
        logger.debug(f"CheckpointManager initialized with dir: {self.checkpoint_dir}")

    def get_checkpoint_path(self, session_id: str = "default") -> Path:
        """Get path to checkpoint file for a given session"""
        session_id = _sanitize_session_id(session_id)
        return self.checkpoint_dir / f"plan_{session_id}.json"

    def save(self, plan: Plan, session_id: str = "default") -> bool:
        """
        Save plan state to disk using Pydantic serialization.

        Args:
            plan: Plan object to save
            session_id: Unique session identifier

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            checkpoint_path = self.get_checkpoint_path(session_id)
            with open(checkpoint_path, "w") as f:
                f.write(plan.model_dump_json(indent=2))
            logger.debug(f"Checkpoint saved: {checkpoint_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False

    def load(self, session_id: str = "default") -> Optional[Plan]:
        """
        Load plan state from disk using Pydantic deserialization.

        Args:
            session_id: Unique session identifier

        Returns:
            Plan object if found and valid, None otherwise
        """
        checkpoint_path = self.get_checkpoint_path(session_id)

        if not checkpoint_path.exists():
            logger.debug(f"No checkpoint found at {checkpoint_path}")
            return None

        try:
            with open(checkpoint_path, "r") as f:
                plan = Plan.model_validate_json(f.read())

            progress = plan.get_progress_summary()
            logger.info(
                f"Checkpoint loaded: {progress['completed']}/{progress['total_tasks']} tasks completed"
            )
            return plan

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def exists(self, session_id: str = "default") -> bool:
        """Check if a checkpoint exists for the given session"""
        return self.get_checkpoint_path(session_id).exists()

    def delete(self, session_id: str = "default") -> bool:
        """
        Delete a checkpoint file.

        Args:
            session_id: Unique session identifier

        Returns:
            True if deletion succeeded, False otherwise
        """
        checkpoint_path = self.get_checkpoint_path(session_id)
        try:
            if checkpoint_path.exists():
                checkpoint_path.unlink()
                logger.info(f"Checkpoint deleted: {checkpoint_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete checkpoint: {e}")
            return False

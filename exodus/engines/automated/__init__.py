"""
Automated execution engine for autonomous agent operation.

This module provides an automated engine that can execute plans autonomously
with planning, reflection, replanning, and checkpointing capabilities.

Main components:
- AutomatedAgentEngine: The main engine class
- create_automated_engine: Factory function for easy setup

Example:
    >>> from exodus.engines.automated import create_automated_engine
    >>> engine = create_automated_engine("recon_agent", "my_session")
    >>> async for event in engine.run_automated("Scan target"):
    ...     print(event)
"""

from exodus.engines.automated.engine import AutomatedAgentEngine
from exodus.engines.automated.factory import create_automated_engine

__all__ = ["AutomatedAgentEngine", "create_automated_engine"]

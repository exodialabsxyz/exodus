from exodus.core.decorators import tool
from exodus.plugins.core_tools.session import (
    session_close,
    session_interact,
    session_list,
    session_open,
    session_read,
)


@tool(
    name="core_tools_bash",
    type="cli",
    description="Executes a Linux command and returns the output. You must be careful with the command you use, it must be a 'oneline' command.",
)
def bash(command: str) -> str:
    """Executes a Linux command and returns the output."""
    return command


@tool(
    name="core_tools_sum",
    type="python",
    description="Just a sum for testing",
)
def sum(a: int, b: int) -> int:
    return a + b


class CoreToolsPlugin:
    @staticmethod
    def get_tools():
        return {
            bash.tool_name: bash,
            sum.tool_name: sum,
            ### Session tools - always registered, will fail with clear error if tmux not available
            session_open.tool_name: session_open,
            session_interact.tool_name: session_interact,
            session_read.tool_name: session_read,
            session_list.tool_name: session_list,
            session_close.tool_name: session_close,
        }

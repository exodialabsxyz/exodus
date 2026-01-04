import asyncio

from exodus.core.decorators import tool
from exodus.plugins.core_tools.session import shell


@tool(
    name="sum",
    type="python",
    description="Just a sum for testing",
)
def sum(a: int, b: int) -> int:
    return a + b


@tool(
    name="wait",
    type="cli",
    description="Waits for a specified amount of time",
)
async def wait(seconds: int = 30) -> str:
    """Waits for a specified amount of time. Default is 30 seconds."""
    await asyncio.sleep(seconds)
    return f"Waited for {seconds} seconds"


class CoreToolsPlugin:
    @staticmethod
    def get_tools():
        return {
            sum.tool_name: sum,
            wait.tool_name: wait,
            shell.tool_name: shell,
        }

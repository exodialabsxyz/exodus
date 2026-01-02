from exodus.core.decorators import tool


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
        return {bash.tool_name: bash, sum.tool_name: sum}

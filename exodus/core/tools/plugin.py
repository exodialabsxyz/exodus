from exodus.core.decorators import tool


@tool(
    name="core_bash",
    type="cli",
    description="Executes a Linux command and returns the output. You must be careful with the command you use, it must be a 'oneline' command.",
)
def core_bash_tool(command: str) -> str:
    """Executes a Linux command and returns the output."""
    return command


@tool(
    name="core_sum",
    type="python",
    description="Just a sum for testing",
)
def sum(a: int, b: int) -> int:
    return a + b


class CorePlugin:
    @staticmethod
    def get_tools():
        return {core_bash_tool.tool_name: core_bash_tool, sum.tool_name: sum}

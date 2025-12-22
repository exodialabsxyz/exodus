from exodus.core.decorators import tool

@tool(name="core_bash", type="cli", description="Executes a Linux command and returns the output. You must be careful with the command you use, it must be a 'oneline' command.")
def core_bash_tool(command: str) -> str:
    """Executes a Linux command and returns the output."""
    return command

class CorePlugin:
    @staticmethod
    def get_tools():
        return {
            core_bash_tool.tool_name: core_bash_tool,
        }
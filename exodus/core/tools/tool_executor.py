from exodus.core.registries import tool_registry
from exodus.core.tools.drivers.docker_executor_driver import DockerExecutorDriver
from exodus.core.tools.drivers.local_executor_driver import LocalExecutorDriver
from exodus.settings import settings


class ToolExecutor:
    def __init__(self):
        self.execution_mode = settings.get("agent.execution_mode", "local")
        self.tool_registry = tool_registry

        if self.execution_mode in ["local", "python"]:
            self.driver = LocalExecutorDriver()
        elif self.execution_mode == "docker":
            self.driver = DockerExecutorDriver()
        else:
            raise ValueError(f"Invalid execution mode: {self.execution_mode}")

    async def execute(self, tool_name: str, tool_args: dict):
        try:
            tool_function = self.tool_registry.get_tool(tool_name)
            tool_type = getattr(tool_function, "tool_type", "python")

            return await self.driver.execute(
                tool_type=tool_type, tool_function=tool_function, **tool_args
            )
        except Exception as e:
            raise ValueError(f"Failed to execute tool {tool_name}: {e}")

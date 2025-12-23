import asyncio
from typing import Callable

from exodus.core.models.tool import ToolExecutionDriver
from exodus.logs import logger


class LocalExecutorDriver(ToolExecutionDriver):
    async def execute(self, tool_type: str, tool_function: Callable, **tool_args) -> str:
        try:
            if tool_type == "cli":
                command = tool_function(**tool_args)
                if not isinstance(command, str):
                    raise ValueError(f"CLI tool must return a string command, got {type(command)}")

                logger.debug(f"Executing CLI command: {command}")
                proc = await asyncio.create_subprocess_shell(
                    command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()

                if proc.returncode != 0:
                    error_msg = stderr.decode().strip()
                    logger.error(f"CLI tool execution failed: {error_msg}")
                    return f"Error: {error_msg}"

                result = stdout.decode().strip()
                logger.debug(f"CLI tool execution result: {result}")
                return result

            elif tool_type == "python":
                if asyncio.iscoroutinefunction(tool_function):
                    return await tool_function(**tool_args)
                else:
                    return tool_function(**tool_args)

            else:
                return f"Error: Unsupported tool type '{tool_type}'"

        except Exception as e:
            logger.error(f"Local execution error: {e}")
            return f"Failed to execute tool: {str(e)}"

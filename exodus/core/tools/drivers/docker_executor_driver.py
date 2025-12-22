from typing import Callable
from exodus.core.models.tool import ToolExecutionDriver
import docker

from exodus.settings import settings
from exodus.logs import logger

class DockerExecutorDriver(ToolExecutionDriver):
    def __init__(self):
        self.docker_client = docker.from_env()
        self.default_image = settings.get("agent.execution.docker.default_image")
        self.default_image_name = settings.get("agent.execution.docker.default_image_name")

    async def execute(self, tool_type: str, tool_function: Callable, **tool_args) -> str:
        try:
            if tool_type == "cli":
                command = tool_function(**tool_args)
                if not isinstance(command, str):
                    raise ValueError(f"CLI tool must return a string command, got {type(command)}")

                ### First of all check if the container is running and if not, start it
                try:
                    container = self.docker_client.containers.get(self.default_image_name)
                except docker.errors.NotFound:
                    logger.warning(f"Docker container '{self.default_image_name}' not found, starting it")
                    container = self.docker_client.containers.run(
                        image=self.default_image,
                        name=self.default_image_name,
                        detach=True,
                        tty=True,
                        command="/bin/bash",
                        stdin_open=True
                    )
                except Exception as e:
                    logger.error(f"Error getting Docker container '{self.default_image_name}': {e}")
                    return f"Failed to execute tool: {str(e)}"

                if container.status != "running":
                    logger.warning(f"Docker container '{self.default_image_name}' is not running, starting it")
                    container.start()

                ### Then execute the command
                logger.info(f"Executing command '{command}' in Docker container '{self.default_image_name}'")
                result = container.exec_run(command, stdout=True, stderr=True)
                return result.output.decode('utf-8').strip()
            else:
                logger.error(f"Unsupported tool type: {tool_type}")
                
        except Exception as e:
            logger.error(f"Docker execution error: {e}")
            return f"Failed to execute tool: {str(e)}"
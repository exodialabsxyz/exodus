import base64
import json
from typing import Callable

import docker
from exodus.core.models.tool import ToolExecutionDriver
from exodus.logs import logger
from exodus.settings import settings


class DockerExecutorDriver(ToolExecutionDriver):
    def __init__(self):
        self.docker_client = docker.from_env()
        self.default_image = settings.get("agent.execution.docker.default_image")
        self.default_image_name = settings.get("agent.execution.docker.default_image_name")

    def _get_or_create_container(self) -> docker.models.containers.Container:
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
                stdin_open=True,
            )
        except Exception as e:
            logger.error(f"Error getting Docker container '{self.default_image_name}': {e}")
            return f"Failed to execute tool: {str(e)}"

        if container.status != "running":
            logger.warning(
                f"Docker container '{self.default_image_name}' is not running, starting it"
            )
            container.start()

        return container

    async def execute(self, tool_type: str, tool_function: Callable, **tool_args) -> str:
        try:
            if tool_type == "cli":
                command = tool_function(**tool_args)
                if not isinstance(command, str):
                    raise ValueError(f"CLI tool must return a string command, got {type(command)}")

                container = self._get_or_create_container()
                logger.info(f"Executing command '{command}' in Docker container '{container.name}'")
                result = container.exec_run(command, stdout=True, stderr=True)
                return result.output.decode("utf-8").strip()
            elif tool_type == "python":
                tool_name = tool_function.tool_name

                logger.info(f"Executing Python tool '{tool_name}' via executor server")

                try:
                    container = self._get_or_create_container()
                    ### Encode tool arguments as base64 JSON
                    tool_args_json = json.dumps(tool_args)
                    tool_args_b64 = base64.b64encode(tool_args_json.encode()).decode()

                    ### Build the exodus-server-exec command
                    command = f"exodus-server-exec --tool-name {tool_name} --tool-args-b64 {tool_args_b64}"

                    logger.info(f"Executing command: {command}")
                    result = container.exec_run(command, stdout=True, stderr=True)
                    output = result.output.decode("utf-8").strip()

                    ### Parse the JSON response
                    try:
                        response = json.loads(output)
                        if response.get("status") == "success":
                            result_data = response.get("message", "")
                            logger.info(f"Tool '{tool_name}' executed successfully")
                            return str(result_data)
                        else:
                            error_msg = response.get("message", "Unknown error")
                            logger.error(f"Tool '{tool_name}' failed: {error_msg}")
                            return f"Error: {error_msg}"
                    except json.JSONDecodeError:
                        ### If output is not JSON, return it as-is
                        logger.warning(f"Non-JSON response from tool '{tool_name}': {output}")
                        return output

                except Exception as e:
                    logger.error(f"Failed to execute Python tool via exodus-server-exec: {e}")
                    return f"Failed to execute tool: {str(e)}"
            else:
                logger.error(f"Unsupported tool type: {tool_type}")
                return f"Unsupported tool type: {tool_type}"

        except Exception as e:
            logger.error(f"Docker execution error: {e}")
            return f"Failed to execute tool: {str(e)}"

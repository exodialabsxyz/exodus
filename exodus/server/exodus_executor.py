"""
This server runs in the background, instantiating the Exodus tool registry and waiting for messages for execution.

Client Message Format:

{
    "id": "uuid",
    "command": "command",
    "tool_name" : "tool_name", (optional)
    "tool_args" : "tool_args", (optional)
}

Server Response Format:

{
    "status": "status",
    "message": "message"
}

TODO:
+ Currently the communication is implemented in base64, which is sufficient but could be improved.
+ The executor only support one connection per execution.

"""

import asyncio
import base64
import inspect
import json
import logging
import socket
import threading
import uuid
from pathlib import Path
from typing import Any, Dict

from exodus.core.registries.tool_registry import ToolPluginRegistry


class ExodusExecutor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._socket_address = Path("/tmp/exodus/executor.sock")
        self._socket = None
        self.is_running = False

        try:
            self.logger.info("Loading the tool registry for the server; no plugins by default")
            self._tool_registry = ToolPluginRegistry()
            self._tool_registry.load_from_plugins()
            self.logger.info("All done! The tool registry was loaded!")
            self._socket_setup()
        except Exception as e:
            self.logger.error(f"There was an error loading the server: {e}")
            self._clean_server()

    def _socket_setup(self):
        if self._socket_address.exists():
            try:
                self._socket_address.unlink()
            except OSError:
                raise

        socket_dir = self._socket_address.parent
        if not socket_dir.exists():
            socket_dir.mkdir(parents=True, exist_ok=True)

        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(str(self._socket_address))
        self._socket.listen(10)

        self._socket_address.chmod(666)
        self.logger.info(f"Socket created on: {self._socket_address}")

    def _process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        command = message.get("command", "unknown")
        message_id = message.get("id", 0)
        self.logger.info(f"[{message_id}] Processing message with command {command}")

        if command == "ping":
            return {"status": "success", "message": "pong"}
        elif command == "list_tools":
            tool_list = self._tool_registry.get_tool_list()
            return {"status": "success", "message": tool_list}
        elif command == "execute":
            tool_name = message.get("tool_name", None)
            tool_args = message.get("tool_args", {})

            if not tool_name:
                return {"status": "error", "message": "Tool name is required"}

            try:
                tool_func = self._tool_registry.get_tool(tool_name=tool_name)

                # Check if the tool is async and handle accordingly
                if inspect.iscoroutinefunction(tool_func):
                    result = asyncio.run(tool_func(**tool_args))
                else:
                    result = tool_func(**tool_args)

                return {"status": "success", "message": result}
            except Exception as e:
                self.logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": "The command is invalid; please try again"}

    def _handle_client(self, client_socket: socket.socket, client_address: str):
        message_id = str(uuid.uuid4())
        try:
            self.logger.info(f"[{message_id}] New client connection")

            base64_data = b""
            while True:
                data_chunk = client_socket.recv(4096)
                if not data_chunk:
                    break
                base64_data += data_chunk
                if b"\n" in data_chunk:
                    break

            base64_data = base64_data.strip()
            json_bytes = base64.b64decode(base64_data)

            message = json.loads(json_bytes.decode("utf-8"))
            message["id"] = message_id

            self.logger.info(
                f"[{message_id}] The message of type {message.get('command', 'unknown')} was received"
            )

            response = self._process_message(message=message)

            response_json = json.dumps(response).encode("utf-8")
            response_base64 = base64.b64encode(response_json) + b"\n"
            client_socket.sendall(response_base64)
        except Exception as e:
            self.logger.error(f"Error handling client: {e}", exc_info=True)
            try:
                error_response = {"status": "error", "message": str(e)}
                error_json = json.dumps(error_response).encode("utf-8")
                error_base64 = base64.b64encode(error_json) + b"\n"
                client_socket.sendall(error_base64)
            except Exception as send_error:
                self.logger.error(f"Failed to send error response: {send_error}")
        finally:
            client_socket.close()

    def _clean_server(self):
        self.logger.info("Cleaning all ...")
        if self._socket:
            self._socket.close()
        if self._socket_address.exists():
            self._socket_address.unlink()

    def run(self):
        try:
            self.logger.info("Waiting...")
            self.is_running = True
            while self.is_running:
                try:
                    self._socket.settimeout(3.0)
                    try:
                        client_socket, client_address = self._socket.accept()
                        client_thread = threading.Thread(
                            target=self._handle_client,
                            args=(client_socket, client_address),
                            daemon=True,
                        )
                        client_thread.start()
                    except socket.timeout:
                        continue
                except Exception as e:
                    self.logger.error(f"There was an error on the server: {e}")
        except Exception:
            self.logger.error("There was an error or the server was interrupted")
        finally:
            self._clean_server()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
        force=True,
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    server = ExodusExecutor()
    server.run()


if __name__ == "__main__":
    main()

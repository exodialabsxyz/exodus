import base64
import json
import socket
from pathlib import Path
from typing import Any, Dict, Optional


class ExodusExecutorClient:
    def __init__(self, socket_path: str = "/tmp/exodus/executor.sock"):
        self.socket_path = Path(socket_path)

    def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        if not self.socket_path.exists():
            return {
                "status": "error",
                "message": "The socket was not found. The executor is not available",
            }

        response = None
        client_socket = None

        try:
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.connect(str(self.socket_path))

            json_message = json.dumps(message).encode("utf-8")
            base64_package = base64.b64encode(json_message) + b"\n"
            client_socket.sendall(base64_package)

            base64_data = b""
            while True:
                data_chunk = client_socket.recv(4096)
                if not data_chunk:
                    break
                base64_data += data_chunk
                if b"\n" in data_chunk:
                    break

            base64_data = base64_data.strip()
            json_bytes = base64.b64decode(base64_data.strip())
            response = json.loads(json_bytes.decode("utf-8"))
        except Exception:
            raise
        finally:
            if client_socket:
                client_socket.close()

        return response

    def ping(self) -> Dict[str, Any]:
        return self.send_message({"command": "ping"})

    def list_tools(self) -> Dict[str, Any]:
        return self.send_message({"command": "list_tools"})

    def execute_tool(
        self, tool_name: str, tool_args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if tool_args is None:
            tool_args = {}

        return self.send_message(
            {"command": "execute", "tool_name": tool_name, "tool_args": tool_args}
        )


def send_message(message: Dict[str, Any]) -> Dict[str, Any]:
    client = ExodusExecutorClient()
    return client.send_message(message)


def main():
    client = ExodusExecutorClient()

    try:
        print("=== Testing Exodus Executor Client ===\n")

        print("1. Testing ping...")
        ping_response = client.ping()
        print(f"   Response: {ping_response}\n")

        print("2. Testing list_tools...")
        tools_response = client.list_tools()
        print(f"   Response: {tools_response}\n")

        print("3. Testing execute (bash)...")
        bash_response = client.execute_tool("core_bash", {"command": "ls -la"})
        print(f"   Response: {bash_response}\n")

        print("4. Testing execute (sum)...")
        sum_response = client.execute_tool("core_sum", {"a": 3, "b": 5})
        print(f"   Response: {sum_response}\n")

        print("=== All tests completed ===")
    except Exception as e:
        print(f"There was an error: {e}")


if __name__ == "__main__":
    main()

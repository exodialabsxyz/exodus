# EXODUS Docker Images

Building custom Docker images for execution and development in isolated and specific environments.

---

## 🐳 Exodus Security Executor

Security image based on **ParrotSec 7.0** with an EXODUS daemon running in the background to execute EXODUS Python tools in an isolated environment.

### Purpose

This container allows agents to execute Python-based tools from the EXODUS tool registry in an isolated, security-focused environment. The server loads the tool registry on startup and listens for execution requests via Unix socket.

### Building the Image

From the project root:

```bash
docker build -t exodus-security-executor -f docker/exodus_security_executor/Dockerfile .
```

**Features:**
- Installs EXODUS using `uv` for fast package management
- Copies only necessary files (`pyproject.toml`, `README.md`, `exodus/`)
- Automatically starts `exodus-server` on container launch
- Virtual environment with `cli` and `docker` extras installed

### Running the Container

```bash
# Run in daemon mode
docker run -d --name exodus-executor exodus-security-executor

# View logs
docker logs -f exodus-executor

# Stop and remove
docker stop exodus-executor
docker rm exodus-executor
```

### Communication Protocol

The server accepts base64-encoded JSON messages via Unix socket at `/tmp/exodus/executor.sock`.

**Available commands:**
- `ping` - Health check
- `list_tools` - Get available tools from registry
- `execute` - Run a specific tool with arguments

**Request format:**
```json
{
  "command": "execute",
  "tool_name": "my_tool",
  "tool_args": {"arg1": "value1"}
}
```

**Response format:**
```json
{
  "status": "success",
  "message": "result"
}
```

### Python Client Example

```python
import socket
import base64
import json

def send_command(command_dict):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect("/tmp/exodus/executor.sock")
    
    message = base64.b64encode(json.dumps(command_dict).encode()) + b'\n'
    sock.sendall(message)
    
    response = b""
    while b'\n' not in response:
        response += sock.recv(4096)
    
    result = json.loads(base64.b64decode(response.strip()))
    sock.close()
    return result

# Example usage
print(send_command({"command": "ping"}))
print(send_command({"command": "list_tools"}))
```

### Using the Built-in CLI Client

```bash
exodus-server-exec ping
exodus-server-exec list-tools
exodus-server-exec execute --tool-name core_echo --tool-args '{"message": "test"}'
```

---

## 📝 Resources

- **Main README**: [`../README.md`](../README.md)
- **Server Implementation**: `exodus/server/exodus_executor.py`
- **GitHub**: https://github.com/exodialabsxyz/exodus

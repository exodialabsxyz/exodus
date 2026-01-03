import subprocess

import libtmux

from exodus.core.decorators import tool


def _get_session_server():
    """Get the tmux server, validating its availability"""
    try:
        ### Check if tmux is installed
        result = subprocess.run(
            ["sh", "-c", "command -v tmux"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "tmux is not installed in the execution environment. "
                "Session tools require tmux to be available."
            )

        ### Connect to the tmux server
        session_server = libtmux.Server()
        return session_server

    except subprocess.TimeoutExpired:
        raise RuntimeError("Timeout while checking tmux availability")
    except Exception as e:
        raise RuntimeError(f"Failed to connect to tmux server: {e}")


@tool(
    name="core_tools_session_open",
    type="python",
    description="Opens a new interactive tmux session with a specific name and executes a command in it. Use this for long-running or interactive commands like netcat listeners, SSH sessions, or msfconsole.",
)
def session_open(session_name: str, command: str) -> str:
    """Opens a new tmux session and executes a command"""
    try:
        session_server = _get_session_server()

        ### Check if session already exists
        existing_sessions = session_server.sessions
        for sess in existing_sessions:
            if sess.name == session_name:
                return f"Error: Session '{session_name}' already exists. Use a different name or close it first."

        ### Create new session
        new_session = session_server.new_session(session_name=session_name, attach=False)

        ### Get the first pane and send the command
        pane = new_session.active_pane
        if pane:
            pane.send_keys(command)

        return f"Session '{session_name}' created successfully and command '{command}' executed."

    except Exception as e:
        return f"Error creating session: {str(e)}"


@tool(
    name="core_tools_session_interact",
    type="python",
    description="Sends input (commands or text) to an existing tmux session. Use this to interact with running sessions like typing commands in a shell, entering passwords, or sending data.",
)
def session_interact(session_name: str, input: str) -> str:
    """Sends input to an existing tmux session"""
    try:
        session_server = _get_session_server()

        ### Find the session
        session = None
        for sess in session_server.sessions:
            if sess.name == session_name:
                session = sess
                break

        if not session:
            return f"Error: Session '{session_name}' not found. Use session_list to see available sessions."

        ### Get the active pane and send input
        pane = session.active_pane
        if pane:
            pane.send_keys(input)
            return f"Input sent to session '{session_name}' successfully."
        else:
            return f"Error: No active pane found in session '{session_name}'."

    except Exception as e:
        return f"Error sending input to session: {str(e)}"


@tool(
    name="core_tools_session_read",
    type="python",
    description="Reads the output from an existing tmux session. Captures the last N lines (default 50) to see what's happening in the session. Use this to check command results, see prompts, or verify connections.",
)
def session_read(session_name: str, lines: int = 50) -> str:
    """Reads output from a tmux session"""
    try:
        session_server = _get_session_server()

        ### Find the session
        session = None
        for sess in session_server.sessions:
            if sess.name == session_name:
                session = sess
                break

        if not session:
            return f"Error: Session '{session_name}' not found. Use session_list to see available sessions."

        ### Get the active pane and capture content
        pane = session.active_pane
        if pane:
            ### Capture the pane content
            captured = pane.capture_pane()

            ### Get last N lines
            if captured:
                all_lines = captured if isinstance(captured, list) else captured.split("\n")
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                output = "\n".join(last_lines)
                return f"Output from session '{session_name}':\n{output}"
            else:
                return f"Session '{session_name}' has no output yet."
        else:
            return f"Error: No active pane found in session '{session_name}'."

    except Exception as e:
        return f"Error reading from session: {str(e)}"


@tool(
    name="core_tools_session_list",
    type="python",
    description="Lists all active tmux sessions with their names and status. Use this to see what sessions are currently running and available for interaction.",
)
def session_list() -> str:
    """Lists all active tmux sessions"""
    try:
        session_server = _get_session_server()
        sessions = session_server.sessions

        if not sessions:
            return "No active sessions found."

        session_info = []
        for sess in sessions:
            session_info.append(
                {
                    "name": sess.name,
                    "windows": len(sess.windows),
                    "attached": sess.attached,
                }
            )

        ### Format output
        output = "Active sessions:\n"
        for info in session_info:
            output += (
                f"  - {info['name']}: {info['windows']} window(s), attached: {info['attached']}\n"
            )

        return output

    except Exception as e:
        return f"Error listing sessions: {str(e)}"


@tool(
    name="core_tools_session_close",
    type="python",
    description="Closes and terminates a specific tmux session by name. Use this to clean up sessions that are no longer needed.",
)
def session_close(session_name: str) -> str:
    """Closes a tmux session"""
    try:
        session_server = _get_session_server()

        ### Find the session
        session = None
        for sess in session_server.sessions:
            if sess.name == session_name:
                session = sess
                break

        if not session:
            return f"Error: Session '{session_name}' not found. Use session_list to see available sessions."

        ### Kill the session
        session.kill()
        return f"Session '{session_name}' closed successfully."

    except Exception as e:
        return f"Error closing session: {str(e)}"

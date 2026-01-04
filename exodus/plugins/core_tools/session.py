import subprocess
from typing import Literal, Optional

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


def _session_create(session_name: str, command: str) -> str:
    """Creates a new tmux session and executes a command"""
    try:
        session_server = _get_session_server()

        ### Check if session already exists
        existing_sessions = session_server.sessions
        for sess in existing_sessions:
            if sess.name == session_name:
                return f"Error: Session '{session_name}' already exists. Use a different name or close it first."

        ### Create new session with large history buffer
        new_session = session_server.new_session(session_name=session_name, attach=False)

        ### Set a large history limit for this session (50000 lines)
        new_session.set_option("history-limit", 50000)

        ### Get the first pane and send the command
        pane = new_session.active_pane
        if pane:
            pane.send_keys(command)

        return f"Session '{session_name}' created successfully and command '{command}' executed."

    except Exception as e:
        return f"Error creating session: {str(e)}"


def _session_interact(session_name: str, input_text: str) -> str:
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
            return f"Error: Session '{session_name}' not found. Use action='list' to see available sessions."

        ### Get the active pane and send input
        pane = session.active_pane
        if pane:
            pane.send_keys(input_text)
            return f"Input sent to session '{session_name}' successfully."
        else:
            return f"Error: No active pane found in session '{session_name}'."

    except Exception as e:
        return f"Error sending input to session: {str(e)}"


def _session_read(session_name: str, lines: int = 50) -> str:
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
            return f"Error: Session '{session_name}' not found. Use action='list' to see available sessions."

        ### Get the active pane and capture content
        pane = session.active_pane
        if pane:
            ### Capture the full pane history using libtmux API
            captured = pane.capture_pane(start="-", end="-")

            ### Get last N lines
            if captured:
                all_lines = captured if isinstance(captured, list) else captured.split("\n")
                total_lines = len(all_lines)
                last_lines = all_lines[-lines:] if total_lines > lines else all_lines
                output = "\n".join(last_lines)

                # Inform if output is truncated
                if total_lines > lines:
                    truncated_msg = f"\n\n[OUTPUT TRUNCATED: Showing last {lines} of {total_lines} total lines. Use lines={total_lines} or higher to see all output.]"
                    return f"Output from session '{session_name}':\n{output}{truncated_msg}"
                else:
                    return f"Output from session '{session_name}' ({total_lines} lines):\n{output}"
            else:
                return f"Session '{session_name}' has no output yet."
        else:
            return f"Error: No active pane found in session '{session_name}'."

    except Exception as e:
        return f"Error reading from session: {str(e)}"


def _session_list() -> str:
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
                    "attached": sess.session_attached,
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


def _session_kill(session_name: str) -> str:
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
            return f"Error: Session '{session_name}' not found. Use action='list' to see available sessions."

        ### Kill the session
        session.kill()
        return f"Session '{session_name}' closed successfully."

    except Exception as e:
        return f"Error closing session: {str(e)}"


@tool(
    name="shell",
    type="python",
    description="Unified shell management tool. Manages interactive shells for running commands. Actions: 'create' (new session with command), 'interact' (send input to session), 'read' (capture session output), 'list' (show all sessions), 'kill' (close session).",
)
def shell(
    action: Literal["create", "interact", "read", "list", "kill"],
    session_name: Optional[str] = None,
    command: Optional[str] = None,
    args: Optional[str] = None,
    lines: int = 50,
) -> str:
    """
    Unified tmux session management tool.

    Args:
        action: Action to perform (create, interact, read, list, kill)
        session_name: Name of the session (required for all actions except 'list')
        command: Command to execute (for 'create') or input to send (for 'interact')
        args: Arguments for the command (concatenated with command for 'create')
        lines: Number of lines to read from session output (default 50, used only for 'read' action)

    Returns:
        String with the result of the operation
    """

    ### Validate required parameters based on action
    if action == "create":
        if not session_name:
            return "Error: 'session_name' is required for action 'create'"
        if not command:
            return "Error: 'command' is required for action 'create'"

        # Concatenate command and args
        full_command = command
        if args:
            full_command = f"{command} {args}"

        return _session_create(session_name, full_command)

    elif action == "interact":
        if not session_name:
            return "Error: 'session_name' is required for action 'interact'"
        if not command:
            return "Error: 'command' is required for action 'interact' (use it to send input)"
        return _session_interact(session_name, command)

    elif action == "read":
        if not session_name:
            return "Error: 'session_name' is required for action 'read'"
        return _session_read(session_name, lines)

    elif action == "list":
        return _session_list()

    elif action == "kill":
        if not session_name:
            return "Error: 'session_name' is required for action 'kill'"
        return _session_kill(session_name)

    else:
        return (
            f"Error: Unknown action '{action}'. Valid actions: create, interact, read, list, kill"
        )

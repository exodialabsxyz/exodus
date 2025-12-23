"""
Display utilities for the Exodus CLI using Rich library.
"""

from contextlib import contextmanager
from typing import Any, Dict, Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.text import Text

console = Console()


def print_banner(
    agent_name: Optional[str] = None, model: Optional[str] = None, tools_count: int = 0
):
    """Display the Exodus CLI banner."""
    title = Text()
    title.append("EXODUS", style="bold cyan")
    title.append(" Agentic CLI", style="cyan")

    info_lines = []
    if agent_name:
        info_lines.append(f"[dim]Agent:[/dim] [green]{agent_name}[/green]")
    if model:
        info_lines.append(f"[dim]Model:[/dim] [blue]{model}[/blue]")
    if tools_count > 0:
        info_lines.append(f"[dim]Tools:[/dim] {tools_count}")

    subtitle = "\n".join(info_lines) if info_lines else "[dim]Interactive AI Assistant[/dim]"

    panel = Panel(subtitle, title=title, border_style="cyan", padding=(0, 1))
    console.print(panel)
    console.print("[dim]Type your message or /help for commands[/dim]\n")


def print_user_message(content: str):
    """Display a user message."""
    console.print(f"\n[bold cyan]You:[/bold cyan] {content}")


def print_assistant_chunk(chunk: str):
    """Print a chunk of the assistant response without newlines."""
    console.print(chunk, end="", style="green")


@contextmanager
def stream_assistant_response(agent_name: str):
    """
    Context manager for streaming assistant response with live updating panel.

    Usage:
        with stream_assistant_response("agent_name") as updater:
            async for chunk in stream:
                updater(chunk)
    """
    content_buffer = []
    char_count = [0]  # Use list to allow mutation in nested function

    def update_content(chunk: str):
        content_buffer.append(chunk)
        full_text = "".join(content_buffer)
        return Panel(
            Markdown(full_text),
            title=f"[bold green]{agent_name}[/bold green]",
            title_align="left",
            border_style="green",
            padding=(1, 2),
        )

    class StreamUpdater:
        def __init__(self, live):
            self.live = live

        def __call__(self, chunk: str):
            # Accumulate chunk
            content_buffer.append(chunk)
            char_count[0] += len(chunk)

            # Update panel every 3 characters or if chunk is large
            if char_count[0] >= 3 or len(chunk) > 10:
                full_text = "".join(content_buffer)
                panel = Panel(
                    Markdown(full_text),
                    title=f"[bold green]{agent_name}[/bold green]",
                    title_align="left",
                    border_style="green",
                    padding=(1, 2),
                )
                self.live.update(panel, refresh=True)
                char_count[0] = 0  # Reset counter

    # Start with empty panel
    initial_panel = Panel(
        "",
        title=f"[bold green]{agent_name}[/bold green]",
        title_align="left",
        border_style="green",
        padding=(1, 2),
    )

    console.print()  # Add newline before the panel
    with Live(initial_panel, console=console, refresh_per_second=15) as live:
        updater = StreamUpdater(live)
        yield updater
        # Final update to ensure all content is displayed
        final_panel = Panel(
            Markdown("".join(content_buffer)),
            title=f"[bold green]{agent_name}[/bold green]",
            title_align="left",
            border_style="green",
            padding=(1, 2),
        )
        live.update(final_panel, refresh=True)


def print_assistant_message(content: str, agent_name: Optional[str] = None):
    """Display an assistant message with markdown rendering."""
    agent_label = agent_name if agent_name else "Assistant"

    if content:
        console.print()
        panel = Panel(
            Markdown(content),
            title=f"[bold green]{agent_label}[/bold green]",
            title_align="left",
            border_style="green",
            padding=(1, 2),
        )
        console.print(panel)
    else:
        console.print(f"\n[bold green]{agent_label}:[/bold green] [dim](no text response)[/dim]")


def print_system_message(content: str):
    """Display a system message."""
    console.print(f"[dim]{content}[/dim]")


def print_error(message: str, exception: Optional[Exception] = None):
    """Display an error message."""
    error_text = f"[bold red]Error:[/bold red] {message}"
    if exception:
        error_text += f"\n[red]{str(exception)}[/red]"

    panel = Panel(error_text, border_style="red", padding=(0, 1))
    console.print()
    console.print(panel)


def print_tool_execution(tool_name: str, args: Dict[str, Any]):
    """Display tool execution information."""
    args_str = str(args) if args else "None"

    # Use Text with overflow handling for better wrapping
    content = Text()
    content.append("Tool: ", style="bold")
    content.append(f"{tool_name}\n")
    content.append("Arguments: ", style="bold")
    content.append(args_str)

    panel = Panel(
        content,
        title="[yellow]Tool Call[/yellow]",
        border_style="yellow",
        padding=(0, 1),
        expand=False,
    )
    console.print()
    console.print(panel)


def print_tool_result(tool_name: str, result: Any):
    """Display tool execution result."""
    result_str = str(result)

    # Use Text for better wrapping
    content = Text(result_str)

    panel = Panel(
        content,
        title=f"[yellow]Tool Result: {tool_name}[/yellow]",
        border_style="yellow",
        padding=(0, 1),
        expand=False,
    )
    console.print(panel)


def print_thinking():
    """Show a thinking indicator."""
    console.print("[dim]Processing...[/dim]")


def show_spinner(message: str = "Processing"):
    """Create a spinner status for long operations."""
    return Status(f"[dim]{message}...[/dim]", console=console, spinner="dots")


def print_help():
    """Display help information."""
    help_content = """
[bold cyan]COMMANDS[/bold cyan]

[bold]Session Management[/bold]
  [green]/exit[/green], [green]/quit[/green]     Exit the CLI
  [green]/clear[/green]             Clear conversation history
  [green]/save[/green] [filename]   Save conversation (default: session.json)
  [green]/load[/green] [filename]   Load conversation (default: session.json)

[bold]Agent Management[/bold]
  [green]/agents[/green]            List available agents
  [green]/switch[/green] <name>     Switch to a different agent
  [green]/tools[/green]             List available tools

[bold]Help[/bold]
  [green]/help[/green]              Show this help message

[bold cyan]EXAMPLES[/bold cyan]

  Switch agent:    [dim]/switch code_assistant[/dim]
  Save session:    [dim]/save my_conversation[/dim]
  Load session:    [dim]/load my_conversation[/dim]

[bold cyan]USAGE[/bold cyan]

Simply type your message and press Enter to chat. The agent
has access to tools and will use them when appropriate.
    """

    panel = Panel(
        help_content.strip(),
        title="[bold]Exodus CLI Help[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def print_tools_list(tools: list):
    """Display available tools."""
    if not tools:
        console.print("\n[yellow]No tools configured[/yellow]\n")
        return

    table = Table(title="Available Tools", border_style="cyan", show_lines=False, padding=(0, 1))
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="green")
    table.add_column("Description", style="dim")

    for idx, tool_info in enumerate(tools, 1):
        if isinstance(tool_info, dict):
            table.add_row(
                str(idx),
                tool_info.get("name", "Unknown"),
                tool_info.get("description", "No description"),
            )
        else:
            table.add_row(str(idx), str(tool_info), "")

    console.print()
    console.print(table)
    console.print()


def print_agents_list(agents: list, current_agent: Optional[str] = None):
    """Display available agents."""
    if not agents:
        console.print("\n[yellow]No agents available[/yellow]\n")
        return

    table = Table(title="Available Agents", border_style="cyan", show_lines=False, padding=(0, 1))
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="green")
    table.add_column("Description", style="dim")
    table.add_column("Status", style="yellow", width=10)

    for idx, agent_info in enumerate(agents, 1):
        if isinstance(agent_info, dict):
            name = agent_info.get("name", "Unknown")
            description = agent_info.get("description", "No description")
            is_current = agent_info.get("is_current", False) or (name == current_agent)

            status = "[>] Active" if is_current else ""

            table.add_row(str(idx), name, description, status)
        else:
            table.add_row(str(idx), str(agent_info), "", "")

    console.print()
    console.print(table)
    console.print("[dim]Use /switch <agent_name> to change agent[/dim]\n")


def print_agent_switched(agent_name: str):
    """Display confirmation of agent switch."""
    console.print(f"\n[green]Switched to:[/green] [bold]{agent_name}[/bold]")
    console.print("[dim]Conversation history preserved[/dim]\n")


def print_conversation_saved(filename: str):
    """Display confirmation of saved conversation."""
    console.print(f"\n[green]Saved:[/green] {filename}\n")


def print_conversation_loaded(filename: str, message_count: int):
    """Display confirmation of loaded conversation."""
    console.print(f"\n[green]Loaded:[/green] {message_count} messages from {filename}\n")


def print_conversation_cleared():
    """Display confirmation of cleared conversation."""
    console.print("\n[yellow]Conversation history cleared[/yellow]\n")


def get_input(prompt: str = "You", agent_name: Optional[str] = None) -> str:
    """Get user input with a styled prompt."""
    try:
        return console.input(f"[bold cyan]{prompt}:[/bold cyan] ")
    except (KeyboardInterrupt, EOFError):
        return "/exit"


def print_goodbye():
    """Display goodbye message."""
    console.print("\n[cyan]Goodbye[/cyan]\n")

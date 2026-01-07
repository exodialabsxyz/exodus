"""
Main Exodus CLI application using Typer.
"""

import asyncio
import json
import random
from typing import Optional

import typer

### Light imports first
from exodus.cli import display
from exodus.logs import logger

LOADING_PHRASES = [
    "To hack or to be hacked, that is the question",
    "L-l-l-l-l-look at you, hacker. A pa-pa-pathetic creature of meat and bone ... How can you challenge a perfect, immortal machine? — SHODAN",
]

app = typer.Typer(
    name="exodus-cli",
    help="Exodus Agentic CLI - Interactive AI assistant with tools",
    add_completion=False,
)


async def run_chat_loop(session):
    """
    Run the main chat loop.

    Args:
        session: Active chat session
    """
    from exodus.cli.commands import CommandHandler
    from exodus.core.models.events import AgentChange, ToolCallEvent, ToolResultEvent

    command_handler = CommandHandler(session)

    # Get tools info
    tools_info = session.get_tools_info()

    # Display banner with agent name, model, and tools count
    display.print_banner(
        agent_name=session.agent_definition.name, model=session.model, tools_count=len(tools_info)
    )

    # Main loop
    while True:
        try:
            # Get user input
            user_input = display.get_input()

            # Skip empty input
            if not user_input.strip():
                continue

            # Check if it's a command
            if command_handler.is_command(user_input):
                should_continue = command_handler.handle(user_input)
                if not should_continue:
                    break
                continue

            try:
                # Reset loop count for new query
                session.agent_engine.loop_count = 0

                # Track current panel context and agent
                current_panel_context = None
                current_updater = None
                current_agent = session.agent_definition.name

                try:
                    ### Stream and handle events
                    async for event in session.send_message_stream(user_input):
                        if isinstance(event, str):
                            # Text chunk - open panel if needed and update
                            if current_panel_context is None:
                                current_panel_context = display.stream_assistant_response(
                                    current_agent
                                )
                                current_updater = current_panel_context.__enter__()
                            current_updater(event)

                        elif isinstance(event, ToolCallEvent):
                            # Close agent panel before showing tools
                            if current_panel_context:
                                current_panel_context.__exit__(None, None, None)
                                current_panel_context = None
                                current_updater = None

                            # Display tool calls
                            for tool_call in event.tool_calls:
                                tool_name = tool_call.function.name
                                try:
                                    tool_args = json.loads(tool_call.function.arguments)
                                except Exception:
                                    tool_args = {}
                                display.print_tool_execution(tool_name, tool_args)

                        elif isinstance(event, ToolResultEvent):
                            # Display tool result
                            if event.result and event.result.strip():
                                display.print_tool_result(event.tool_name, event.result)

                        elif isinstance(event, AgentChange):
                            # Close current panel
                            if current_panel_context:
                                current_panel_context.__exit__(None, None, None)
                                current_panel_context = None
                                current_updater = None

                            # Show handoff message
                            display.print_system_message(
                                f"\n[Transferring to {event.new_agent_name}: {event.reason}]\n"
                            )

                            # Update current agent for next panel
                            current_agent = event.new_agent_name

                finally:
                    # Ensure panel is closed
                    if current_panel_context:
                        current_panel_context.__exit__(None, None, None)

            except Exception as e:
                display.print_error("Failed to process message", e)
                logger.exception("Message processing failed")

        except KeyboardInterrupt:
            display.print_system_message("\n(Ctrl+C pressed - type /exit to quit)")
            continue
        except EOFError:
            display.print_goodbye()
            break
        except Exception as e:
            display.print_error("Unexpected error", e)
            logger.exception("Unexpected error in chat loop")


@app.command()
def chat(
    agent: Optional[str] = typer.Option(
        None,
        "--agent",
        "-a",
        help="Name of the agent to use (from registry or default from settings)",
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="LLM model to use (e.g., gemini-2.5-flash, gpt-4)"
    ),
    tools: Optional[str] = typer.Option(
        None,
        "--tools",
        "-t",
        help="Comma-separated list of tools to enable (e.g., calculator.add,core.echo)",
    ),
    temperature: float = typer.Option(0.7, "--temperature", help="Model temperature (0.0 to 2.0)"),
    max_tokens: Optional[int] = typer.Option(
        None, "--max-tokens", help="Maximum tokens for response"
    ),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key for the LLM provider"),
):
    """
    Start an interactive chat session with the Exodus agent.

    Examples:

        exodus-cli chat

        exodus-cli chat --agent chat_agent

        exodus-cli chat --model gpt-4 --temperature 0.5

        exodus-cli chat --tools calculator.add,calculator.multiply
    """
    try:
        # Parse tools if provided
        tools_list = None
        if tools:
            tools_list = [t.strip() for t in tools.split(",")]

        async def run_chat_loop_with_cleanup():
            # START LOADING BEFORE IMPORTS
            display.console.print("\n[bold cyan]Starting EXODUS ...[/bold cyan]")

            phrase = random.choice(LOADING_PHRASES)
            with display.show_spinner(f"{phrase}"):
                # Heavy imports inside the function to allow showing the message first
                from exodus.cli.session import ChatSession

                session = ChatSession(
                    agent_name=agent,
                    model=model,
                    tools=tools_list,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=api_key,
                )

            display.console.print(f'[dim]"{phrase}"[/dim]')
            display.console.print("[green][0] Ready[/green]\n")

            try:
                await run_chat_loop(session)
            finally:
                await session.close()
                logger.info("Cleaning up session...")
                await asyncio.sleep(0.5)  ### Double time to ensure the session is cleaned up
                logger.info("Session cleaned up")

        asyncio.run(run_chat_loop_with_cleanup())

    except ValueError as e:
        display.print_error(str(e))
        raise typer.Exit(code=1)
    except Exception as e:
        display.print_error("Failed to initialize CLI", e)
        logger.exception("CLI initialization failed")
        raise typer.Exit(code=1)


@app.command()
def auto(
    objective: str = typer.Argument(..., help="Objective to accomplish"),
    agent: Optional[str] = typer.Option(
        None, "--agent", "-a", help="Starting agent (default: triage_agent)"
    ),
    context: Optional[str] = typer.Option(None, "--context", "-c", help="Additional context"),
    session_id: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID"),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume from checkpoint"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """
    Run agent in automated mode with planning and execution.

    Examples:

        exodus-cli auto "Capture flags on 10.10.10.5"

        exodus-cli auto "Pwn HTB machine" --agent recon_agent

        exodus-cli auto "Continue" --resume --session htb_20260105
    """
    from datetime import datetime

    from exodus.core.models.events import (
        AgentChange,
        AutomatedEvent,
        ToolCallEvent,
        ToolResultEvent,
    )
    from exodus.engines.automated import create_automated_engine

    ### Generate session ID if not provided
    if not session_id:
        obj_clean = "".join(c if c.isalnum() else "_" for c in objective[:20])
        session_id = f"{obj_clean}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    async def run():
        display.console.print("\n[bold cyan]EXODUS - Automated Mode[/bold cyan]")
        display.console.print(f"[dim]Objective: {objective}[/dim]")
        if context:
            display.console.print(f"[dim]Context: {context}[/dim]")
        display.console.print(f"[dim]Session: {session_id}[/dim]\n")

        try:
            ### Create engine
            engine = create_automated_engine(
                agent_name=agent or "triage_agent", session_id=session_id
            )

            ### Track state
            task_start_times = {}
            current_agent = agent or "triage_agent"
            current_panel_context = None
            current_updater = None

            async for event in engine.run_automated(
                objective=objective, context=context or "", session_id=session_id, resume=resume
            ):
                if isinstance(event, str):
                    ### Text chunk - show agent thoughts in a panel like interactive mode
                    if current_panel_context is None:
                        current_panel_context = display.stream_assistant_response(current_agent)
                        current_updater = current_panel_context.__enter__()
                    current_updater(event)

                elif isinstance(event, AutomatedEvent):
                    event_type = event.event_type
                    data = event.data

                    if event_type == "plan_created":
                        ### Use new plan table display
                        display.print_plan_table(data)

                    elif event_type == "plan_loaded":
                        ### Display loaded plan with progress info
                        display.console.print(
                            f"\n[bold green]Checkpoint Loaded[/bold green] - "
                            f"Progress: {data['completed']}/{data['total_tasks']} completed, "
                            f"{data['failed']} failed, {data['pending']} pending"
                        )
                        display.print_plan_table(data)

                    elif event_type == "plan_updated":
                        ### Display updated plan
                        display.console.print(
                            f"\n[bold magenta]Plan Updated:[/bold magenta] {data.get('reason', 'Replanning triggered')}"
                        )
                        display.print_plan_table(data)

                    elif event_type == "task_started":
                        ### Close any open agent panel before starting new task
                        if current_panel_context:
                            current_panel_context.__exit__(None, None, None)
                            current_panel_context = None
                            current_updater = None

                        task_id = data["task_id"]
                        task_start_times[task_id] = datetime.now()

                        ### Use new task header display
                        display.print_task_header(
                            task_id, data["description"], data.get("attempt", 1)
                        )

                    elif event_type == "task_completed":
                        ### Close any open agent panel
                        if current_panel_context:
                            current_panel_context.__exit__(None, None, None)
                            current_panel_context = None
                            current_updater = None

                        task_id = data["task_id"]
                        duration = (
                            (datetime.now() - task_start_times.get(task_id)).total_seconds()
                            if task_id in task_start_times
                            else 0
                        )

                        ### Use new task completion display
                        display.print_task_completion(
                            task_id, data["result"], duration, data.get("score", 0.0)
                        )

                        if data.get("observations") and verbose:
                            display.console.print(
                                f"  [dim]Findings: {', '.join(data['observations'])}[/dim]\n"
                            )

                    elif event_type == "task_failed":
                        ### Close any open agent panel
                        if current_panel_context:
                            current_panel_context.__exit__(None, None, None)
                            current_panel_context = None
                            current_updater = None

                        display.console.print(f"\n[red]✗ Task Failed:[/red] {data['task_id']}")
                        display.console.print(f"  {data.get('result', 'Failed')}\n")

                    elif event_type == "reflection":
                        if verbose:
                            display.console.print(
                                f"\n[magenta]Reflection:[/magenta] {data['action']} (confidence: {data['confidence']:.1f})"
                            )
                            display.console.print(f"  {data['reasoning']}\n")

                    elif event_type == "plan_completed":
                        progress = data["progress"]
                        display.console.print("\n[bold green]Mission Complete[/bold green]")
                        display.console.print(
                            f"  Completed: {progress['completed']}/{progress['total_tasks']}"
                        )
                        display.console.print(f"  Failed: {progress['failed']}")
                        display.console.print(f"  Score: {progress['avg_score'] * 10:.1f}/10\n")

                    elif event_type == "escalation_requested":
                        display.console.print(
                            "\n[yellow]⚠ Agent requests human assistance[/yellow]"
                        )
                        display.console.print(f"  {data.get('reason', '')}\n")

                    elif event_type == "max_iterations_reached":
                        display.console.print("\n[yellow]⚠ Max iterations reached[/yellow]")
                        display.console.print(
                            f"  Task {data['task_id']} incomplete after {data['iterations']} iterations"
                        )
                        display.console.print(
                            f"  Resume with: exodus-cli auto --resume --session {session_id}\n"
                        )

                elif isinstance(event, AgentChange):
                    ### Close current panel before agent switch
                    if current_panel_context:
                        current_panel_context.__exit__(None, None, None)
                        current_panel_context = None
                        current_updater = None

                    ### Show handoff using print_step
                    display.print_step(
                        f"Switched to {event.new_agent_name}: {event.reason}",
                        icon="->",
                        style="bold cyan",
                    )
                    current_agent = event.new_agent_name

                elif isinstance(event, ToolCallEvent):
                    ### Close agent panel before showing tools
                    if current_panel_context:
                        current_panel_context.__exit__(None, None, None)
                        current_panel_context = None
                        current_updater = None

                    ### Use the same tool display as interactive mode
                    for tool_call in event.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            tool_args = json.loads(tool_call.function.arguments)
                        except Exception:
                            tool_args = {}

                        ### Handle handoffs specially with print_step
                        if tool_name.startswith("transfer_to_"):
                            target_agent = tool_name.replace("transfer_to_", "")
                            display.print_step(
                                f"Transferring to {target_agent}...",
                                icon="->",
                                style="cyan",
                            )
                        else:
                            ### Regular tools use the standard display
                            display.print_tool_execution(tool_name, tool_args)

                elif isinstance(event, ToolResultEvent):
                    ### Show tool results using standard display
                    if event.result and event.result.strip():
                        display.print_tool_result(event.tool_name, event.result)

            ### Ensure panel is closed at end
            if current_panel_context:
                current_panel_context.__exit__(None, None, None)

        except KeyboardInterrupt:
            display.console.print("\n")
            display.console.print("\n[yellow]Interrupted by user[/yellow]")
            display.console.print(f"Resume with: exodus-cli auto --resume --session {session_id}")
        except Exception as e:
            display.console.print(f"\n[red]Error: {e}[/red]")
            logger.exception("Automated execution failed")

    asyncio.run(run())


@app.command()
def version():
    """Show the Exodus CLI version."""
    display.console.print("Exodus CLI v0.1.0", style="bold cyan")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

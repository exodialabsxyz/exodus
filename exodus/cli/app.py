"""
Main Exodus CLI application using Typer.
"""
import asyncio
from typing import Optional, List
import typer

from exodus.cli.session import ChatSession
from exodus.cli.commands import CommandHandler
from exodus.cli import display
from exodus.logs import logger


app = typer.Typer(
    name="exodus-cli",
    help="Exodus Agentic CLI - Interactive AI assistant with tools",
    add_completion=False
)


async def run_chat_loop(session: ChatSession):
    """
    Run the main chat loop.
    
    Args:
        session: Active chat session
    """
    command_handler = CommandHandler(session)
    
    # Get tools info
    tools_info = session.get_tools_info()
    
    # Display banner with agent name, model, and tools count
    display.print_banner(
        agent_name=session.agent_definition.name,
        model=session.model,
        tools_count=len(tools_info)
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
            
            # Send message to agent
            display.print_user_message(user_input)
            display.print_thinking()
            
            try:
                # Reset loop count for new query
                session.agent_engine.loop_count = 0
                
                # Get memory length before sending message to track new messages
                memory_before = len(session.get_memory())
                
                # Send message and get response
                await session.send_message(user_input)
                
                # Get all messages added during this interaction
                memory = session.get_memory()
                new_messages = memory[memory_before:]
                
                # Display tool calls and results from the interaction
                # Skip the user message (already displayed) and only show tool interactions
                for msg in new_messages:
                    if msg.role == "user":
                        # Skip user messages, already displayed above
                        continue
                    elif msg.role == "assistant" and hasattr(msg, 'tool_calls') and msg.tool_calls:
                        # This assistant message contains tool calls
                        import json
                        for tool_call in msg.tool_calls:
                            tool_name = tool_call.function.name
                            tool_args = json.loads(tool_call.function.arguments)
                            display.print_tool_execution(tool_name, tool_args)
                    elif msg.role == "tool":
                        # This is a tool result - only display if it has content
                        if msg.content and msg.content.strip():
                            tool_name = msg.name if hasattr(msg, 'name') and msg.name else "unknown"
                            display.print_tool_result(tool_name, msg.content)
                
                # Display final assistant response
                if memory:
                    last_message = memory[-1]
                    if last_message.role == "assistant":
                        display.print_assistant_message(
                            last_message.content or "",
                            agent_name=session.agent_definition.name
                        )
                    else:
                        display.print_system_message("Agent completed task")
                
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
        "--agent", "-a",
        help="Name of the agent to use (from registry or default from settings)"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model", "-m",
        help="LLM model to use (e.g., gemini-2.5-flash, gpt-4)"
    ),
    tools: Optional[str] = typer.Option(
        None,
        "--tools", "-t",
        help="Comma-separated list of tools to enable (e.g., calculator.add,core.echo)"
    ),
    temperature: float = typer.Option(
        0.7,
        "--temperature",
        help="Model temperature (0.0 to 2.0)"
    ),
    max_tokens: Optional[int] = typer.Option(
        None,
        "--max-tokens",
        help="Maximum tokens for response"
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        help="API key for the LLM provider"
    ),
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
        
        # Initialize session
        session = ChatSession(
            agent_name=agent,
            model=model,
            tools=tools_list,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key
        )
        
        # Run the chat loop
        asyncio.run(run_chat_loop(session))
        
    except ValueError as e:
        display.print_error(str(e))
        raise typer.Exit(code=1)
    except Exception as e:
        display.print_error("Failed to initialize CLI", e)
        logger.exception("CLI initialization failed")
        raise typer.Exit(code=1)


@app.command()
def version():
    """Show the Exodus CLI version."""
    display.console.print("Exodus CLI v0.1.0", style="bold cyan")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

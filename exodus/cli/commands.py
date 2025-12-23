"""
Command handlers for slash commands in the Exodus CLI.
"""

from typing import Optional

from exodus.cli import display
from exodus.cli.session import ChatSession
from exodus.core.registries import agent_registry
from exodus.logs import logger


class CommandHandler:
    """Handles slash commands in the CLI."""

    def __init__(self, session: ChatSession):
        """
        Initialize the command handler.

        Args:
            session: The active chat session
        """
        self.session = session
        self.commands = {
            "/exit": self.exit_command,
            "/quit": self.exit_command,
            "/help": self.help_command,
            "/clear": self.clear_command,
            "/save": self.save_command,
            "/load": self.load_command,
            "/tools": self.tools_command,
            "/agents": self.agents_command,
            "/switch": self.switch_command,
        }

    def is_command(self, user_input: str) -> bool:
        """
        Check if the input is a slash command.

        Args:
            user_input: User's input

        Returns:
            True if it's a command, False otherwise
        """
        return user_input.strip().startswith("/")

    def handle(self, user_input: str) -> bool:
        """
        Handle a slash command.

        Args:
            user_input: User's input starting with /

        Returns:
            True to continue the loop, False to exit
        """
        parts = user_input.strip().split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else None

        handler = self.commands.get(command)
        if handler:
            return handler(args)
        else:
            display.print_error(f"Unknown command: {command}")
            display.print_system_message("Type /help to see available commands")
            return True

    def exit_command(self, args: Optional[str]) -> bool:
        """Handle /exit or /quit command."""
        display.print_goodbye()
        return False

    def help_command(self, args: Optional[str]) -> bool:
        """Handle /help command."""
        display.print_help()
        return True

    def clear_command(self, args: Optional[str]) -> bool:
        """Handle /clear command."""
        try:
            self.session.clear_history()
            display.print_conversation_cleared()
        except Exception as e:
            display.print_error("Failed to clear conversation", e)
        return True

    def save_command(self, args: Optional[str]) -> bool:
        """Handle /save [filename] command."""
        filename = args if args else None
        try:
            filepath = self.session.save_conversation(filename)
            display.print_conversation_saved(filepath)
        except Exception as e:
            display.print_error("Failed to save conversation", e)
            logger.exception("Save failed")
        return True

    def load_command(self, args: Optional[str]) -> bool:
        """Handle /load [filename] command."""
        filename = args if args else None
        try:
            message_count = self.session.load_conversation(filename)
            display.print_conversation_loaded(filename or "session.json", message_count)
        except FileNotFoundError:
            display.print_error(f"File not found: {filename or 'session.json'}")
        except Exception as e:
            display.print_error("Failed to load conversation", e)
            logger.exception("Load failed")
        return True

    def tools_command(self, args: Optional[str]) -> bool:
        """Handle /tools command to show available tools."""
        tools_info = self.session.get_tools_info()
        display.print_tools_list(tools_info)
        return True

    def agents_command(self, args: Optional[str]) -> bool:
        """Handle /agents command to list available agents."""
        try:
            # Get all registered agents
            agents_info = []
            for agent_name, agent_def in agent_registry._agents.items():
                agents_info.append(
                    {
                        "name": agent_name,
                        "description": agent_def.description,
                        "is_current": agent_name == self.session.agent_definition.name,
                    }
                )

            if not agents_info:
                display.print_system_message(
                    "No agents loaded. Make sure agent TOML files exist in exodus/agents/single/"
                )
            else:
                display.print_agents_list(
                    agents_info, current_agent=self.session.agent_definition.name
                )
        except Exception as e:
            display.print_error("Failed to list agents", e)
            logger.exception("Agents list failed")
        return True

    def switch_command(self, args: Optional[str]) -> bool:
        """Handle /switch <agent_name> command to change the current agent."""
        if not args:
            display.print_error("Usage: /switch <agent_name>")
            display.print_system_message("Use /agents to see available agents")
            return True

        agent_name = args.strip()
        try:
            # Try to switch to the new agent
            success = self.session.switch_agent(agent_name)
            if success:
                display.print_agent_switched(agent_name)
                # Update the banner to show new agent
                display.print_system_message(f"Now chatting with: {agent_name}")
            else:
                display.print_error(f"Agent '{agent_name}' not found")
                display.print_system_message("Use /agents to see available agents")
        except Exception as e:
            display.print_error(f"Failed to switch to agent '{agent_name}'", e)
            logger.exception("Agent switch failed")
        return True

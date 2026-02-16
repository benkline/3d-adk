"""Interactive command-line interface for 3D-ADK."""

import asyncio
import logging
from typing import Optional

from src.tools.coordinator_tools import (
    create_project_session,
    get_project_status,
    list_project_sessions,
    advance_phase,
    backtrack_phase,
)

logger = logging.getLogger(__name__)


def format_status(status_dict: dict) -> str:
    """Format project status for display."""
    if status_dict.get("status") == "error":
        return f"[ERROR] {status_dict.get('message', 'Unknown error')}"

    lines = [
        f"Project: {status_dict.get('project_name', 'N/A')}",
        f"Phase: {status_dict.get('current_phase', 'N/A').upper()}",
        f"Design Approved: {'✓' if status_dict.get('design_approved') else '✗'}",
        f"Model Exported: {'✓' if status_dict.get('model_exported') else '✗'}",
        f"Print Started: {'✓' if status_dict.get('print_started') else '✗'}",
    ]

    if status_dict.get("created_at"):
        lines.append(f"Created: {status_dict.get('created_at')}")
    if status_dict.get("updated_at"):
        lines.append(f"Updated: {status_dict.get('updated_at')}")

    return "\n".join(lines)


def format_sessions_list(sessions: list) -> str:
    """Format sessions list for display."""
    if not sessions:
        return "No active projects."

    lines = ["Active Projects:"]
    for i, session in enumerate(sessions, 1):
        lines.append(
            f"  {i}. {session.get('project_name')} "
            f"({session.get('current_phase', 'unknown').upper()}) "
            f"[{session.get('session_id', 'N/A')[:8]}...]"
        )
    return "\n".join(lines)


def format_error(msg: str) -> str:
    """Format error message for display."""
    return f"[ERROR] {msg}"


class CLI:
    """Interactive command-line interface for 3D-ADK."""

    def __init__(self, session_id: Optional[str] = None):
        """Initialize CLI.

        Args:
            session_id: Optional session ID to load on startup
        """
        self.session_id = session_id
        self.logger = logging.getLogger(__name__)

        self.commands = {
            "help": self.cmd_help,
            "new": self.cmd_new,
            "resume": self.cmd_resume,
            "status": self.cmd_status,
            "next": self.cmd_next,
            "back": self.cmd_back,
            "exit": self.cmd_exit,
            "quit": self.cmd_exit,
        }

    def run(self):
        """Run the interactive CLI loop."""
        print("\n" + "=" * 60)
        print("3D ADK - Interactive Command Interface")
        print("=" * 60)
        print("Type 'help' for available commands\n")

        if self.session_id:
            print(f"Loaded session: {self.session_id}\n")

        while True:
            try:
                # Get user input
                prompt = "3d-adk> " if not self.session_id else f"3d-adk [{self.session_id[:8]}...]> "
                user_input = input(prompt).strip()

                if not user_input:
                    continue

                # Parse command and arguments
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""

                # Execute command
                if command in self.commands:
                    asyncio.run(self.commands[command](args))
                else:
                    print(format_error(f"Unknown command '{command}'. Type 'help' for available commands."))

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                print(format_error(f"Unexpected error: {e}"))

    async def cmd_help(self, args: str = ""):
        """Show available commands."""
        help_text = """
Available Commands:

  help              Show this help message
  new <name>        Create a new project (e.g., 'new my_phone_stand')
  resume            List all projects and resume one
  status            Show current project status
  next              Advance to the next phase
  back              Go back to the previous phase
  exit / quit       Exit the CLI

Examples:
  new custom_stand      - Create a new project
  resume               - Choose a project from the list
  status               - Show current phase and progress
  next                 - Move to next phase (if approved)
  back                 - Return to previous phase
"""
        print(help_text)

    async def cmd_new(self, args: str = ""):
        """Create a new project."""
        if not args:
            print(format_error("Project name required. Usage: new <project_name>"))
            return

        project_name = args.strip()
        self.logger.info(f"Creating new project: {project_name}")

        result = await create_project_session(project_name)

        if result.get("status") == "error":
            print(format_error(result.get("message", "Failed to create project")))
        else:
            self.session_id = result.get("session_id")
            print(f"\n✓ Created project: {project_name}")
            print(f"  Session ID: {self.session_id}")
            print(f"  Current Phase: {result.get('current_phase', 'design').upper()}\n")
            self.logger.info(f"Successfully created project with session {self.session_id}")

    async def cmd_resume(self, args: str = ""):
        """Resume a project from the list."""
        self.logger.info("Listing available projects")

        result = await list_project_sessions()

        if result.get("status") == "error":
            print(format_error(result.get("message", "Failed to list projects")))
            return

        sessions = result.get("sessions", [])
        if not sessions:
            print("No projects available. Create a new one with 'new <project_name>'")
            return

        print("\n" + format_sessions_list(sessions) + "\n")

        try:
            choice = input("Enter project number to resume (or press Ctrl+C to cancel): ").strip()
            index = int(choice) - 1

            if 0 <= index < len(sessions):
                self.session_id = sessions[index].get("session_id")
                print(f"\n✓ Resumed project: {sessions[index].get('project_name')}\n")
                self.logger.info(f"Resumed session {self.session_id}")
            else:
                print(format_error("Invalid selection"))
        except (ValueError, KeyboardInterrupt, EOFError):
            pass

    async def cmd_status(self, args: str = ""):
        """Show current project status."""
        if not self.session_id:
            print(format_error("No project loaded. Create a new project or use 'resume' to continue one."))
            return

        self.logger.info(f"Getting status for session {self.session_id}")

        result = await get_project_status(self.session_id)

        print("\n" + format_status(result) + "\n")

        if result.get("status") == "error":
            self.logger.warning(f"Failed to get status: {result.get('message')}")

    async def cmd_next(self, args: str = ""):
        """Advance to the next phase."""
        if not self.session_id:
            print(format_error("No project loaded. Create a new project or use 'resume' to continue one."))
            return

        self.logger.info(f"Advancing phase for session {self.session_id}")

        result = await advance_phase(self.session_id)

        if result.get("status") == "error":
            print(format_error(result.get("message", "Failed to advance phase")))
        else:
            print(f"\n✓ Advanced to phase: {result.get('current_phase', 'unknown').upper()}\n")
            self.logger.info(f"Successfully advanced to {result.get('current_phase')}")

    async def cmd_back(self, args: str = ""):
        """Go back to the previous phase."""
        if not self.session_id:
            print(format_error("No project loaded. Create a new project or use 'resume' to continue one."))
            return

        self.logger.info(f"Backtracking phase for session {self.session_id}")

        result = await backtrack_phase(self.session_id)

        if result.get("status") == "error":
            print(format_error(result.get("message", "Failed to backtrack phase")))
        else:
            print(f"\n✓ Backtracked to phase: {result.get('current_phase', 'unknown').upper()}\n")
            self.logger.info(f"Successfully backtracked to {result.get('current_phase')}")

    async def cmd_exit(self, args: str = ""):
        """Exit the CLI."""
        print("\nGoodbye!")
        exit(0)

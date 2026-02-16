"""Tests for CLI interface."""

import pytest
import os
from unittest.mock import patch, AsyncMock

# Set environment before importing modules that use config
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
os.environ.setdefault("LLM_MODEL", "claude-opus-4-6")
os.environ.setdefault("OCTOPRINT_HOST", "localhost")
os.environ.setdefault("OCTOPRINT_PORT", "5000")
os.environ.setdefault("OCTOPRINT_API_KEY", "test_key")
os.environ.setdefault("LOG_LEVEL", "DEBUG")


def test_cli_instantiates_without_error():
    """Test that CLI can be instantiated."""
    from src.cli import CLI

    cli = CLI()
    assert cli is not None
    assert cli.session_id is None


def test_cli_instantiates_with_session_id():
    """Test that CLI can be instantiated with a session ID."""
    from src.cli import CLI

    session_id = "test-session-123"
    cli = CLI(session_id=session_id)
    assert cli.session_id == session_id


def test_format_status_with_ok_result():
    """Test formatting of successful status result."""
    from src.cli import format_status

    result = {
        "status": "ok",
        "project_name": "test_project",
        "current_phase": "design",
        "design_approved": True,
        "model_exported": False,
        "print_started": False,
        "created_at": "2025-02-15T10:00:00",
        "updated_at": "2025-02-15T10:05:00",
    }

    output = format_status(result)

    assert "test_project" in output
    assert "DESIGN" in output
    assert "✓" in output  # design_approved should have checkmark
    assert "✗" in output  # model_exported should have X


def test_format_status_with_error_result():
    """Test formatting of error status result."""
    from src.cli import format_status

    result = {
        "status": "error",
        "message": "Session not found",
    }

    output = format_status(result)

    assert "[ERROR]" in output
    assert "Session not found" in output


def test_format_sessions_list_empty():
    """Test formatting of empty sessions list."""
    from src.cli import format_sessions_list

    output = format_sessions_list([])

    assert "No active projects" in output


def test_format_sessions_list_with_sessions():
    """Test formatting of sessions list with sessions."""
    from src.cli import format_sessions_list

    sessions = [
        {
            "session_id": "abc123def456",
            "project_name": "phone_stand",
            "current_phase": "design",
            "created_at": "2025-02-15T10:00:00",
        },
        {
            "session_id": "xyz789abc123",
            "project_name": "desk_organizer",
            "current_phase": "modeling",
            "created_at": "2025-02-15T09:00:00",
        },
    ]

    output = format_sessions_list(sessions)

    assert "Active Projects" in output
    assert "phone_stand" in output
    assert "DESIGN" in output
    assert "desk_organizer" in output
    assert "MODELING" in output


def test_format_error():
    """Test formatting of error messages."""
    from src.cli import format_error

    msg = "Something went wrong"
    output = format_error(msg)

    assert "[ERROR]" in output
    assert "Something went wrong" in output


def test_cli_has_expected_commands():
    """Test that CLI has all expected command methods."""
    from src.cli import CLI

    cli = CLI()

    expected_commands = ["help", "new", "resume", "status", "next", "back", "exit", "quit"]

    for cmd in expected_commands:
        assert cmd in cli.commands


@pytest.mark.asyncio
async def test_cli_cmd_help():
    """Test help command output."""
    from src.cli import CLI

    cli = CLI()

    # help command should not raise
    await cli.cmd_help("")


@pytest.mark.asyncio
async def test_cli_new_project_with_empty_name():
    """Test new command with empty project name."""
    from src.cli import CLI
    from unittest.mock import patch
    from io import StringIO

    cli = CLI()

    with patch("builtins.print") as mock_print:
        await cli.cmd_new("")

        # Should have printed an error
        assert mock_print.called
        output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "Project name required" in str(output)


@pytest.mark.asyncio
async def test_cli_new_project_success():
    """Test new command with valid project name."""
    from src.cli import CLI
    from unittest.mock import patch

    cli = CLI()

    # Mock the coordinator tool
    mock_result = {
        "status": "ok",
        "session_id": "session-123",
        "project_name": "test_project",
        "current_phase": "design",
    }

    with patch("src.cli.create_project_session", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_result

        with patch("builtins.print"):
            await cli.cmd_new("test_project")

            # Verify the session_id was set
            assert cli.session_id == "session-123"
            # Verify the tool was called
            mock_create.assert_called_once_with("test_project")


@pytest.mark.asyncio
async def test_cli_new_project_error():
    """Test new command when project creation fails."""
    from src.cli import CLI
    from unittest.mock import patch

    cli = CLI()

    # Mock the coordinator tool to return error
    mock_result = {
        "status": "error",
        "message": "Project already exists",
    }

    with patch("src.cli.create_project_session", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_result

        with patch("builtins.print") as mock_print:
            await cli.cmd_new("existing_project")

            # Session ID should not be set
            assert cli.session_id is None
            # Should have printed an error
            assert mock_print.called


@pytest.mark.asyncio
async def test_cli_status_without_session():
    """Test status command when no session is loaded."""
    from src.cli import CLI
    from unittest.mock import patch

    cli = CLI()

    with patch("builtins.print") as mock_print:
        await cli.cmd_status("")

        # Should have printed an error about no project loaded
        assert mock_print.called


@pytest.mark.asyncio
async def test_cli_status_with_session():
    """Test status command with a loaded session."""
    from src.cli import CLI
    from unittest.mock import patch

    cli = CLI(session_id="test-session-123")

    # Mock the coordinator tool
    mock_result = {
        "status": "ok",
        "project_name": "test_project",
        "current_phase": "design",
        "design_approved": False,
        "model_exported": False,
        "print_started": False,
    }

    with patch("src.cli.get_project_status", new_callable=AsyncMock) as mock_status:
        mock_status.return_value = mock_result

        with patch("builtins.print"):
            await cli.cmd_status("")

            # Verify the tool was called with the session ID
            mock_status.assert_called_once_with("test-session-123")


@pytest.mark.asyncio
async def test_cli_next_without_session():
    """Test next command when no session is loaded."""
    from src.cli import CLI
    from unittest.mock import patch

    cli = CLI()

    with patch("builtins.print") as mock_print:
        await cli.cmd_next("")

        # Should have printed an error
        assert mock_print.called


@pytest.mark.asyncio
async def test_cli_next_with_session():
    """Test next command with a loaded session."""
    from src.cli import CLI
    from unittest.mock import patch

    cli = CLI(session_id="test-session-123")

    # Mock the coordinator tool
    mock_result = {
        "status": "ok",
        "current_phase": "modeling",
    }

    with patch("src.cli.advance_phase", new_callable=AsyncMock) as mock_advance:
        mock_advance.return_value = mock_result

        with patch("builtins.print"):
            await cli.cmd_next("")

            # Verify the tool was called with the session ID
            mock_advance.assert_called_once_with("test-session-123")


@pytest.mark.asyncio
async def test_cli_back_with_session():
    """Test back command with a loaded session."""
    from src.cli import CLI
    from unittest.mock import patch

    cli = CLI(session_id="test-session-123")

    # Mock the coordinator tool
    mock_result = {
        "status": "ok",
        "current_phase": "design",
    }

    with patch("src.cli.backtrack_phase", new_callable=AsyncMock) as mock_backtrack:
        mock_backtrack.return_value = mock_result

        with patch("builtins.print"):
            await cli.cmd_back("")

            # Verify the tool was called with the session ID
            mock_backtrack.assert_called_once_with("test-session-123")

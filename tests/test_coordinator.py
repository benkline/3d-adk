"""Tests for Coordinator Agent core framework (TICKET-023)."""

import os
import pytest


# Sync tests for agent structure
def test_coordinator_agent_initializes():
    """Test that coordinator agent initializes without errors."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.agents.coordinator import coordinator_agent

    assert coordinator_agent is not None


def test_coordinator_agent_has_correct_name():
    """Test that coordinator agent has the correct name."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.agents.coordinator import coordinator_agent

    assert coordinator_agent.name == "coordinator_agent"


def test_coordinator_agent_has_five_tools():
    """Test that coordinator agent has exactly five tools."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.agents.coordinator import coordinator_agent

    assert len(coordinator_agent.tools) == 5


def test_coordinator_agent_uses_config_model():
    """Test that coordinator agent uses the model from config."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.agents.coordinator import coordinator_agent
    from src.config import LLM_MODEL

    assert coordinator_agent.model == LLM_MODEL


def test_coordinator_agent_has_three_sub_agents():
    """Test that coordinator agent has three sub-agents."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.agents.coordinator import coordinator_agent

    assert len(coordinator_agent.sub_agents) == 3
    agent_names = {agent.name for agent in coordinator_agent.sub_agents}
    assert "design_phase_agent" in agent_names
    assert "modeling_phase_agent" in agent_names
    assert "monitor_phase_agent" in agent_names


# Async tests for tool function behavior
@pytest.mark.asyncio
async def test_create_project_session_returns_session_id():
    """Test that create_project_session tool returns properly formatted response."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.tools.coordinator_tools import create_project_session

    result = await create_project_session(project_name="test_project")

    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] == "ok"
    assert "session_id" in result
    assert "project_name" in result
    assert result["project_name"] == "test_project"
    assert "current_phase" in result
    assert result["current_phase"] == "design"


@pytest.mark.asyncio
async def test_create_project_session_validates_empty_name():
    """Test that create_project_session validates empty project name."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.tools.coordinator_tools import create_project_session

    result = await create_project_session(project_name="")

    assert isinstance(result, dict)
    assert result["status"] == "error"
    assert "message" in result


@pytest.mark.asyncio
async def test_get_project_status_with_valid_session():
    """Test that get_project_status returns session state correctly."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.tools.coordinator_tools import create_project_session, get_project_status

    # Create a project first
    create_result = await create_project_session(project_name="test_project_status")
    session_id = create_result["session_id"]

    # Get status
    status_result = await get_project_status(session_id=session_id)

    assert isinstance(status_result, dict)
    assert status_result["status"] == "ok"
    assert "current_phase" in status_result
    assert status_result["current_phase"] == "design"
    assert "design_approved" in status_result
    assert "model_exported" in status_result
    assert "print_started" in status_result


@pytest.mark.asyncio
async def test_get_project_status_with_invalid_session():
    """Test that get_project_status returns error for invalid session."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.tools.coordinator_tools import get_project_status

    result = await get_project_status(session_id="invalid_session_id")

    assert isinstance(result, dict)
    assert result["status"] == "error"
    assert "message" in result


@pytest.mark.asyncio
async def test_list_project_sessions_returns_list():
    """Test that list_project_sessions returns a list of projects."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.tools.coordinator_tools import create_project_session, list_project_sessions

    # Create a project first
    await create_project_session(project_name="test_project_list")

    # List projects
    result = await list_project_sessions()

    assert isinstance(result, dict)
    assert result["status"] == "ok"
    assert "sessions" in result
    assert isinstance(result["sessions"], list)
    # Check that at least our test project is in the list
    project_names = [s.get("project_name") for s in result["sessions"]]
    assert "test_project_list" in project_names


@pytest.mark.asyncio
async def test_advance_phase_from_design_to_modeling_without_approval():
    """Test that advance_phase blocks transition without design_approved."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.tools.coordinator_tools import create_project_session, advance_phase

    # Create a project
    create_result = await create_project_session(project_name="test_advance_no_approval")
    session_id = create_result["session_id"]

    # Try to advance without approval
    result = await advance_phase(session_id=session_id)

    assert isinstance(result, dict)
    assert result["status"] == "error"
    assert "message" in result


@pytest.mark.asyncio
async def test_backtrack_phase_from_design_returns_error():
    """Test that backtrack_phase returns error when already at design."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.tools.coordinator_tools import create_project_session, backtrack_phase

    # Create a project (starts at design)
    create_result = await create_project_session(project_name="test_backtrack_design")
    session_id = create_result["session_id"]

    # Try to backtrack from design
    result = await backtrack_phase(session_id=session_id)

    assert isinstance(result, dict)
    assert result["status"] == "error"
    assert "message" in result


@pytest.mark.asyncio
async def test_advance_phase_with_approval():
    """Test that advance_phase works with design_approved set."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.session import create_project, get_project, update_project_phase
    from src.services.sessions import ProjectSessionService
    import json

    # Create a project and manually set design_approved
    session = await create_project(project_name="test_advance_with_approval")

    # Persist design_approved to disk
    _service = ProjectSessionService()
    session_file = _service._get_session_file_path("3d-adk", "default", session.id)
    session_data = {
        "id": session.id,
        "app_name": session.app_name,
        "user_id": session.user_id,
        "state": {**session.state, "design_approved": True},
        "events": session.events,
        "last_update_time": session.last_update_time,
    }
    _service._save_session_to_file(session_file, session_data)

    # Now try advancing
    from src.tools.coordinator_tools import advance_phase
    result = await advance_phase(session_id=session.id)

    # Should succeed and move to modeling
    assert result["status"] == "ok"
    assert result["previous_phase"] == "design"
    assert result["current_phase"] == "modeling"

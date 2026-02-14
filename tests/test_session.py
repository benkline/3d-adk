"""Tests for session management and configuration."""

import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path


def test_config_has_sessions_dir():
    """Test that SESSIONS_DIR is defined in config."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    import importlib
    import src.config

    importlib.reload(src.config)

    assert hasattr(src.config, "SESSIONS_DIR")
    assert src.config.SESSIONS_DIR is not None


@pytest.mark.asyncio
async def test_create_session():
    """Test that a session can be created with correct state."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.services.sessions import ProjectSessionService

    service = ProjectSessionService()
    session = await service.create_session(
        app_name="test_app",
        user_id="test_user",
        state={"project_name": "test_project"},
    )

    assert session.id is not None
    assert session.app_name == "test_app"
    assert session.user_id == "test_user"
    assert session.state["project_name"] == "test_project"
    assert session.state["current_phase"] == "design"
    assert session.state["design_approved"] is False
    assert session.state["model_exported"] is False
    assert session.state["print_started"] is False


@pytest.mark.asyncio
async def test_get_session():
    """Test that a session can be retrieved by ID after creation."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.services.sessions import ProjectSessionService

    service = ProjectSessionService()
    created = await service.create_session(
        app_name="test_app2",
        user_id="test_user2",
        state={"project_name": "test_project2"},
    )

    retrieved = await service.get_session(
        app_name="test_app2",
        user_id="test_user2",
        session_id=created.id,
    )

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.state["project_name"] == "test_project2"


@pytest.mark.asyncio
async def test_session_persistence():
    """Test that session is written to disk as JSON file."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.services.sessions import ProjectSessionService
    from src.config import SESSIONS_DIR

    service = ProjectSessionService()
    session = await service.create_session(
        app_name="test_app3",
        user_id="test_user3",
        state={"project_name": "test_project3"},
    )

    # Check that file was created
    session_file = (
        Path(SESSIONS_DIR) / "test_app3" / "test_user3" / f"{session.id}.json"
    )
    assert session_file.exists()

    # Verify file contents
    with open(session_file, "r") as f:
        data = json.load(f)

    assert data["id"] == session.id
    assert data["app_name"] == "test_app3"
    assert data["user_id"] == "test_user3"
    assert data["state"]["project_name"] == "test_project3"


@pytest.mark.asyncio
async def test_session_recovery():
    """Test that a new service instance can load an existing session."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.services.sessions import ProjectSessionService

    # Create session with first instance
    service1 = ProjectSessionService()
    session1 = await service1.create_session(
        app_name="test_app4",
        user_id="test_user4",
        state={"project_name": "test_project4"},
    )

    # Load with new instance
    service2 = ProjectSessionService()
    session2 = await service2.get_session(
        app_name="test_app4",
        user_id="test_user4",
        session_id=session1.id,
    )

    assert session2 is not None
    assert session2.id == session1.id
    assert session2.state == session1.state


@pytest.mark.asyncio
async def test_project_dirs_created():
    """Test that project directories are created with all expected subdirs."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.services.sessions import ProjectSessionService
    from src.config import PROJECTS_DIR

    service = ProjectSessionService()
    await service.create_session(
        app_name="test_app5",
        user_id="test_user5",
        state={"project_name": "test_project5"},
    )

    # Check directory structure
    project_root = Path(PROJECTS_DIR) / "test_project5"
    assert (project_root / "design" / "sketches").exists()
    assert (project_root / "design" / "images").exists()
    assert (project_root / "model" / "exports").exists()
    assert (project_root / "print").exists()


@pytest.mark.asyncio
async def test_list_sessions():
    """Test that created sessions appear in listings."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.services.sessions import ProjectSessionService

    service = ProjectSessionService()

    # Create multiple sessions
    session1 = await service.create_session(
        app_name="test_app6",
        user_id="test_user6",
        state={"project_name": "project_a"},
    )
    session2 = await service.create_session(
        app_name="test_app6",
        user_id="test_user6",
        state={"project_name": "project_b"},
    )

    # List sessions
    response = await service.list_sessions(
        app_name="test_app6",
        user_id="test_user6",
    )

    session_ids = {s.id for s in response.sessions}
    assert session1.id in session_ids
    assert session2.id in session_ids


@pytest.mark.asyncio
async def test_update_phase():
    """Test that phase transitions update persisted state."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.session import create_project, get_project, update_project_phase

    # Create project
    session = await create_project("test_project_phase")

    # Verify initial phase
    assert session.state["current_phase"] == "design"

    # Update phase
    updated = await update_project_phase(session.id, "modeling")
    assert updated.state["current_phase"] == "modeling"

    # Verify persistence
    recovered = await get_project(session.id)
    assert recovered.state["current_phase"] == "modeling"


@pytest.mark.asyncio
async def test_convenience_create_project():
    """Test convenience function create_project."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.session import create_project

    session = await create_project("convenience_test_project")

    assert session.id is not None
    assert session.state["project_name"] == "convenience_test_project"
    assert session.state["current_phase"] == "design"


@pytest.mark.asyncio
async def test_convenience_list_projects():
    """Test convenience function list_projects."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    from src.session import create_project, list_projects

    # Create a few projects
    p1 = await create_project("list_test_1")
    p2 = await create_project("list_test_2")

    # List all
    projects = await list_projects()

    project_ids = {p.id for p in projects}
    assert p1.id in project_ids
    assert p2.id in project_ids

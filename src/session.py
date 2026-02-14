"""High-level project session management convenience layer."""

from datetime import datetime
from typing import Optional
from google.adk.sessions import Session

from src.services.sessions import ProjectSessionService

# Single-user local mode constants
APP_NAME = "3d-adk"
USER_ID = "default"

# Global service instance
_service = ProjectSessionService()


async def create_project(project_name: str) -> Session:
    """Create a new project session.

    Args:
        project_name: Name of the project

    Returns:
        Session object with initialized project state
    """
    return await _service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={"project_name": project_name},
    )


async def get_project(session_id: str) -> Optional[Session]:
    """Retrieve a project session by ID.

    Args:
        session_id: Session ID to retrieve

    Returns:
        Session object if found, None otherwise
    """
    return await _service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )


async def update_project_phase(session_id: str, phase: str) -> Session:
    """Update the current phase of a project.

    Args:
        session_id: Session ID to update
        phase: New phase ('design', 'modeling', 'monitor')

    Returns:
        Updated Session object

    Raises:
        ValueError: If session not found
    """
    session = await get_project(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # Update phase in state
    session.state["current_phase"] = phase
    session.state["updated_at"] = datetime.utcnow().isoformat()

    # Re-persist to disk
    session_file = _service._get_session_file_path(APP_NAME, USER_ID, session_id)
    import json
    session_data = {
        "id": session.id,
        "app_name": session.app_name,
        "user_id": session.user_id,
        "state": session.state,
        "events": session.events,
        "last_update_time": session.last_update_time,
    }
    _service._save_session_to_file(session_file, session_data)

    return session


async def list_projects() -> list[Session]:
    """List all projects for the current user.

    Returns:
        List of Session objects
    """
    response = await _service.list_sessions(app_name=APP_NAME, user_id=USER_ID)
    return response.sessions


async def recover_session(session_id: str) -> Optional[Session]:
    """Alias for get_project - recover a session.

    Args:
        session_id: Session ID to recover

    Returns:
        Session object if found, None otherwise
    """
    return await get_project(session_id)

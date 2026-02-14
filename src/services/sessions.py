"""Sessions service implementation with JSON filesystem backend."""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from google.adk.sessions import BaseSessionService, Session
from google.adk.sessions.session import Event
from google.adk.sessions.base_session_service import ListSessionsResponse

from src.config import SESSIONS_DIR, PROJECTS_DIR


class ProjectSessionService(BaseSessionService):
    """Extends ADK BaseSessionService with JSON filesystem storage backend."""

    def __init__(self):
        """Initialize session service with filesystem paths."""
        self.sessions_dir = Path(SESSIONS_DIR)
        self.projects_dir = Path(PROJECTS_DIR)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_file_path(self, app_name: str, user_id: str, session_id: str) -> Path:
        """Get the filesystem path for a session file."""
        session_path = self.sessions_dir / app_name / user_id / f"{session_id}.json"
        return session_path

    def _load_session_from_file(self, path: Path) -> Optional[dict]:
        """Load session data from JSON file."""
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise RuntimeError(f"Failed to load session from {path}: {e}")

    def _save_session_to_file(self, path: Path, data: dict) -> None:
        """Save session data to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except IOError as e:
            raise RuntimeError(f"Failed to save session to {path}: {e}")

    def _default_project_state(self, project_name: str) -> dict:
        """Create default project state schema."""
        now = datetime.utcnow().isoformat()
        return {
            "project_name": project_name,
            "current_phase": "design",
            "created_at": now,
            "updated_at": now,
            "design_approved": False,
            "model_exported": False,
            "print_started": False,
        }

    def _create_project_directories(self, project_name: str) -> None:
        """Create project directory tree under PROJECTS_DIR."""
        project_root = self.projects_dir / project_name
        subdirs = [
            project_root / "design" / "sketches",
            project_root / "design" / "images",
            project_root / "model" / "exports",
            project_root / "print",
        ]
        for subdir in subdirs:
            subdir.mkdir(parents=True, exist_ok=True)

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """Create a new session with project state.

        Args:
            app_name: Application name identifier
            user_id: User identifier
            state: Initial project state (will be merged with defaults)
            session_id: Session ID (generated if not provided)

        Returns:
            Session object with state persisted to disk
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        # Extract project_name from state or use a default
        project_name = state.get("project_name") if state else None
        if not project_name:
            raise ValueError("project_name must be provided in state")

        # Create default state and merge with provided state
        default_state = self._default_project_state(project_name)
        if state:
            default_state.update(state)
        final_state = default_state

        # Update timestamp
        final_state["updated_at"] = datetime.utcnow().isoformat()

        # Create project directories
        self._create_project_directories(project_name)

        # Create Session object (matches ADK's Session model)
        # last_update_time should be a float (unix timestamp)
        last_update_timestamp = datetime.utcnow().timestamp()
        session = Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=final_state,
            events=[],
            last_update_time=last_update_timestamp,
        )

        # Persist to disk
        session_file = self._get_session_file_path(app_name, user_id, session_id)
        session_data = {
            "id": session.id,
            "app_name": session.app_name,
            "user_id": session.user_id,
            "state": session.state,
            "events": session.events,
            "last_update_time": session.last_update_time,
        }
        self._save_session_to_file(session_file, session_data)

        return session

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config=None,
    ) -> Optional[Session]:
        """Retrieve a session by ID.

        Args:
            app_name: Application name identifier
            user_id: User identifier
            session_id: Session ID to retrieve
            config: Optional configuration (unused)

        Returns:
            Session object if found, None otherwise
        """
        session_file = self._get_session_file_path(app_name, user_id, session_id)
        data = self._load_session_from_file(session_file)

        if data is None:
            return None

        return Session(
            id=data["id"],
            app_name=data["app_name"],
            user_id=data["user_id"],
            state=data.get("state", {}),
            events=data.get("events", []),
            last_update_time=data.get("last_update_time"),
        )

    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        """List all sessions for an app or specific user.

        Args:
            app_name: Application name identifier
            user_id: Optional user ID filter

        Returns:
            ListSessionsResponse with matching sessions
        """
        sessions = []
        app_dir = self.sessions_dir / app_name

        if not app_dir.exists():
            return ListSessionsResponse(sessions=[])

        # Scan directory structure: {app_name}/{user_id}/{session_id}.json
        for user_path in app_dir.iterdir():
            if not user_path.is_dir():
                continue

            # Filter by user_id if specified
            current_user_id = user_path.name
            if user_id and current_user_id != user_id:
                continue

            # Load all session files for this user
            for session_file in user_path.glob("*.json"):
                try:
                    data = self._load_session_from_file(session_file)
                    if data:
                        session = Session(
                            id=data["id"],
                            app_name=data["app_name"],
                            user_id=data["user_id"],
                            state=data.get("state", {}),
                            events=data.get("events", []),
                            last_update_time=data.get("last_update_time"),
                        )
                        sessions.append(session)
                except RuntimeError as e:
                    # Skip sessions that fail to load
                    continue

        return ListSessionsResponse(sessions=sessions)

    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        """Delete a session.

        Args:
            app_name: Application name identifier
            user_id: User identifier
            session_id: Session ID to delete
        """
        session_file = self._get_session_file_path(app_name, user_id, session_id)
        if session_file.exists():
            session_file.unlink()

    async def append_event(self, session: Session, event: Event) -> Event:
        """Append an event to a session and persist to disk.

        Args:
            session: Session to append event to
            event: Event to append

        Returns:
            The appended event
        """
        # Update session events in memory
        session.events.append(event)
        session.last_update_time = datetime.utcnow().timestamp()

        # Re-persist to disk
        session_file = self._get_session_file_path(
            session.app_name, session.user_id, session.id
        )
        session_data = {
            "id": session.id,
            "app_name": session.app_name,
            "user_id": session.user_id,
            "state": session.state,
            "events": session.events,
            "last_update_time": session.last_update_time,
        }
        self._save_session_to_file(session_file, session_data)

        return event

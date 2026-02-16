"""Coordinator phase and session management tools."""

import logging
from typing import Optional

from src.session import (
    create_project,
    get_project,
    update_project_phase,
    update_project_state,
    list_projects,
)

logger = logging.getLogger(__name__)


async def create_project_session(project_name: str) -> dict:
    """Create a new project session.

    Args:
        project_name: Name of the project (non-empty)

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - session_id: Session ID (if status is "ok")
        - project_name: Project name (if status is "ok")
        - current_phase: Current phase, always "design" for new projects
        - message: Error message (if status is "error")

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    # Validate input
    if not project_name or not isinstance(project_name, str) or project_name.strip() == "":
        logger.warning("create_project_session called with empty project_name")
        return {
            "status": "error",
            "message": "project_name is required and must be a non-empty string"
        }

    try:
        # Create project session
        session = await create_project(project_name)
        logger.info(f"Created new project session: {session.id} for project '{project_name}'")

        return {
            "status": "ok",
            "session_id": session.id,
            "project_name": session.state.get("project_name"),
            "current_phase": session.state.get("current_phase", "design"),
        }
    except Exception as e:
        logger.error(f"Error creating project session: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create project session: {str(e)}"
        }


async def get_project_status(session_id: str) -> dict:
    """Get current project status and phase.

    Args:
        session_id: Session ID to retrieve

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - current_phase: Current phase ("design", "modeling", "monitor")
        - design_approved: Whether design is approved
        - model_exported: Whether model is exported
        - print_started: Whether print has started
        - project_name: Name of the project
        - created_at: Creation timestamp
        - updated_at: Last update timestamp
        - message: Error message (if status is "error")

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    # Validate input
    if not session_id or not isinstance(session_id, str):
        logger.warning("get_project_status called with invalid session_id")
        return {
            "status": "error",
            "message": "session_id is required and must be a non-empty string"
        }

    try:
        session = await get_project(session_id)

        if not session:
            logger.warning(f"Session not found: {session_id}")
            return {
                "status": "error",
                "message": f"Session {session_id} not found"
            }

        return {
            "status": "ok",
            "current_phase": session.state.get("current_phase", "design"),
            "design_approved": session.state.get("design_approved", False),
            "model_exported": session.state.get("model_exported", False),
            "print_started": session.state.get("print_started", False),
            "project_name": session.state.get("project_name"),
            "created_at": session.state.get("created_at"),
            "updated_at": session.state.get("updated_at"),
        }
    except Exception as e:
        logger.error(f"Error getting project status: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get project status: {str(e)}"
        }


async def list_project_sessions() -> dict:
    """List all available project sessions.

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - sessions: List of session dicts with (id, project_name, current_phase, created_at)
        - message: Error message (if status is "error")

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    try:
        sessions = await list_projects()

        # Transform sessions to dicts for cleaner output
        session_list = []
        for session in sessions:
            session_list.append({
                "session_id": session.id,
                "project_name": session.state.get("project_name"),
                "current_phase": session.state.get("current_phase", "design"),
                "created_at": session.state.get("created_at"),
            })

        logger.info(f"Listed {len(session_list)} project sessions")
        return {
            "status": "ok",
            "sessions": session_list,
        }
    except Exception as e:
        logger.error(f"Error listing project sessions: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to list project sessions: {str(e)}"
        }


async def advance_phase(session_id: str) -> dict:
    """Advance to the next phase with validation.

    Transition rules:
    - design → modeling: requires design_approved = True
    - modeling → monitor: requires model_exported = True
    - monitor → no next phase (error)

    Args:
        session_id: Session ID to advance

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - previous_phase: Previous phase
        - current_phase: New current phase
        - message: Info or error message

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    # Validate input
    if not session_id or not isinstance(session_id, str):
        logger.warning("advance_phase called with invalid session_id")
        return {
            "status": "error",
            "message": "session_id is required and must be a non-empty string"
        }

    try:
        session = await get_project(session_id)

        if not session:
            logger.warning(f"Session not found: {session_id}")
            return {
                "status": "error",
                "message": f"Session {session_id} not found"
            }

        current_phase = session.state.get("current_phase", "design")

        # Phase transition validation
        if current_phase == "design":
            # design → modeling requires design_approved
            if not session.state.get("design_approved", False):
                logger.warning(f"Cannot advance to modeling: design not approved for {session_id}")
                return {
                    "status": "error",
                    "message": "Cannot advance to modeling phase: design must be approved first"
                }
            next_phase = "modeling"

        elif current_phase == "modeling":
            # modeling → monitor requires model_exported
            if not session.state.get("model_exported", False):
                logger.warning(f"Cannot advance to monitor: model not exported for {session_id}")
                return {
                    "status": "error",
                    "message": "Cannot advance to monitor phase: model must be exported first"
                }
            next_phase = "monitor"

        elif current_phase == "monitor":
            # Already at last phase
            logger.warning(f"Cannot advance beyond monitor phase for {session_id}")
            return {
                "status": "error",
                "message": "Already at the final phase (monitor)"
            }

        else:
            # Unknown phase
            logger.warning(f"Unknown phase: {current_phase} for {session_id}")
            return {
                "status": "error",
                "message": f"Unknown current phase: {current_phase}"
            }

        # Update session to new phase
        await update_project_phase(session_id, next_phase)
        logger.info(f"Advanced project {session_id} from {current_phase} to {next_phase}")

        return {
            "status": "ok",
            "previous_phase": current_phase,
            "current_phase": next_phase,
            "message": f"Successfully advanced from {current_phase} to {next_phase}"
        }

    except Exception as e:
        logger.error(f"Error advancing phase: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to advance phase: {str(e)}"
        }


async def backtrack_phase(session_id: str) -> dict:
    """Backtrack to the previous phase with validation.

    Backtrack rules:
    - modeling → design: allowed anytime
    - monitor → modeling: only if print_started = False
    - design → error (no previous phase)

    Args:
        session_id: Session ID to backtrack

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - previous_phase: Phase before backtrack
        - current_phase: New current phase
        - message: Info or error message

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    # Validate input
    if not session_id or not isinstance(session_id, str):
        logger.warning("backtrack_phase called with invalid session_id")
        return {
            "status": "error",
            "message": "session_id is required and must be a non-empty string"
        }

    try:
        session = await get_project(session_id)

        if not session:
            logger.warning(f"Session not found: {session_id}")
            return {
                "status": "error",
                "message": f"Session {session_id} not found"
            }

        current_phase = session.state.get("current_phase", "design")

        # Phase backtrack validation
        if current_phase == "design":
            # Cannot go back from design phase
            logger.warning(f"Cannot backtrack from design phase for {session_id}")
            return {
                "status": "error",
                "message": "Cannot backtrack from the initial design phase"
            }

        elif current_phase == "modeling":
            # modeling → design allowed anytime
            previous_phase = current_phase
            next_phase = "design"

        elif current_phase == "monitor":
            # monitor → modeling only if print_started = False
            if session.state.get("print_started", False):
                logger.warning(f"Cannot backtrack from monitor: print already started for {session_id}")
                return {
                    "status": "error",
                    "message": "Cannot backtrack from monitor phase: print has already started"
                }
            previous_phase = current_phase
            next_phase = "modeling"

        else:
            # Unknown phase
            logger.warning(f"Unknown phase: {current_phase} for {session_id}")
            return {
                "status": "error",
                "message": f"Unknown current phase: {current_phase}"
            }

        # Update session to previous phase
        await update_project_phase(session_id, next_phase)
        logger.info(f"Backtracked project {session_id} from {current_phase} to {next_phase}")

        return {
            "status": "ok",
            "previous_phase": current_phase,
            "current_phase": next_phase,
            "message": f"Successfully backtracked from {current_phase} to {next_phase}"
        }

    except Exception as e:
        logger.error(f"Error backtracking phase: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to backtrack phase: {str(e)}"
        }


async def approve_design(session_id: str) -> dict:
    """Approve the design and mark as ready for modeling phase.

    Sets design_approved = True in the session state, enabling the design → modeling transition.

    Args:
        session_id: Session ID to update

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - session_id: Session ID
        - design_approved: Whether design is now approved (True on success)
        - message: Info or error message

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    # Validate input
    if not session_id or not isinstance(session_id, str):
        logger.warning("approve_design called with invalid session_id")
        return {
            "status": "error",
            "message": "session_id is required and must be a non-empty string"
        }

    try:
        session = await get_project(session_id)

        if not session:
            logger.warning(f"Session not found: {session_id}")
            return {
                "status": "error",
                "message": f"Session {session_id} not found"
            }

        # Update session state
        await update_project_state(session_id, {"design_approved": True})
        logger.info(f"Design approved for project {session_id}")

        return {
            "status": "ok",
            "session_id": session_id,
            "design_approved": True,
            "message": "Design successfully approved"
        }

    except Exception as e:
        logger.error(f"Error approving design: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to approve design: {str(e)}"
        }


async def mark_model_exported(session_id: str) -> dict:
    """Mark the model as exported and ready for printing phase.

    Sets model_exported = True in the session state, enabling the modeling → monitor transition.

    Args:
        session_id: Session ID to update

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - session_id: Session ID
        - model_exported: Whether model is now exported (True on success)
        - message: Info or error message

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    # Validate input
    if not session_id or not isinstance(session_id, str):
        logger.warning("mark_model_exported called with invalid session_id")
        return {
            "status": "error",
            "message": "session_id is required and must be a non-empty string"
        }

    try:
        session = await get_project(session_id)

        if not session:
            logger.warning(f"Session not found: {session_id}")
            return {
                "status": "error",
                "message": f"Session {session_id} not found"
            }

        # Update session state
        await update_project_state(session_id, {"model_exported": True})
        logger.info(f"Model marked as exported for project {session_id}")

        return {
            "status": "ok",
            "session_id": session_id,
            "model_exported": True,
            "message": "Model successfully marked as exported"
        }

    except Exception as e:
        logger.error(f"Error marking model exported: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to mark model as exported: {str(e)}"
        }


async def mark_print_started(session_id: str) -> dict:
    """Mark the print as started to prevent backtracking from monitor phase.

    Sets print_started = True in the session state, preventing backtrack from monitor → modeling.

    Args:
        session_id: Session ID to update

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - session_id: Session ID
        - print_started: Whether print is now marked as started (True on success)
        - message: Info or error message

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    # Validate input
    if not session_id or not isinstance(session_id, str):
        logger.warning("mark_print_started called with invalid session_id")
        return {
            "status": "error",
            "message": "session_id is required and must be a non-empty string"
        }

    try:
        session = await get_project(session_id)

        if not session:
            logger.warning(f"Session not found: {session_id}")
            return {
                "status": "error",
                "message": f"Session {session_id} not found"
            }

        # Update session state
        await update_project_state(session_id, {"print_started": True})
        logger.info(f"Print marked as started for project {session_id}")

        return {
            "status": "ok",
            "session_id": session_id,
            "print_started": True,
            "message": "Print successfully marked as started"
        }

    except Exception as e:
        logger.error(f"Error marking print started: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to mark print as started: {str(e)}"
        }

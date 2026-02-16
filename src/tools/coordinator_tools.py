"""Coordinator phase and session management tools."""

import logging
import os
import json
import shutil
import zipfile
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.config import PROJECTS_DIR
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


async def get_project_structure(project_name: str) -> dict:
    """Get the file structure and organization of a project.

    Walks the project directory and returns metadata about all files and directories.

    Args:
        project_name: Name of the project (non-empty)

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - project_name: Project name (if status is "ok")
        - root_path: Root directory path (if status is "ok")
        - files: List of {path, size_bytes} dicts (if status is "ok")
        - total_files: Total number of files (if status is "ok")
        - total_size_bytes: Total size of all files (if status is "ok")
        - message: Error message (if status is "error")

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    if not project_name or not isinstance(project_name, str) or project_name.strip() == "":
        logger.warning("get_project_structure called with empty project_name")
        return {
            "status": "error",
            "message": "project_name is required and must be a non-empty string"
        }

    try:
        project_path = Path(PROJECTS_DIR) / project_name

        if not project_path.exists():
            logger.warning(f"Project directory not found: {project_path}")
            return {
                "status": "error",
                "message": f"Project directory not found: {project_path}"
            }

        files = []
        total_size = 0

        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(project_path))
                size = file_path.stat().st_size
                files.append({
                    "path": rel_path,
                    "size_bytes": size
                })
                total_size += size

        logger.info(f"Retrieved project structure for '{project_name}': {len(files)} files, {total_size} bytes")

        return {
            "status": "ok",
            "project_name": project_name,
            "root_path": str(project_path),
            "files": files,
            "total_files": len(files),
            "total_size_bytes": total_size
        }

    except Exception as e:
        logger.error(f"Error getting project structure: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get project structure: {str(e)}"
        }


async def organize_project_files(project_name: str) -> dict:
    """Ensure project files are properly organized with correct directory structure.

    Creates all required subdirectories for a project if they don't exist.

    Args:
        project_name: Name of the project (non-empty)

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - project_name: Project name (if status is "ok")
        - directories_created: List of created directories (if status is "ok")
        - existing_directories: List of existing directories (if status is "ok")
        - message: Info or error message

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    if not project_name or not isinstance(project_name, str) or project_name.strip() == "":
        logger.warning("organize_project_files called with empty project_name")
        return {
            "status": "error",
            "message": "project_name is required and must be a non-empty string"
        }

    try:
        project_path = Path(PROJECTS_DIR) / project_name
        required_dirs = [
            project_path / "design",
            project_path / "design" / "sketches",
            project_path / "design" / "images",
            project_path / "model",
            project_path / "model" / "exports",
            project_path / "print",
        ]

        created_dirs = []
        existing_dirs = []

        for dir_path in required_dirs:
            if dir_path.exists():
                existing_dirs.append(str(dir_path))
            else:
                dir_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(str(dir_path))

        logger.info(f"Organized project '{project_name}': created {len(created_dirs)}, existing {len(existing_dirs)}")

        return {
            "status": "ok",
            "project_name": project_name,
            "directories_created": created_dirs,
            "existing_directories": existing_dirs,
            "message": f"Project organized: {len(created_dirs)} directories created, {len(existing_dirs)} already existed"
        }

    except Exception as e:
        logger.error(f"Error organizing project files: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to organize project files: {str(e)}"
        }


async def create_design_version(project_name: str, version_label: str = "") -> dict:
    """Create a snapshot of current design files as a version.

    Copies all design files (except versions/) to design/versions/{version_id}/ and updates version history.

    Args:
        project_name: Name of the project (non-empty)
        version_label: Optional human-readable label for this version

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - project_name: Project name (if status is "ok")
        - version_id: UUID of the created version (if status is "ok")
        - label: Version label (if status is "ok")
        - timestamp: ISO-8601 timestamp (if status is "ok")
        - files_versioned: Number of files copied (if status is "ok")
        - message: Info or error message

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    if not project_name or not isinstance(project_name, str) or project_name.strip() == "":
        logger.warning("create_design_version called with empty project_name")
        return {
            "status": "error",
            "message": "project_name is required and must be a non-empty string"
        }

    try:
        project_path = Path(PROJECTS_DIR) / project_name
        design_path = project_path / "design"
        versions_dir = design_path / "versions"

        # Ensure versions directory exists
        versions_dir.mkdir(parents=True, exist_ok=True)

        # Generate version ID
        version_id = str(uuid.uuid4())
        version_path = versions_dir / version_id
        version_path.mkdir(parents=True, exist_ok=True)

        # Copy design files (exclude versions/ directory)
        files_copied = 0
        for item in design_path.iterdir():
            if item.name == "versions":
                continue
            if item.is_dir():
                shutil.copytree(item, version_path / item.name, dirs_exist_ok=True)
                files_copied += sum(1 for _ in (version_path / item.name).rglob("*") if _.is_file())
            elif item.is_file():
                shutil.copy2(item, version_path / item.name)
                files_copied += 1

        # Update version history
        history_path = versions_dir / "version_history.json"
        history = []
        if history_path.exists():
            with open(history_path, "r") as f:
                history = json.load(f)

        timestamp = datetime.utcnow().isoformat()
        history.append({
            "version_id": version_id,
            "label": version_label or f"Version {len(history) + 1}",
            "timestamp": timestamp,
            "files_count": files_copied
        })

        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)

        logger.info(f"Created design version for '{project_name}': {version_id} with {files_copied} files")

        return {
            "status": "ok",
            "project_name": project_name,
            "version_id": version_id,
            "label": version_label or f"Version {len(history)}",
            "timestamp": timestamp,
            "files_versioned": files_copied,
            "message": f"Design version created with {files_copied} files"
        }

    except Exception as e:
        logger.error(f"Error creating design version: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create design version: {str(e)}"
        }


async def list_design_versions(project_name: str) -> dict:
    """List all saved design versions for a project.

    Reads the design version history and returns metadata for each version.

    Args:
        project_name: Name of the project (non-empty)

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - project_name: Project name (if status is "ok")
        - versions: List of {version_id, label, timestamp, files_count} dicts (if status is "ok")
        - total_versions: Total number of versions (if status is "ok")
        - message: Info or error message

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    if not project_name or not isinstance(project_name, str) or project_name.strip() == "":
        logger.warning("list_design_versions called with empty project_name")
        return {
            "status": "error",
            "message": "project_name is required and must be a non-empty string"
        }

    try:
        project_path = Path(PROJECTS_DIR) / project_name
        history_path = project_path / "design" / "versions" / "version_history.json"

        versions = []
        if history_path.exists():
            with open(history_path, "r") as f:
                versions = json.load(f)

        logger.info(f"Retrieved {len(versions)} design versions for '{project_name}'")

        return {
            "status": "ok",
            "project_name": project_name,
            "versions": versions,
            "total_versions": len(versions),
            "message": f"Retrieved {len(versions)} design versions"
        }

    except Exception as e:
        logger.error(f"Error listing design versions: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to list design versions: {str(e)}"
        }


async def backup_project(project_name: str) -> dict:
    """Create a full backup of project files.

    Creates a timestamped backup of design/, model/, and print/ directories.

    Args:
        project_name: Name of the project (non-empty)

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - project_name: Project name (if status is "ok")
        - backup_id: UUID of the backup (if status is "ok")
        - timestamp: ISO-8601 timestamp (if status is "ok")
        - files_backed_up: Number of files in backup (if status is "ok")
        - backup_path: Path to backup directory (if status is "ok")
        - message: Info or error message

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    if not project_name or not isinstance(project_name, str) or project_name.strip() == "":
        logger.warning("backup_project called with empty project_name")
        return {
            "status": "error",
            "message": "project_name is required and must be a non-empty string"
        }

    try:
        project_path = Path(PROJECTS_DIR) / project_name
        backups_dir = project_path / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup ID
        backup_id = str(uuid.uuid4())
        backup_path = backups_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)

        # Copy design, model, print directories (exclude backups and exports)
        files_backed_up = 0
        for source_dir in ["design", "model", "print"]:
            source_path = project_path / source_dir
            if source_path.exists():
                # Copy excluding certain subdirectories
                for item in source_path.iterdir():
                    if item.name in ["backups", "exports"]:
                        continue
                    if item.is_dir():
                        shutil.copytree(item, backup_path / source_dir / item.name, dirs_exist_ok=True)
                        files_backed_up += sum(1 for _ in (backup_path / source_dir / item.name).rglob("*") if _.is_file())
                    elif item.is_file():
                        (backup_path / source_dir).mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, backup_path / source_dir / item.name)
                        files_backed_up += 1

        # Update backup manifest
        manifest_path = backups_dir / "backup_manifest.json"
        manifest = []
        if manifest_path.exists():
            with open(manifest_path, "r") as f:
                manifest = json.load(f)

        timestamp = datetime.utcnow().isoformat()
        manifest.append({
            "backup_id": backup_id,
            "timestamp": timestamp,
            "files_count": files_backed_up
        })

        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Created backup for '{project_name}': {backup_id} with {files_backed_up} files")

        return {
            "status": "ok",
            "project_name": project_name,
            "backup_id": backup_id,
            "timestamp": timestamp,
            "files_backed_up": files_backed_up,
            "backup_path": str(backup_path),
            "message": f"Backup created with {files_backed_up} files"
        }

    except Exception as e:
        logger.error(f"Error backing up project: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to backup project: {str(e)}"
        }


async def export_project(project_name: str, export_format: str = "zip") -> dict:
    """Export project as an archive file.

    Creates a zip archive of the project (excluding backups and exports directories).

    Args:
        project_name: Name of the project (non-empty)
        export_format: Export format (currently only "zip" supported)

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - project_name: Project name (if status is "ok")
        - export_path: Path to exported file (if status is "ok")
        - file_count: Number of files in export (if status is "ok")
        - size_bytes: Size of exported file (if status is "ok")
        - message: Info or error message

    Error Handling:
        Returns error dict with message rather than raising exceptions
    """
    if not project_name or not isinstance(project_name, str) or project_name.strip() == "":
        logger.warning("export_project called with empty project_name")
        return {
            "status": "error",
            "message": "project_name is required and must be a non-empty string"
        }

    if export_format != "zip":
        logger.warning(f"Unsupported export format: {export_format}")
        return {
            "status": "error",
            "message": f"Unsupported export format: {export_format}. Only 'zip' is currently supported."
        }

    try:
        project_path = Path(PROJECTS_DIR) / project_name
        exports_dir = project_path / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        export_filename = f"{project_name}_{timestamp}.zip"
        export_path = exports_dir / export_filename

        # Create zip file
        file_count = 0
        with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for source_dir in ["design", "model", "print"]:
                source_path = project_path / source_dir
                if source_path.exists():
                    for item in source_path.rglob("*"):
                        if item.is_file():
                            # Skip backups and exports directories
                            if "backups" not in item.parts and "exports" not in item.parts:
                                arcname = item.relative_to(project_path)
                                zipf.write(item, arcname)
                                file_count += 1

        size_bytes = export_path.stat().st_size
        logger.info(f"Exported project '{project_name}' to {export_filename}: {file_count} files, {size_bytes} bytes")

        return {
            "status": "ok",
            "project_name": project_name,
            "export_path": str(export_path),
            "file_count": file_count,
            "size_bytes": size_bytes,
            "message": f"Project exported: {file_count} files, {size_bytes} bytes"
        }

    except Exception as e:
        logger.error(f"Error exporting project: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to export project: {str(e)}"
        }

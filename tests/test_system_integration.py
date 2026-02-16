"""System integration tests for complete end-to-end workflow (TICKET-027).

Tests the full design→modeling→monitor pipeline with the coordinator agent.
Verifies data flows correctly between phases, error handling is robust,
and state persists across service restarts.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

import src.config
import src.tools.coordinator_tools
from src.services.sessions import ProjectSessionService


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def tmp_projects_dir(tmp_path):
    """Create a temporary projects directory for testing."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    return str(projects_dir)


@pytest.fixture
def mock_projects_dir(tmp_projects_dir, monkeypatch):
    """Patch PROJECTS_DIR to use temporary directory."""
    monkeypatch.setattr(src.config, "PROJECTS_DIR", tmp_projects_dir)
    monkeypatch.setattr(src.tools.coordinator_tools, "PROJECTS_DIR", tmp_projects_dir)
    return tmp_projects_dir


@pytest.fixture
def mock_sessions_dir(tmp_path, monkeypatch):
    """Patch SESSIONS_DIR to use temporary directory."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    monkeypatch.setattr(src.config, "SESSIONS_DIR", str(sessions_dir))
    return str(sessions_dir)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _write_design_file(projects_dir: str, project_name: str, filename: str, content: str):
    """Helper to write a file to the design directory."""
    design_dir = Path(projects_dir) / project_name / "design"
    design_dir.mkdir(parents=True, exist_ok=True)
    (design_dir / filename).write_text(content)


# ============================================================================
# TEST CLASSES
# ============================================================================

class TestFullSystemPipeline:
    """Tests the complete coordinator workflow end-to-end."""

    @pytest.mark.asyncio
    async def test_complete_workflow_design_to_monitor(self, mock_projects_dir, mock_sessions_dir):
        """Test complete workflow: design → modeling → monitor."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            get_project_status,
            approve_design,
            advance_phase,
            mark_model_exported,
        )

        # Create session in design phase
        result = await create_project_session(project_name="sys_int_complete_workflow")
        assert result["status"] == "ok"
        session_id = result["session_id"]
        assert result["current_phase"] == "design"

        # Approve design and advance to modeling
        result = await approve_design(session_id=session_id)
        assert result["status"] == "ok"
        assert result["design_approved"] is True

        result = await advance_phase(session_id=session_id)
        assert result["status"] == "ok"
        assert result["current_phase"] == "modeling"

        # Mark model exported and advance to monitor
        result = await mark_model_exported(session_id=session_id)
        assert result["status"] == "ok"
        assert result["model_exported"] is True

        result = await advance_phase(session_id=session_id)
        assert result["status"] == "ok"
        assert result["current_phase"] == "monitor"

        # Verify final state
        result = await get_project_status(session_id=session_id)
        assert result["current_phase"] == "monitor"
        assert result["design_approved"] is True
        assert result["model_exported"] is True

    @pytest.mark.asyncio
    async def test_state_flags_gate_phase_transitions(self, mock_projects_dir, mock_sessions_dir):
        """Test that state flags gate phase transitions."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            advance_phase,
            mark_model_exported,
        )

        # Create session
        result = await create_project_session(project_name="sys_int_gates")
        session_id = result["session_id"]

        # Try to advance without design approval
        result = await advance_phase(session_id=session_id)
        assert result["status"] == "error"
        assert "design" in result["message"].lower()

        # Manually set design_approved to test modeling gate
        service = ProjectSessionService()
        session = await service.get_session(
            app_name="3d-adk",
            user_id="default",
            session_id=session_id,
        )
        session.state["design_approved"] = True
        session_file = service._get_session_file_path("3d-adk", "default", session_id)
        session_data = {
            "id": session.id,
            "app_name": "3d-adk",
            "user_id": "default",
            "state": session.state,
            "events": session.events,
            "last_update_time": session.last_update_time,
        }
        service._save_session_to_file(session_file, session_data)

        # Now advance to modeling should work
        result = await advance_phase(session_id=session_id)
        assert result["status"] == "ok"
        assert result["current_phase"] == "modeling"

        # Try to advance without model export
        result = await advance_phase(session_id=session_id)
        assert result["status"] == "error"
        assert "model" in result["message"].lower()

        # Mark model exported
        result = await mark_model_exported(session_id=session_id)
        assert result["status"] == "ok"

        # Now advance to monitor should work
        result = await advance_phase(session_id=session_id)
        assert result["status"] == "ok"
        assert result["current_phase"] == "monitor"

    @pytest.mark.asyncio
    async def test_full_pipeline_phase_sequence(self, mock_projects_dir, mock_sessions_dir):
        """Test phases transition in exact sequence."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            get_project_status,
            approve_design,
            advance_phase,
            mark_model_exported,
        )

        result = await create_project_session(project_name="sys_int_sequence")
        session_id = result["session_id"]

        # Verify initial phase
        result = await get_project_status(session_id=session_id)
        assert result["current_phase"] == "design"

        # Design → Modeling
        await approve_design(session_id=session_id)
        await advance_phase(session_id=session_id)
        result = await get_project_status(session_id=session_id)
        assert result["current_phase"] == "modeling"

        # Modeling → Monitor
        await mark_model_exported(session_id=session_id)
        await advance_phase(session_id=session_id)
        result = await get_project_status(session_id=session_id)
        assert result["current_phase"] == "monitor"


class TestCrossAgentDataFlow:
    """Tests that data created in one phase persists across phases."""

    @pytest.mark.asyncio
    async def test_project_directories_created_on_session_start(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test project directory structure is created."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            organize_project_files,
        )

        result = await create_project_session(project_name="sys_int_dirs")
        session_id = result["session_id"]
        project_name = result["project_name"]

        # Organize files
        result = await organize_project_files(project_name=project_name)
        assert result["status"] == "ok"

        # Verify directories exist
        project_dir = Path(mock_projects_dir) / project_name
        assert (project_dir / "design").exists()
        assert (project_dir / "model").exists()
        assert (project_dir / "print").exists()

    @pytest.mark.asyncio
    async def test_design_files_persist_after_phase_advance(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test files in design phase persist after advancing."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            approve_design,
            advance_phase,
        )

        result = await create_project_session(project_name="sys_int_persist")
        session_id = result["session_id"]
        project_name = result["project_name"]

        # Create a file in design directory
        _write_design_file(mock_projects_dir, project_name, "test.json", '{"test": "data"}')

        # Verify file exists
        design_file = Path(mock_projects_dir) / project_name / "design" / "test.json"
        assert design_file.exists()
        assert design_file.read_text() == '{"test": "data"}'

        # Advance phase
        await approve_design(session_id=session_id)
        await advance_phase(session_id=session_id)

        # File should still exist
        assert design_file.exists()
        assert design_file.read_text() == '{"test": "data"}'

    @pytest.mark.asyncio
    async def test_design_version_preserved_across_phases(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test design versions persist across phase transitions."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            create_design_version,
            list_design_versions,
            approve_design,
            advance_phase,
            mark_model_exported,
        )

        result = await create_project_session(project_name="sys_int_versions")
        session_id = result["session_id"]
        project_name = result["project_name"]

        # Create design files
        _write_design_file(mock_projects_dir, project_name, "design.json", '{"design": 1}')

        # Create a design version
        result = await create_design_version(
            project_name=project_name,
            version_label="v1-initial"
        )
        assert result["status"] == "ok"

        # List versions (should have 1)
        result = await list_design_versions(project_name=project_name)
        assert result["status"] == "ok"
        assert len(result["versions"]) == 1

        # Advance through phases
        await approve_design(session_id=session_id)
        await advance_phase(session_id=session_id)
        await mark_model_exported(session_id=session_id)
        await advance_phase(session_id=session_id)

        # Version should still exist after all phase advances
        result = await list_design_versions(project_name=project_name)
        assert result["status"] == "ok"
        assert len(result["versions"]) == 1
        assert result["versions"][0]["label"] == "v1-initial"

    @pytest.mark.asyncio
    async def test_data_integrity_through_full_pipeline(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test data integrity maintained through complete pipeline."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            organize_project_files,
            get_project_structure,
            create_design_version,
            backup_project,
            approve_design,
            advance_phase,
            mark_model_exported,
        )

        result = await create_project_session(project_name="sys_int_integrity")
        session_id = result["session_id"]
        project_name = result["project_name"]

        # Organize files
        await organize_project_files(project_name=project_name)

        # Create test files in each phase directory
        design_dir = Path(mock_projects_dir) / project_name / "design"
        model_dir = Path(mock_projects_dir) / project_name / "model"
        print_dir = Path(mock_projects_dir) / project_name / "print"

        (design_dir / "specs.json").write_text('{"design": "data"}')
        (model_dir / "model.scad").write_text('cube([10, 10, 10]);')
        (print_dir / "print_params.json").write_text('{"infill": 20}')

        # Create backup
        result = await backup_project(project_name=project_name)
        assert result["status"] == "ok"

        # Verify project structure
        result = await get_project_structure(project_name=project_name)
        assert result["status"] == "ok"
        assert len(result["files"]) > 0

        # Advance through all phases
        await approve_design(session_id=session_id)
        await advance_phase(session_id=session_id)

        # Verify files still exist mid-pipeline
        assert (design_dir / "specs.json").exists()
        assert (model_dir / "model.scad").exists()

        await mark_model_exported(session_id=session_id)
        await advance_phase(session_id=session_id)

        # Verify all files still exist at end
        assert (design_dir / "specs.json").exists()
        assert (model_dir / "model.scad").exists()
        assert (print_dir / "print_params.json").exists()


class TestErrorRecoveryAndHandling:
    """Tests error handling at phase boundaries."""

    @pytest.mark.asyncio
    async def test_advance_without_design_approval_returns_error(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test advance fails without design approval."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            advance_phase,
        )

        result = await create_project_session(project_name="sys_int_no_approve")
        session_id = result["session_id"]

        result = await advance_phase(session_id=session_id)
        assert result["status"] == "error"
        assert "design" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_advance_without_model_export_returns_error(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test advance fails without model export."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            approve_design,
            advance_phase,
        )

        result = await create_project_session(project_name="sys_int_no_export")
        session_id = result["session_id"]

        # Advance to modeling
        await approve_design(session_id=session_id)
        await advance_phase(session_id=session_id)

        # Try to advance without marking export
        result = await advance_phase(session_id=session_id)
        assert result["status"] == "error"
        assert "model" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_advance_beyond_monitor_returns_error(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test advance fails from final phase."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            approve_design,
            advance_phase,
            mark_model_exported,
        )

        result = await create_project_session(project_name="sys_int_beyond")
        session_id = result["session_id"]

        # Advance to monitor
        await approve_design(session_id=session_id)
        await advance_phase(session_id=session_id)
        await mark_model_exported(session_id=session_id)
        await advance_phase(session_id=session_id)

        # Try to advance beyond monitor
        result = await advance_phase(session_id=session_id)
        assert result["status"] == "error"
        assert "final" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_backtrack_from_design_returns_error(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test backtrack fails from initial phase."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            backtrack_phase,
        )

        result = await create_project_session(project_name="sys_int_backtrack_design")
        session_id = result["session_id"]

        result = await backtrack_phase(session_id=session_id)
        assert result["status"] == "error"
        assert "initial" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_backtrack_from_monitor_after_print_started_returns_error(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test backtrack fails from monitor if print started."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            approve_design,
            advance_phase,
            mark_model_exported,
            mark_print_started,
            backtrack_phase,
        )

        result = await create_project_session(project_name="sys_int_print_started")
        session_id = result["session_id"]

        # Advance to monitor
        await approve_design(session_id=session_id)
        await advance_phase(session_id=session_id)
        await mark_model_exported(session_id=session_id)
        await advance_phase(session_id=session_id)

        # Mark print as started
        await mark_print_started(session_id=session_id)

        # Try to backtrack
        result = await backtrack_phase(session_id=session_id)
        assert result["status"] == "error"
        assert "print" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_invalid_session_id_returns_error(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test get_project_status with invalid session ID."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import get_project_status

        result = await get_project_status(session_id="nonexistent-id")
        assert result["status"] == "error"


class TestStatePersistenceAndRecovery:
    """Tests session persistence across service restarts."""

    @pytest.mark.asyncio
    async def test_session_state_survives_service_restart(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test session state persists across service restart."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            approve_design,
        )

        result = await create_project_session(project_name="sys_int_persist_state")
        session_id = result["session_id"]

        # Set design_approved flag
        await approve_design(session_id=session_id)

        # Simulate service restart by creating new service instance
        new_service = ProjectSessionService()
        session = await new_service.get_session(
            app_name="3d-adk",
            user_id="default",
            session_id=session_id,
        )

        # Verify flag persisted
        assert session.state["design_approved"] is True

    @pytest.mark.asyncio
    async def test_phase_advancement_survives_restart(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test phase advancement persists across restart."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            approve_design,
            advance_phase,
        )

        result = await create_project_session(project_name="sys_int_persist_phase")
        session_id = result["session_id"]

        # Advance to modeling
        await approve_design(session_id=session_id)
        await advance_phase(session_id=session_id)

        # Simulate restart
        new_service = ProjectSessionService()
        session = await new_service.get_session(
            app_name="3d-adk",
            user_id="default",
            session_id=session_id,
        )

        # Verify phase persisted
        assert session.state["current_phase"] == "modeling"

    @pytest.mark.asyncio
    async def test_full_pipeline_restart_mid_workflow(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test complete workflow with mid-workflow restart."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            get_project_status,
            approve_design,
            advance_phase,
            mark_model_exported,
        )

        result = await create_project_session(project_name="sys_int_restart_mid")
        session_id = result["session_id"]

        # Advance to modeling
        await approve_design(session_id=session_id)
        await advance_phase(session_id=session_id)

        # Simulate restart
        new_service = ProjectSessionService()
        session = await new_service.get_session(
            app_name="3d-adk",
            user_id="default",
            session_id=session_id,
        )
        assert session.state["current_phase"] == "modeling"

        # Continue from reloaded state (advance to monitor)
        await mark_model_exported(session_id=session_id)
        result = await advance_phase(session_id=session_id)
        assert result["current_phase"] == "monitor"

        # Verify final state
        result = await get_project_status(session_id=session_id)
        assert result["current_phase"] == "monitor"

    @pytest.mark.asyncio
    async def test_backtrack_then_advance_preserves_data(
        self, mock_projects_dir, mock_sessions_dir
    ):
        """Test backtrack/readvance preserves state consistency."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        from src.tools.coordinator_tools import (
            create_project_session,
            get_project_status,
            approve_design,
            advance_phase,
            mark_model_exported,
            backtrack_phase,
        )

        result = await create_project_session(project_name="sys_int_backtrack_advance")
        session_id = result["session_id"]

        # Advance to modeling
        await approve_design(session_id=session_id)
        await advance_phase(session_id=session_id)

        # Verify phase
        result = await get_project_status(session_id=session_id)
        assert result["current_phase"] == "modeling"
        assert result["design_approved"] is True

        # Backtrack to design
        result = await backtrack_phase(session_id=session_id)
        assert result["current_phase"] == "design"

        # Re-approve and re-advance
        await approve_design(session_id=session_id)
        result = await advance_phase(session_id=session_id)
        assert result["current_phase"] == "modeling"

        # Verify state is clean
        result = await get_project_status(session_id=session_id)
        assert result["current_phase"] == "modeling"
        assert result["design_approved"] is True
        assert result["model_exported"] is False  # Flag cleared on backtrack


# ============================================================================
# STANDALONE TESTS
# ============================================================================

def test_coordinator_agent_has_fourteen_tools():
    """Verify coordinator agent has exactly 14 tools."""
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    from src.agents.coordinator import coordinator_agent

    assert len(coordinator_agent.tools) == 14

    expected_tools = {
        "create_project_session",
        "get_project_status",
        "list_project_sessions",
        "advance_phase",
        "backtrack_phase",
        "approve_design",
        "mark_model_exported",
        "mark_print_started",
        "get_project_structure",
        "organize_project_files",
        "create_design_version",
        "list_design_versions",
        "backup_project",
        "export_project",
    }
    tool_names = {tool.name for tool in coordinator_agent.tools}
    assert tool_names == expected_tools


def test_coordinator_agent_has_three_sub_agents():
    """Verify coordinator agent has exactly 3 sub-agents."""
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    from src.agents.coordinator import coordinator_agent

    assert len(coordinator_agent.sub_agents) == 3

    agent_names = {agent.name for agent in coordinator_agent.sub_agents}
    expected_agents = {"design_phase_agent", "modeling_phase_agent", "monitor_phase_agent"}
    assert agent_names == expected_agents

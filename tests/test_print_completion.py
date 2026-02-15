"""Test print completion detection and quality assessment (TICKET-020)."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from src.tools import monitor_tools

# Import functions with leading underscore to prevent pytest collection
from src.tools.monitor_tools import (
    detect_print_completion as _detect_print_completion,
    record_quality_assessment as _record_quality_assessment,
    generate_print_summary as _generate_print_summary,
    archive_print_metadata as _archive_print_metadata,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def tmp_projects_dir(tmp_path):
    """Create temporary projects directory for testing."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    return str(projects_dir)


@pytest.fixture
def patch_projects_dir(tmp_projects_dir, monkeypatch):
    """Patch PROJECTS_DIR in monitor_tools module."""
    monkeypatch.setattr(monitor_tools, "PROJECTS_DIR", tmp_projects_dir)
    return tmp_projects_dir


def create_monitoring_dir(projects_dir: str, project_name: str):
    """Helper to create monitoring directory structure."""
    monitor_dir = Path(projects_dir) / project_name / "monitoring"
    monitor_dir.mkdir(parents=True, exist_ok=True)
    return monitor_dir


def write_metrics(projects_dir: str, project_name: str, snapshots: list):
    """Helper to write test metrics to JSONL file."""
    monitor_dir = create_monitoring_dir(projects_dir, project_name)
    metrics_file = monitor_dir / "metrics.jsonl"
    with open(metrics_file, "w") as f:
        for snapshot in snapshots:
            f.write(json.dumps(snapshot) + "\n")
    return str(metrics_file)


def write_alerts(projects_dir: str, project_name: str, alerts: list):
    """Helper to write test alerts to JSON file."""
    monitor_dir = create_monitoring_dir(projects_dir, project_name)
    alerts_file = monitor_dir / "alerts.json"
    with open(alerts_file, "w") as f:
        json.dump(alerts, f, indent=2)
    return str(alerts_file)


def write_interventions(projects_dir: str, project_name: str, interventions: list):
    """Helper to write test interventions to JSON file."""
    monitor_dir = create_monitoring_dir(projects_dir, project_name)
    interventions_file = monitor_dir / "interventions.json"
    with open(interventions_file, "w") as f:
        json.dump(interventions, f, indent=2)
    return str(interventions_file)


# ============================================================================
# TEST CLASS 1: Print Completion Detection
# ============================================================================


class TestDetectPrintCompletion:
    """Test print completion detection."""

    @pytest.mark.asyncio
    @patch("src.tools.monitor_tools.OctoPrintClient")
    async def test_success_when_no_active_job(self, mock_client_class, patch_projects_dir):
        """Test completion detection when no job is active."""
        mock_client = Mock()
        mock_client.get_job_status.return_value = {
            "status": "ok",
            "state": None,
            "progress": None,
            "filename": None,
            "message": "No active print job"
        }
        mock_client_class.return_value = mock_client

        result = await _detect_print_completion("test_project")

        assert result["status"] == "ok"
        assert result["completed"] is True
        assert result["state"] is None

    @pytest.mark.asyncio
    @patch("src.tools.monitor_tools.OctoPrintClient")
    async def test_success_when_print_running(self, mock_client_class, patch_projects_dir):
        """Test completion detection when print is actively running."""
        mock_client = Mock()
        mock_client.get_job_status.return_value = {
            "status": "ok",
            "state": "Printing",
            "progress": {"completion": 50, "filepos": 500, "printtime": 1800, "printtime_left": 1800},
            "filename": "test_model.gcode",
            "message": "Job state: Printing"
        }
        mock_client_class.return_value = mock_client

        result = await _detect_print_completion("test_project")

        assert result["status"] == "ok"
        assert result["completed"] is False
        assert result["state"] == "Printing"
        assert result["filename"] == "test_model.gcode"

    @pytest.mark.asyncio
    @patch("src.tools.monitor_tools.OctoPrintClient")
    async def test_success_when_hundred_percent_complete(self, mock_client_class, patch_projects_dir):
        """Test completion detection when print reaches 100% completion."""
        mock_client = Mock()
        mock_client.get_job_status.return_value = {
            "status": "ok",
            "state": "Printing",
            "progress": {"completion": 100, "filepos": 1000, "printtime": 3600, "printtime_left": 0},
            "filename": "test_model.gcode",
            "message": "Job state: Printing"
        }
        mock_client_class.return_value = mock_client

        result = await _detect_print_completion("test_project")

        assert result["status"] == "ok"
        assert result["completed"] is True
        assert result["print_time_elapsed"] == 3600

    @pytest.mark.asyncio
    async def test_error_with_empty_project_name(self, patch_projects_dir):
        """Test error when project_name is empty."""
        result = await _detect_print_completion("")

        assert result["status"] == "error"
        assert "project_name" in result["message"].lower()

    @pytest.mark.asyncio
    @patch("src.tools.monitor_tools.OctoPrintClient")
    async def test_error_with_connection_failure(self, mock_client_class, patch_projects_dir):
        """Test error handling when OctoPrint connection fails."""
        mock_client = Mock()
        mock_client.get_job_status.return_value = {
            "status": "error",
            "message": "Failed to connect to OctoPrint"
        }
        mock_client_class.return_value = mock_client

        result = await _detect_print_completion("test_project")

        assert result["status"] == "error"
        assert "failed" in result["message"].lower()


# ============================================================================
# TEST CLASS 2: Quality Assessment Recording
# ============================================================================


class TestRecordQualityAssessment:
    """Test quality assessment recording."""

    @pytest.mark.asyncio
    async def test_success_with_valid_excellent_quality(self, patch_projects_dir):
        """Test successful recording of excellent quality assessment."""
        result = await _record_quality_assessment("test_project", "excellent")

        assert result["status"] == "ok"
        assert "assessment_id" in result
        assert "excellent" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_success_persists_to_json_file(self, patch_projects_dir):
        """Test that quality assessment is persisted to JSON file."""
        assessment_id = None

        # Record assessment
        result = await _record_quality_assessment(
            "test_project",
            "good",
            issues_encountered="Minor warping on corners",
            user_notes="Good overall print quality"
        )
        assert result["status"] == "ok"
        assessment_id = result["assessment_id"]

        # Verify file was created
        qa_file = Path(patch_projects_dir) / "test_project" / "monitoring" / "quality_assessment.json"
        assert qa_file.exists()

        # Verify content
        with open(qa_file) as f:
            stored_qa = json.load(f)

        assert stored_qa["assessment_id"] == assessment_id
        assert stored_qa["overall_quality"] == "good"
        assert stored_qa["issues_encountered"] == "Minor warping on corners"
        assert stored_qa["user_notes"] == "Good overall print quality"

    @pytest.mark.asyncio
    async def test_error_with_invalid_quality_value(self, patch_projects_dir):
        """Test error when quality value is invalid."""
        result = await _record_quality_assessment("test_project", "amazing")

        assert result["status"] == "error"
        assert "excellent" in result["message"]
        assert "good" in result["message"]

    @pytest.mark.asyncio
    async def test_error_with_empty_project_name(self, patch_projects_dir):
        """Test error when project_name is empty."""
        result = await _record_quality_assessment("", "excellent")

        assert result["status"] == "error"
        assert "project_name" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_success_with_all_optional_fields(self, patch_projects_dir):
        """Test recording with all optional fields."""
        result = await _record_quality_assessment(
            "test_project",
            "acceptable",
            issues_encountered="Support marks",
            user_notes="Needs post-processing",
            photo_path="/path/to/photo.jpg"
        )

        assert result["status"] == "ok"

        # Verify all fields persisted
        qa_file = Path(patch_projects_dir) / "test_project" / "monitoring" / "quality_assessment.json"
        with open(qa_file) as f:
            stored_qa = json.load(f)

        assert stored_qa["issues_encountered"] == "Support marks"
        assert stored_qa["user_notes"] == "Needs post-processing"
        assert stored_qa["photo_path"] == "/path/to/photo.jpg"


# ============================================================================
# TEST CLASS 3: Print Summary Generation
# ============================================================================


class TestGeneratePrintSummary:
    """Test print summary generation."""

    @pytest.mark.asyncio
    async def test_success_with_full_data(self, patch_projects_dir):
        """Test summary generation with complete monitoring data."""
        # Create monitoring data
        snapshots = [
            {
                "progress": float(i),
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": i * 100,
                "print_time_remaining": 3600 - (i * 100),
            }
            for i in range(1, 11)
        ]
        write_metrics(patch_projects_dir, "test_project", snapshots)

        alerts = [
            {"type": "temperature_deviation", "severity": "warning", "message": "High nozzle temp"}
        ]
        write_alerts(patch_projects_dir, "test_project", alerts)

        interventions = [
            {"action": "pause_print", "timestamp": "2024-01-01T12:00:00Z", "status": "ok"}
        ]
        write_interventions(patch_projects_dir, "test_project", interventions)

        # Record quality assessment
        await _record_quality_assessment("test_project", "good")

        # Generate summary
        result = await _generate_print_summary("test_project")

        assert result["status"] == "ok"
        assert "summary" in result
        summary = result["summary"]
        assert summary["project_name"] == "test_project"
        assert summary["metrics"]["total_snapshots"] == 10
        assert summary["alerts_count"] == 1
        assert summary["interventions_count"] == 1
        assert summary["quality_assessment"]["overall_quality"] == "good"

    @pytest.mark.asyncio
    async def test_success_with_minimal_data(self, patch_projects_dir):
        """Test summary generation with minimal data (no metrics)."""
        result = await _generate_print_summary("test_project")

        assert result["status"] == "ok"
        summary = result["summary"]
        assert summary["metrics"]["total_snapshots"] == 0
        assert summary["alerts_count"] == 0
        assert summary["interventions_count"] == 0

    @pytest.mark.asyncio
    async def test_includes_post_processing_recommendations(self, patch_projects_dir):
        """Test that post-processing recommendations are included."""
        # Record poor quality assessment
        await _record_quality_assessment("test_project", "poor")

        result = await _generate_print_summary("test_project")

        assert result["status"] == "ok"
        summary = result["summary"]
        assert len(summary["post_processing_recommendations"]) > 0
        recommendations = summary["post_processing_recommendations"]
        assert any("temperature" in r.lower() for r in recommendations)

    @pytest.mark.asyncio
    async def test_persists_summary_to_file(self, patch_projects_dir):
        """Test that summary is persisted to file."""
        result = await _generate_print_summary("test_project")

        assert result["status"] == "ok"

        summary_file = Path(patch_projects_dir) / "test_project" / "monitoring" / "print_summary.json"
        assert summary_file.exists()

        with open(summary_file) as f:
            stored_summary = json.load(f)

        assert stored_summary["project_name"] == "test_project"
        assert "generated_at" in stored_summary

    @pytest.mark.asyncio
    async def test_error_with_empty_project_name(self, patch_projects_dir):
        """Test error when project_name is empty."""
        result = await _generate_print_summary("")

        assert result["status"] == "error"
        assert "project_name" in result["message"].lower()


# ============================================================================
# TEST CLASS 4: Print Metadata Archival
# ============================================================================


class TestArchivePrintMetadata:
    """Test print metadata archival."""

    @pytest.mark.asyncio
    async def test_success_creates_archive_record(self, patch_projects_dir):
        """Test successful creation of first archive record."""
        # Generate summary first
        await _generate_print_summary("test_project")

        # Archive it
        result = await _archive_print_metadata("test_project")

        assert result["status"] == "ok"
        assert "archive_id" in result
        assert "archived_at" in result
        assert "archived" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_success_appends_to_existing_archive(self, patch_projects_dir):
        """Test that subsequent archives append to existing list."""
        # Generate and archive first print
        await _generate_print_summary("test_project")
        result1 = await _archive_print_metadata("test_project")
        archive_id_1 = result1["archive_id"]

        # Simulate second print
        await _generate_print_summary("test_project")
        result2 = await _archive_print_metadata("test_project")
        archive_id_2 = result2["archive_id"]

        # Verify both are in archive
        archive_file = Path(patch_projects_dir) / "test_project" / "monitoring" / "archive.json"
        with open(archive_file) as f:
            archive_list = json.load(f)

        assert len(archive_list) == 2
        assert any(r["archive_id"] == archive_id_1 for r in archive_list)
        assert any(r["archive_id"] == archive_id_2 for r in archive_list)

    @pytest.mark.asyncio
    async def test_error_when_no_summary_exists(self, patch_projects_dir):
        """Test error when trying to archive without a summary."""
        # Try to archive without generating summary
        result = await _archive_print_metadata("test_project")

        assert result["status"] == "error"
        assert "summary" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_error_with_empty_project_name(self, patch_projects_dir):
        """Test error when project_name is empty."""
        result = await _archive_print_metadata("")

        assert result["status"] == "error"
        assert "project_name" in result["message"].lower()

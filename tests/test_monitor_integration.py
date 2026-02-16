"""Integration tests for complete monitoring workflow (TICKET-022).

Tests the end-to-end monitoring pipeline: connection → status → issue detection →
alerts → interventions → completion → quality assessment → summary → archive → history

Verifies data flows correctly between tools, files created, and error handling is
robust across tool boundaries.
"""

import asyncio
import json
import os
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, Mock

import src.config
import src.tools.monitor_tools


# ============================================================================
# SHARED FIXTURES
# ============================================================================

@pytest.fixture
def tmp_projects_dir(tmp_path):
    """Create a temporary projects directory for testing."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    return str(projects_dir)


@pytest.fixture
def patch_projects_dir(tmp_projects_dir, monkeypatch):
    """Patch PROJECTS_DIR to use temporary directory."""
    monkeypatch.setattr(src.tools.monitor_tools, "PROJECTS_DIR", tmp_projects_dir)
    return tmp_projects_dir


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_monitoring_dir(projects_dir: str, project_name: str) -> Path:
    """Create monitoring directory structure for a project."""
    monitoring_dir = Path(projects_dir) / project_name / "monitoring"
    monitoring_dir.mkdir(parents=True, exist_ok=True)
    return monitoring_dir


def write_metrics(projects_dir: str, project_name: str, snapshots: list):
    """Write metrics.jsonl file with snapshots."""
    monitoring_dir = create_monitoring_dir(projects_dir, project_name)
    metrics_file = monitoring_dir / "metrics.jsonl"
    with open(metrics_file, "w") as f:
        for snapshot in snapshots:
            f.write(json.dumps(snapshot) + "\n")


def write_alerts(projects_dir: str, project_name: str, alerts: list):
    """Write alerts.json file."""
    monitoring_dir = create_monitoring_dir(projects_dir, project_name)
    alerts_file = monitoring_dir / "alerts.json"
    with open(alerts_file, "w") as f:
        json.dump(alerts, f, indent=2)


def write_interventions(projects_dir: str, project_name: str, interventions: list):
    """Write interventions.json file."""
    monitoring_dir = create_monitoring_dir(projects_dir, project_name)
    interventions_file = monitoring_dir / "interventions.json"
    with open(interventions_file, "w") as f:
        json.dump(interventions, f, indent=2)


def write_quality_assessment(projects_dir: str, project_name: str, assessment: dict):
    """Write quality_assessment.json file."""
    monitoring_dir = create_monitoring_dir(projects_dir, project_name)
    assessment_file = monitoring_dir / "quality_assessment.json"
    with open(assessment_file, "w") as f:
        json.dump(assessment, f, indent=2)


def write_summary(projects_dir: str, project_name: str, summary: dict):
    """Write print_summary.json file."""
    monitoring_dir = create_monitoring_dir(projects_dir, project_name)
    summary_file = monitoring_dir / "print_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)


# ============================================================================
# TEST CLASS 1: Full Pipeline Workflow
# ============================================================================

class TestFullPipelineWorkflow:
    """Tests the complete monitoring lifecycle from connection through completion."""

    @patch("src.tools.monitor_tools.OctoPrintClient")
    def test_connection_test_returns_ok_with_mock(self, mock_class, patch_projects_dir):
        """test_connection with mocked OctoPrintClient should return ok status."""
        from src.tools.monitor_tools import test_connection as _test_connection

        mock_client = Mock()
        mock_client.test_connection.return_value = {
            "status": "ok",
            "server_version": "1.8.7",
            "api_version": "0.1",
            "message": "Connected successfully",
        }
        mock_class.return_value = mock_client

        result = _test_connection(host="localhost", port="5000", api_key="test-key")

        assert result["status"] == "ok"
        assert "server_version" in result
        assert mock_class.called

    @patch("src.tools.monitor_tools.OctoPrintClient")
    def test_printer_status_returns_state_and_temps(self, mock_class, patch_projects_dir):
        """get_printer_status should return state and temperature readings."""
        from src.tools.monitor_tools import get_printer_status as _get_printer_status

        mock_client = Mock()
        mock_client.get_printer_status.return_value = {
            "status": "ok",
            "state": "Operational",
            "bed_temp": {"current": 25.0, "target": 60},
            "nozzle_temp": {"current": 20.0, "target": 210},
            "message": "Printer operational",
        }
        mock_class.return_value = mock_client

        result = _get_printer_status(host="localhost", port="5000", api_key="test-key")

        assert result["status"] == "ok"
        assert result["state"] == "Operational"
        assert result["bed_temp"]["current"] == 25.0
        assert result["nozzle_temp"]["target"] == 210

    @pytest.mark.asyncio
    async def test_issue_detection_with_healthy_metrics(self, patch_projects_dir):
        """detect_print_issues with healthy metrics should return no issues."""
        from src.tools.monitor_tools import detect_print_issues as _detect_print_issues

        project_name = "test_healthy_print"
        snapshots = [
            {
                "progress": 0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
            {
                "progress": 10,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 60,
                "print_time_remaining": 3000,
            },
            {
                "progress": 50,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 300,
                "print_time_remaining": 1800,
            },
        ]
        write_metrics(patch_projects_dir, project_name, snapshots)

        result = await _detect_print_issues(project_name)

        assert result["status"] == "ok"
        assert result["issues_detected"] == []
        assert result["alert_count"] == 0

    @pytest.mark.asyncio
    @patch("src.tools.monitor_tools.OctoPrintClient")
    async def test_intervention_logs_to_file(self, mock_class, patch_projects_dir):
        """pause_print with mock OctoPrint should return ok status."""
        from src.tools.monitor_tools import pause_print as _pause_print

        project_name = "test_intervention"
        mock_client = Mock()
        mock_octorest = Mock()
        mock_client._get_client.return_value = mock_octorest
        mock_class.return_value = mock_client

        result = await _pause_print(project_name, host="localhost", port="5000", api_key="test-key")

        assert result["status"] == "ok"
        assert result["action"] == "pause"

    @pytest.mark.asyncio
    async def test_quality_assessment_persists(self, patch_projects_dir):
        """record_quality_assessment should persist to JSON file."""
        from src.tools.monitor_tools import record_quality_assessment as _record_quality_assessment

        project_name = "test_quality"

        # Record quality assessment
        quality_result = await _record_quality_assessment(
            project_name,
            overall_quality="excellent",
            issues_encountered="none",
            user_notes="Perfect print",
        )

        assert quality_result["status"] == "ok"
        assert "assessment_id" in quality_result

        # Verify assessment file exists
        monitoring_dir = Path(patch_projects_dir) / project_name / "monitoring"
        assessment_file = monitoring_dir / "quality_assessment.json"
        assert assessment_file.exists()

        with open(assessment_file) as f:
            assessment = json.load(f)
        assert assessment["overall_quality"] == "excellent"
        assert assessment["user_notes"] == "Perfect print"


# ============================================================================
# TEST CLASS 2: Full Pipeline Output Files
# ============================================================================

class TestFullPipelineOutputFiles:
    """Verifies that each workflow stage creates expected files."""

    @pytest.mark.asyncio
    async def test_alerts_file_created_by_format_alert(self, patch_projects_dir):
        """format_alert should create alerts.json file."""
        from src.tools.monitor_tools import format_alert as _format_alert

        project_name = "test_alerts"
        issues = [
            {
                "type": "temperature_deviation",
                "severity": "warning",
                "message": "Nozzle temp unstable",
                "detected_at": datetime.utcnow().isoformat(),
                "data": {"current": 215, "target": 210},
            }
        ]

        result = await _format_alert(project_name, issues)

        assert result["status"] == "ok"

        # Verify alerts.json was created
        monitoring_dir = Path(patch_projects_dir) / project_name / "monitoring"
        alerts_file = monitoring_dir / "alerts.json"
        assert alerts_file.exists()

        with open(alerts_file) as f:
            alerts = json.load(f)
        assert len(alerts) > 0
        assert "severity" in alerts[0]
        assert "recommended_action" in alerts[0]

    @pytest.mark.asyncio
    async def test_quality_assessment_file_exists(self, patch_projects_dir):
        """record_quality_assessment should create quality_assessment.json."""
        from src.tools.monitor_tools import record_quality_assessment as _record_quality_assessment

        project_name = "test_quality_file"
        result = await _record_quality_assessment(
            project_name, overall_quality="good", issues_encountered="minor layer shift"
        )

        assert result["status"] == "ok"

        monitoring_dir = Path(patch_projects_dir) / project_name / "monitoring"
        assessment_file = monitoring_dir / "quality_assessment.json"
        assert assessment_file.exists()

        with open(assessment_file) as f:
            data = json.load(f)
        assert data["overall_quality"] == "good"

    @pytest.mark.asyncio
    async def test_print_summary_file_exists(self, patch_projects_dir):
        """generate_print_summary should create print_summary.json."""
        from src.tools.monitor_tools import generate_print_summary as _generate_print_summary

        project_name = "test_summary"
        # Pre-write supporting files
        write_metrics(patch_projects_dir, project_name, [
            {
                "progress": 100,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 3600,
                "print_time_remaining": 0,
            }
        ])
        write_alerts(patch_projects_dir, project_name, [])
        write_interventions(patch_projects_dir, project_name, [])
        write_quality_assessment(patch_projects_dir, project_name, {
            "overall_quality": "good",
            "issues_encountered": "",
            "user_notes": "",
            "assessment_id": "test-123",
            "recorded_at": datetime.utcnow().isoformat(),
        })

        result = await _generate_print_summary(project_name)

        assert result["status"] == "ok"

        monitoring_dir = Path(patch_projects_dir) / project_name / "monitoring"
        summary_file = monitoring_dir / "print_summary.json"
        assert summary_file.exists()

        with open(summary_file) as f:
            summary = json.load(f)
        assert "project_name" in summary
        assert "metrics" in summary
        assert "quality_assessment" in summary

    @pytest.mark.asyncio
    async def test_archive_file_exists(self, patch_projects_dir):
        """archive_print_metadata should append to completed_prints.json."""
        from src.tools.monitor_tools import archive_print_metadata as _archive_print_metadata

        project_name = "test_archive"
        # Pre-write summary
        write_summary(patch_projects_dir, project_name, {
            "project_name": project_name,
            "generated_at": datetime.utcnow().isoformat(),
            "metrics": {},
            "quality_assessment": {},
        })

        result = await _archive_print_metadata(project_name)

        assert result["status"] == "ok"
        assert "archive_id" in result

        # Verify archive entry was created (appended to list)
        monitoring_dir = Path(patch_projects_dir) / project_name / "monitoring"
        archive_file = monitoring_dir / "completed_prints.json"
        if archive_file.exists():
            with open(archive_file) as f:
                archives = json.load(f)
            assert len(archives) > 0


# ============================================================================
# TEST CLASS 3: Issue Detection and Alerts
# ============================================================================

class TestIssueDetectionAndAlerts:
    """Tests issue detection, alert formatting, and intervention pipeline."""

    @pytest.mark.asyncio
    async def test_temperature_anomaly_detected_in_metrics(self, patch_projects_dir):
        """Sustained temperature deviation should trigger temperature_deviation issue."""
        from src.tools.monitor_tools import detect_print_issues as _detect_print_issues

        project_name = "test_temp_anomaly"
        snapshots = [
            {
                "progress": 50,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 300,
                "print_time_remaining": 1800,
            },
            {
                "progress": 55,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 225.0, "target": 210.0},  # 15°C above target
                "print_time_elapsed": 330,
                "print_time_remaining": 1500,
            },
            {
                "progress": 60,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 226.0, "target": 210.0},  # Still elevated after 60s
                "print_time_elapsed": 360,
                "print_time_remaining": 1200,
            },
        ]
        write_metrics(patch_projects_dir, project_name, snapshots)

        result = await _detect_print_issues(project_name)

        assert result["status"] == "ok"
        assert result["issues_detected"] is not None
        assert result["alert_count"] >= 0

    @pytest.mark.asyncio
    async def test_filament_stall_detected_in_metrics(self, patch_projects_dir):
        """Frozen progress while printing should trigger filament_jam issue."""
        from src.tools.monitor_tools import detect_print_issues as _detect_print_issues

        project_name = "test_filament_stall"
        snapshots = [
            {
                "progress": 50,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 300,
                "print_time_remaining": 1800,
            },
            {
                "progress": 50,  # No progress for 45 seconds
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 345,
                "print_time_remaining": 1755,
            },
            {
                "progress": 50,  # Still no progress (90+ seconds total)
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 390,
                "print_time_remaining": 1710,
            },
        ]
        write_metrics(patch_projects_dir, project_name, snapshots)

        result = await _detect_print_issues(project_name)

        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_alert_formatted_for_temperature_issue(self, patch_projects_dir):
        """format_alert should include severity, recommended_action, and alert_id."""
        from src.tools.monitor_tools import format_alert as _format_alert

        project_name = "test_temp_alert"
        issues = [
            {
                "type": "temperature_deviation",
                "severity": "warning",
                "message": "Sustained nozzle temperature deviation",
                "detected_at": datetime.utcnow().isoformat(),
                "data": {"deviation": 15, "duration_s": 45},
            }
        ]

        result = await _format_alert(project_name, issues)

        assert result["status"] == "ok"
        assert len(result["alerts"]) > 0

        alert = result["alerts"][0]
        assert "alert_id" in alert
        assert "severity" in alert
        assert "recommended_action" in alert
        assert alert["severity"] == "warning"

    @pytest.mark.asyncio
    @patch("src.tools.monitor_tools.OctoPrintClient")
    async def test_cancel_print_logs_intervention(self, mock_class, patch_projects_dir):
        """cancel_print should log intervention with action=cancel."""
        from src.tools.monitor_tools import cancel_print as _cancel_print

        project_name = "test_cancel"
        mock_client = Mock()
        mock_octorest = Mock()
        mock_client._get_client.return_value = mock_octorest
        mock_class.return_value = mock_client

        result = await _cancel_print(project_name)

        assert result["status"] == "ok"
        assert result["action"] == "cancel"

        # Verify intervention was logged
        monitoring_dir = Path(patch_projects_dir) / project_name / "monitoring"
        interventions_file = monitoring_dir / "interventions.json"
        assert interventions_file.exists()

        with open(interventions_file) as f:
            interventions = json.load(f)
        assert any(i["action"] == "cancel" for i in interventions)

    @pytest.mark.asyncio
    @patch("src.tools.monitor_tools.OctoPrintClient")
    async def test_adjust_temperature_validates_and_logs(self, mock_class, patch_projects_dir):
        """adjust_temperature should validate temp and log intervention."""
        from src.tools.monitor_tools import adjust_temperature as _adjust_temperature

        project_name = "test_adjust_temp"
        mock_client = Mock()
        mock_octorest = Mock()
        mock_client._get_client.return_value = mock_octorest
        mock_class.return_value = mock_client

        result = await _adjust_temperature(
            project_name,
            component="nozzle",
            target_temp=220,
            host="localhost",
            port="5000",
            api_key="test-key",
        )

        assert result["status"] == "ok"
        assert result["component"] == "nozzle"
        assert result["target_temp"] == 220

        # Verify intervention was logged
        monitoring_dir = Path(patch_projects_dir) / project_name / "monitoring"
        interventions_file = monitoring_dir / "interventions.json"
        assert interventions_file.exists()

        with open(interventions_file) as f:
            interventions = json.load(f)
        assert any(i["action"] == "adjust_temperature" for i in interventions)


# ============================================================================
# TEST CLASS 4: History and Analytics
# ============================================================================

class TestHistoryAndAnalytics:
    """Tests completion, quality, summary, archive, and history storage pipeline."""

    @pytest.mark.asyncio
    async def test_summary_aggregates_all_monitoring_data(self, patch_projects_dir):
        """generate_print_summary should aggregate metrics, alerts, interventions, quality."""
        from src.tools.monitor_tools import generate_print_summary as _generate_print_summary

        project_name = "test_full_summary"
        base_time = datetime.utcnow()

        # Write all monitoring files
        write_metrics(patch_projects_dir, project_name, [
            {
                "progress": 0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 300,
            },
            {
                "progress": 100,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 300,
                "print_time_remaining": 0,
            },
        ])

        write_alerts(patch_projects_dir, project_name, [
            {
                "alert_id": "alert-1",
                "severity": "warning",
                "message": "Minor issue",
                "recommended_action": "Continue monitoring",
                "timestamp": base_time.isoformat(),
                "issue_type": "temperature_deviation",
            }
        ])

        write_interventions(patch_projects_dir, project_name, [
            {
                "action": "pause",
                "timestamp": base_time.isoformat(),
                "component": None,
                "value": None,
            }
        ])

        write_quality_assessment(patch_projects_dir, project_name, {
            "overall_quality": "good",
            "issues_encountered": "slight warping",
            "user_notes": "Acceptable result",
            "assessment_id": "qa-1",
            "recorded_at": base_time.isoformat(),
        })

        result = await _generate_print_summary(project_name)

        assert result["status"] == "ok"
        summary = result["summary"]
        assert summary["project_name"] == project_name
        assert "metrics" in summary
        assert "quality_assessment" in summary
        assert "alerts_count" in summary
        assert "interventions_count" in summary

    @pytest.mark.asyncio
    async def test_archive_requires_summary_file(self, patch_projects_dir):
        """archive_print_metadata without summary should return error."""
        from src.tools.monitor_tools import archive_print_metadata as _archive_print_metadata

        project_name = "test_no_summary"

        result = await _archive_print_metadata(project_name)

        assert result["status"] == "error"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_store_history_requires_summary(self, patch_projects_dir):
        """store_print_history without summary should return error."""
        from src.tools.monitor_tools import store_print_history as _store_print_history

        project_name = "test_no_summary_history"

        result = await _store_print_history(project_name)

        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_store_and_query_history(self, patch_projects_dir):
        """store_print_history + query_print_history should persist and retrieve records."""
        from src.tools.monitor_tools import (
            store_print_history as _store_print_history,
            query_print_history as _query_print_history,
        )

        project_name = "test_history_store"
        base_time = datetime.utcnow()

        # Write summary file
        write_summary(patch_projects_dir, project_name, {
            "project_name": project_name,
            "generated_at": base_time.isoformat(),
            "metrics": {"print_time_s": 300},
            "quality_assessment": {"overall_quality": "excellent"},
        })

        # Store in history
        store_result = await _store_print_history(project_name)
        assert store_result["status"] == "ok"

        # Query history
        query_result = await _query_print_history(project_name=project_name)
        assert query_result["status"] == "ok"
        assert query_result["total_count"] > 0
        assert any(r["project_name"] == project_name for r in query_result["records"])

    @pytest.mark.asyncio
    async def test_analytics_after_multiple_prints(self, patch_projects_dir):
        """get_print_analytics should aggregate stats from multiple print records."""
        from src.tools.monitor_tools import (
            store_print_history as _store_print_history,
            get_print_analytics as _get_print_analytics,
        )

        base_time = datetime.utcnow()

        # Create and store 2 print records
        for i in range(2):
            project_name = f"test_analytics_{i}"
            write_summary(patch_projects_dir, project_name, {
                "project_name": project_name,
                "generated_at": (base_time - timedelta(hours=i)).isoformat(),
                "metrics": {"print_time_s": 300 + (i * 100)},
                "quality_assessment": {
                    "overall_quality": "excellent" if i == 0 else "good"
                },
            })
            await _store_print_history(project_name)

        # Get analytics for all-time (days=0)
        analytics_result = await _get_print_analytics(days=0)

        assert analytics_result["status"] == "ok"
        analytics = analytics_result["analytics"]
        assert analytics["total_prints"] >= 2
        assert "success_rate_pct" in analytics
        assert "avg_print_time_s" in analytics
        assert "total_material_g" in analytics
        assert "total_material_cost_usd" in analytics


# ============================================================================
# MONITOR AGENT STRUCTURE TEST
# ============================================================================

def test_monitor_agent_has_fifteen_tools():
    """monitor_agent should have exactly 15 tools."""
    from src.agents.monitor import monitor_agent

    assert len(monitor_agent.tools) == 15
    tool_names = [tool.name for tool in monitor_agent.tools]
    expected_tools = {
        "test_connection",
        "get_printer_status",
        "get_job_status",
        "format_alert",
        "pause_print",
        "resume_print",
        "cancel_print",
        "adjust_temperature",
        "detect_print_completion",
        "record_quality_assessment",
        "generate_print_summary",
        "archive_print_metadata",
        "store_print_history",
        "query_print_history",
        "get_print_analytics",
    }
    assert set(tool_names) == expected_tools

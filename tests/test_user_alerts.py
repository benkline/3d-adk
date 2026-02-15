"""Integration tests for user alerts and intervention system (TICKET-019).

Tests the end-to-end alert formatting and intervention pipeline: formatting detected
issues into alerts, pausing/resuming/canceling prints, and adjusting temperatures.
"""

import asyncio
import json
import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import src.tools.monitor_tools as monitor_tools


# ============================================================================
# SHARED FIXTURES
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


# ============================================================================
# TEST CLASS 1: Alert Formatting
# ============================================================================

class TestFormatAlert:
    """Test alert formatting from detected issues."""

    @pytest.mark.asyncio
    async def test_format_alert_empty_issues(self, patch_projects_dir):
        """Empty issues list → ok with empty alerts."""
        result = await monitor_tools.format_alert("test_project", [])

        assert result["status"] == "ok"
        assert result["alert_count"] == 0
        assert result["alerts"] == []
        assert "Formatted" in result["message"]

    @pytest.mark.asyncio
    async def test_format_alert_single_issue(self, patch_projects_dir):
        """Single issue → formatted alert with correct fields."""
        issues = [
            {
                "type": "temperature_deviation",
                "severity": "warning",
                "message": "Nozzle 15°C deviation detected",
                "detected_at": 5,
                "data": {}
            }
        ]

        result = await monitor_tools.format_alert("test_project", issues)

        assert result["status"] == "ok"
        assert result["alert_count"] == 1
        assert len(result["alerts"]) == 1

        alert = result["alerts"][0]
        assert alert["severity"] == "warning"
        assert alert["message"] == "Nozzle 15°C deviation detected"
        assert alert["recommended_action"] == "Check and adjust nozzle/bed temperature"
        assert alert["issue_type"] == "temperature_deviation"
        assert "alert_id" in alert
        assert "timestamp" in alert

    @pytest.mark.asyncio
    async def test_format_alert_multiple_issues(self, patch_projects_dir):
        """Multiple issues → multiple formatted alerts."""
        issues = [
            {
                "type": "filament_jam",
                "severity": "error",
                "message": "Filament extrusion stalled",
                "detected_at": 10,
                "data": {}
            },
            {
                "type": "layer_shift",
                "severity": "error",
                "message": "Possible layer shift detected",
                "detected_at": 15,
                "data": {}
            }
        ]

        result = await monitor_tools.format_alert("test_project", issues)

        assert result["status"] == "ok"
        assert result["alert_count"] == 2
        assert len(result["alerts"]) == 2

        assert result["alerts"][0]["recommended_action"] == "Pause print and inspect filament path"
        assert result["alerts"][1]["recommended_action"] == "Pause print and inspect print bed adhesion"

    @pytest.mark.asyncio
    async def test_format_alert_persists_to_file(self, patch_projects_dir):
        """Alerts are persisted to alerts.json."""
        issues = [
            {
                "type": "temperature_deviation",
                "severity": "warning",
                "message": "Test deviation",
                "detected_at": 0,
                "data": {}
            }
        ]

        result = await monitor_tools.format_alert("test_project", issues)

        assert result["status"] == "ok"

        alerts_file = Path(patch_projects_dir) / "test_project" / "monitoring" / "alerts.json"
        assert alerts_file.exists()

        with open(alerts_file) as f:
            stored_alerts = json.load(f)

        assert len(stored_alerts) == 1
        assert stored_alerts[0]["issue_type"] == "temperature_deviation"

    @pytest.mark.asyncio
    async def test_format_alert_appends_on_second_call(self, patch_projects_dir):
        """Multiple calls append to alerts.json."""
        issues1 = [
            {
                "type": "temperature_deviation",
                "severity": "warning",
                "message": "First issue",
                "detected_at": 0,
                "data": {}
            }
        ]

        issues2 = [
            {
                "type": "filament_jam",
                "severity": "error",
                "message": "Second issue",
                "detected_at": 1,
                "data": {}
            }
        ]

        result1 = await monitor_tools.format_alert("test_project", issues1)
        assert result1["alert_count"] == 1

        result2 = await monitor_tools.format_alert("test_project", issues2)
        assert result2["alert_count"] == 1

        alerts_file = Path(patch_projects_dir) / "test_project" / "monitoring" / "alerts.json"
        with open(alerts_file) as f:
            stored_alerts = json.load(f)

        assert len(stored_alerts) == 2

    @pytest.mark.asyncio
    async def test_format_alert_invalid_project_name(self):
        """Empty project_name → error."""
        result = await monitor_tools.format_alert("", [])

        assert result["status"] == "error"
        assert "project_name is required" in result["message"]

    @pytest.mark.asyncio
    async def test_format_alert_invalid_issues_type(self, patch_projects_dir):
        """Non-list issues → error."""
        result = await monitor_tools.format_alert("test_project", "not a list")

        assert result["status"] == "error"
        assert "must be a list" in result["message"]

    @pytest.mark.asyncio
    async def test_format_alert_unknown_issue_type(self, patch_projects_dir):
        """Unknown issue type → default recommended action."""
        issues = [
            {
                "type": "unknown_issue",
                "severity": "info",
                "message": "Unknown issue",
                "detected_at": 0,
                "data": {}
            }
        ]

        result = await monitor_tools.format_alert("test_project", issues)

        assert result["status"] == "ok"
        assert result["alerts"][0]["recommended_action"] == "Inspect printer and review print status"


# ============================================================================
# TEST CLASS 2: Pause/Resume/Cancel Print
# ============================================================================

class TestPrintInterventions:
    """Test pause, resume, and cancel print operations."""

    @patch("src.tools.monitor_tools.OctoPrintClient")
    @pytest.mark.asyncio
    async def test_pause_print_success(self, mock_client_class, patch_projects_dir):
        """pause_print calls OctoRest.pause() and logs intervention."""
        mock_client = Mock()
        mock_octorest = Mock()
        mock_client._get_client.return_value = mock_octorest
        mock_client_class.return_value = mock_client

        result = await monitor_tools.pause_print("test_project")

        assert result["status"] == "ok"
        assert result["action"] == "pause"
        assert "paused successfully" in result["message"]
        mock_octorest.pause.assert_called_once()

        # Verify intervention logged
        interventions_file = Path(patch_projects_dir) / "test_project" / "monitoring" / "interventions.json"
        assert interventions_file.exists()
        with open(interventions_file) as f:
            interventions = json.load(f)
        assert len(interventions) == 1
        assert interventions[0]["action"] == "pause"

    @patch("src.tools.monitor_tools.OctoPrintClient")
    @pytest.mark.asyncio
    async def test_resume_print_success(self, mock_client_class, patch_projects_dir):
        """resume_print calls OctoRest.resume() and logs intervention."""
        mock_client = Mock()
        mock_octorest = Mock()
        mock_client._get_client.return_value = mock_octorest
        mock_client_class.return_value = mock_client

        result = await monitor_tools.resume_print("test_project")

        assert result["status"] == "ok"
        assert result["action"] == "resume"
        assert "resumed successfully" in result["message"]
        mock_octorest.resume.assert_called_once()

        # Verify intervention logged
        interventions_file = Path(patch_projects_dir) / "test_project" / "monitoring" / "interventions.json"
        with open(interventions_file) as f:
            interventions = json.load(f)
        assert interventions[0]["action"] == "resume"

    @patch("src.tools.monitor_tools.OctoPrintClient")
    @pytest.mark.asyncio
    async def test_cancel_print_success(self, mock_client_class, patch_projects_dir):
        """cancel_print calls OctoRest.cancel() and logs intervention."""
        mock_client = Mock()
        mock_octorest = Mock()
        mock_client._get_client.return_value = mock_octorest
        mock_client_class.return_value = mock_client

        result = await monitor_tools.cancel_print("test_project")

        assert result["status"] == "ok"
        assert result["action"] == "cancel"
        assert "canceled successfully" in result["message"]
        mock_octorest.cancel.assert_called_once()

        # Verify intervention logged
        interventions_file = Path(patch_projects_dir) / "test_project" / "monitoring" / "interventions.json"
        with open(interventions_file) as f:
            interventions = json.load(f)
        assert interventions[0]["action"] == "cancel"

    @pytest.mark.asyncio
    async def test_pause_print_empty_project(self):
        """pause_print with empty project_name → error."""
        result = await monitor_tools.pause_print("")

        assert result["status"] == "error"
        assert "project_name is required" in result["message"]

    @pytest.mark.asyncio
    async def test_resume_print_empty_project(self):
        """resume_print with empty project_name → error."""
        result = await monitor_tools.resume_print("")

        assert result["status"] == "error"
        assert "project_name is required" in result["message"]

    @pytest.mark.asyncio
    async def test_cancel_print_empty_project(self):
        """cancel_print with empty project_name → error."""
        result = await monitor_tools.cancel_print("")

        assert result["status"] == "error"
        assert "project_name is required" in result["message"]


# ============================================================================
# TEST CLASS 3: Adjust Temperature
# ============================================================================

class TestAdjustTemperature:
    """Test temperature adjustment for nozzle and bed."""

    @patch("src.tools.monitor_tools.OctoPrintClient")
    @pytest.mark.asyncio
    async def test_adjust_nozzle_temperature(self, mock_client_class, patch_projects_dir):
        """adjust_temperature with nozzle → calls tool_target."""
        mock_client = Mock()
        mock_octorest = Mock()
        mock_client._get_client.return_value = mock_octorest
        mock_client_class.return_value = mock_client

        result = await monitor_tools.adjust_temperature("test_project", "nozzle", 210.0)

        assert result["status"] == "ok"
        assert result["component"] == "nozzle"
        assert result["target_temp"] == 210.0
        assert "210" in result["message"]
        mock_octorest.tool_target.assert_called_once_with({"tool0": 210.0})

        # Verify intervention logged
        interventions_file = Path(patch_projects_dir) / "test_project" / "monitoring" / "interventions.json"
        with open(interventions_file) as f:
            interventions = json.load(f)
        assert interventions[0]["action"] == "adjust_temperature"
        assert interventions[0]["component"] == "nozzle"

    @patch("src.tools.monitor_tools.OctoPrintClient")
    @pytest.mark.asyncio
    async def test_adjust_bed_temperature(self, mock_client_class, patch_projects_dir):
        """adjust_temperature with bed → calls bed_target."""
        mock_client = Mock()
        mock_octorest = Mock()
        mock_client._get_client.return_value = mock_octorest
        mock_client_class.return_value = mock_client

        result = await monitor_tools.adjust_temperature("test_project", "bed", 60.0)

        assert result["status"] == "ok"
        assert result["component"] == "bed"
        assert result["target_temp"] == 60.0
        mock_octorest.bed_target.assert_called_once_with(60.0)

        # Verify intervention logged
        interventions_file = Path(patch_projects_dir) / "test_project" / "monitoring" / "interventions.json"
        with open(interventions_file) as f:
            interventions = json.load(f)
        assert interventions[0]["action"] == "adjust_temperature"
        assert interventions[0]["component"] == "bed"

    @pytest.mark.asyncio
    async def test_adjust_temperature_invalid_component(self, patch_projects_dir):
        """adjust_temperature with invalid component → error."""
        result = await monitor_tools.adjust_temperature("test_project", "invalid", 210.0)

        assert result["status"] == "error"
        assert "must be 'nozzle' or 'bed'" in result["message"]

    @pytest.mark.asyncio
    async def test_adjust_temperature_too_low(self, patch_projects_dir):
        """adjust_temperature with temp < 0 → error."""
        result = await monitor_tools.adjust_temperature("test_project", "nozzle", -10.0)

        assert result["status"] == "error"
        assert "between 0 and 350" in result["message"]

    @pytest.mark.asyncio
    async def test_adjust_temperature_too_high(self, patch_projects_dir):
        """adjust_temperature with temp > 350 → error."""
        result = await monitor_tools.adjust_temperature("test_project", "nozzle", 400.0)

        assert result["status"] == "error"
        assert "between 0 and 350" in result["message"]

    @pytest.mark.asyncio
    async def test_adjust_temperature_invalid_temp_type(self, patch_projects_dir):
        """adjust_temperature with non-numeric temp → error."""
        result = await monitor_tools.adjust_temperature("test_project", "nozzle", "not a number")

        assert result["status"] == "error"
        assert "must be a number" in result["message"]

    @pytest.mark.asyncio
    async def test_adjust_temperature_empty_project(self):
        """adjust_temperature with empty project_name → error."""
        result = await monitor_tools.adjust_temperature("", "nozzle", 210.0)

        assert result["status"] == "error"
        assert "project_name is required" in result["message"]

    @patch("src.tools.monitor_tools.OctoPrintClient")
    @pytest.mark.asyncio
    async def test_adjust_temperature_temperature_as_int(self, mock_client_class, patch_projects_dir):
        """adjust_temperature accepts int temperature and converts to float."""
        mock_client = Mock()
        mock_octorest = Mock()
        mock_client._get_client.return_value = mock_octorest
        mock_client_class.return_value = mock_client

        result = await monitor_tools.adjust_temperature("test_project", "bed", 60)

        assert result["status"] == "ok"
        assert result["target_temp"] == 60.0

    @patch("src.tools.monitor_tools.OctoPrintClient")
    @pytest.mark.asyncio
    async def test_adjust_temperature_boundary_zero(self, mock_client_class, patch_projects_dir):
        """adjust_temperature with 0°C (boundary) → allowed."""
        mock_client = Mock()
        mock_octorest = Mock()
        mock_client._get_client.return_value = mock_octorest
        mock_client_class.return_value = mock_client

        result = await monitor_tools.adjust_temperature("test_project", "nozzle", 0.0)

        assert result["status"] == "ok"
        assert result["target_temp"] == 0.0

    @patch("src.tools.monitor_tools.OctoPrintClient")
    @pytest.mark.asyncio
    async def test_adjust_temperature_boundary_350(self, mock_client_class, patch_projects_dir):
        """adjust_temperature with 350°C (boundary) → allowed."""
        mock_client = Mock()
        mock_octorest = Mock()
        mock_client._get_client.return_value = mock_octorest
        mock_client_class.return_value = mock_client

        result = await monitor_tools.adjust_temperature("test_project", "nozzle", 350.0)

        assert result["status"] == "ok"
        assert result["target_temp"] == 350.0

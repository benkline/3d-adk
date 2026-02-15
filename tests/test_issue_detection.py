"""Integration tests for print issue detection system (TICKET-018).

Tests the end-to-end issue detection pipeline: reading metrics from JSONL,
analyzing for anomalies, and returning actionable alerts.
"""

import asyncio
import json
import os
import pytest
from pathlib import Path

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


def write_metrics(project_dir, snapshots):
    """Helper to write test metrics to JSONL file."""
    project_path = Path(project_dir) / "test_project"
    monitor_dir = project_path / "monitoring"
    monitor_dir.mkdir(parents=True, exist_ok=True)

    metrics_file = monitor_dir / "metrics.jsonl"
    with open(metrics_file, "w") as f:
        for snapshot in snapshots:
            f.write(json.dumps(snapshot) + "\n")

    return str(metrics_file)


# ============================================================================
# TEST CLASS 1: Temperature Anomaly Detection
# ============================================================================

class TestTemperatureAnomalyDetection:
    """Test temperature deviation detection."""

    @pytest.mark.asyncio
    async def test_no_issues_when_temps_normal(self, patch_projects_dir):
        """All snapshots within threshold → no issues."""
        snapshots = [
            {
                "progress": 10.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 205.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
            {
                "progress": 20.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 209.0, "target": 210.0},
                "print_time_elapsed": 600,
                "print_time_remaining": 3000,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        temp_issues = [i for i in result["issues_detected"] if i["type"] == "temperature_deviation"]
        assert len(temp_issues) == 0

    @pytest.mark.asyncio
    async def test_brief_deviation_below_duration_no_issue(self, patch_projects_dir):
        """Deviation < 30s duration → no issue."""
        snapshots = [
            {
                "progress": 10.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 200.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
            {
                "progress": 15.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 198.0, "target": 210.0},
                "print_time_elapsed": 20,  # Only 20 seconds have passed
                "print_time_remaining": 3580,
            },
            {
                "progress": 20.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 209.0, "target": 210.0},
                "print_time_elapsed": 40,  # Recovery before threshold
                "print_time_remaining": 3560,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        temp_issues = [i for i in result["issues_detected"] if i["type"] == "temperature_deviation"]
        assert len(temp_issues) == 0

    @pytest.mark.asyncio
    async def test_sustained_nozzle_deviation_triggers_warning(self, patch_projects_dir):
        """Sustained nozzle deviation > 30s → warning."""
        snapshots = [
            {
                "progress": 10.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 195.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
            {
                "progress": 15.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 194.0, "target": 210.0},
                "print_time_elapsed": 20,
                "print_time_remaining": 3580,
            },
            {
                "progress": 20.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 193.0, "target": 210.0},
                "print_time_elapsed": 40,  # Duration > 30s, threshold exceeded
                "print_time_remaining": 3560,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        temp_issues = [i for i in result["issues_detected"] if i["type"] == "temperature_deviation"]
        assert len(temp_issues) >= 1
        assert any(i["severity"] == "warning" for i in temp_issues)

    @pytest.mark.asyncio
    async def test_sustained_bed_deviation_triggers_warning(self, patch_projects_dir):
        """Sustained bed deviation > 30s → warning."""
        snapshots = [
            {
                "progress": 10.0,
                "state": "Printing",
                "bed_temp": {"current": 45.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
            {
                "progress": 15.0,
                "state": "Printing",
                "bed_temp": {"current": 44.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 20,
                "print_time_remaining": 3580,
            },
            {
                "progress": 20.0,
                "state": "Printing",
                "bed_temp": {"current": 43.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 40,
                "print_time_remaining": 3560,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        temp_issues = [i for i in result["issues_detected"] if i["type"] == "temperature_deviation"]
        assert len(temp_issues) >= 1

    @pytest.mark.asyncio
    async def test_deviation_resets_after_temp_recovers(self, patch_projects_dir):
        """Deviation followed by recovery → no issue from brief spike."""
        snapshots = [
            {
                "progress": 10.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 195.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
            {
                "progress": 15.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 209.0, "target": 210.0},
                "print_time_elapsed": 10,  # Recovery before duration threshold
                "print_time_remaining": 3590,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        temp_issues = [i for i in result["issues_detected"] if i["type"] == "temperature_deviation"]
        assert len(temp_issues) == 0


# ============================================================================
# TEST CLASS 2: Filament Stall Detection
# ============================================================================

class TestFilamentStallDetection:
    """Test filament extrusion stall detection."""

    @pytest.mark.asyncio
    async def test_no_stall_when_progress_advancing(self, patch_projects_dir):
        """Progress increasing → no stall."""
        snapshots = [
            {
                "progress": 10.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
            {
                "progress": 20.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 600,
                "print_time_remaining": 3000,
            },
            {
                "progress": 30.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 1200,
                "print_time_remaining": 2400,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        stall_issues = [i for i in result["issues_detected"] if i["type"] == "filament_jam"]
        assert len(stall_issues) == 0

    @pytest.mark.asyncio
    async def test_short_stall_below_threshold_no_issue(self, patch_projects_dir):
        """Stall < 60s → no issue."""
        snapshots = [
            {
                "progress": 20.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 600,
                "print_time_remaining": 3000,
            },
            {
                "progress": 20.0,  # No progress
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 650,  # 50 seconds passed
                "print_time_remaining": 2950,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        stall_issues = [i for i in result["issues_detected"] if i["type"] == "filament_jam"]
        assert len(stall_issues) == 0

    @pytest.mark.asyncio
    async def test_stall_while_printing_triggers_error(self, patch_projects_dir):
        """Progress frozen while printing > 60s → error."""
        snapshots = [
            {
                "progress": 25.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 900,
                "print_time_remaining": 2700,
            },
            {
                "progress": 25.0,  # No progress
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 1000,  # 100 seconds passed
                "print_time_remaining": 2600,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        stall_issues = [i for i in result["issues_detected"] if i["type"] == "filament_jam"]
        assert len(stall_issues) >= 1
        assert any(i["severity"] == "error" for i in stall_issues)

    @pytest.mark.asyncio
    async def test_no_stall_when_state_not_printing(self, patch_projects_dir):
        """Paused/idle state → no stall."""
        snapshots = [
            {
                "progress": 25.0,
                "state": "Paused",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 900,
                "print_time_remaining": 2700,
            },
            {
                "progress": 25.0,  # No progress, but not printing
                "state": "Paused",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 1000,
                "print_time_remaining": 2600,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        stall_issues = [i for i in result["issues_detected"] if i["type"] == "filament_jam"]
        assert len(stall_issues) == 0


# ============================================================================
# TEST CLASS 3: Bed Adhesion Detection
# ============================================================================

class TestBedAdhesionDetection:
    """Test bed adhesion issue detection."""

    @pytest.mark.asyncio
    async def test_normal_early_layer_no_issue(self, patch_projects_dir):
        """Stable bed temp in first 5% → no issue."""
        snapshots = [
            {
                "progress": 2.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
            {
                "progress": 5.0,
                "state": "Printing",
                "bed_temp": {"current": 59.8, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 200,
                "print_time_remaining": 3400,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        adhesion_issues = [i for i in result["issues_detected"] if i["type"] in ("bed_adhesion_risk", "early_print_failure")]
        assert len(adhesion_issues) == 0

    @pytest.mark.asyncio
    async def test_bed_temp_drop_early_layer_triggers_warning(self, patch_projects_dir):
        """Bed temp drops > 5°C early → warning."""
        snapshots = [
            {
                "progress": 3.0,
                "state": "Printing",
                "bed_temp": {"current": 54.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        adhesion_issues = [i for i in result["issues_detected"] if i["type"] == "bed_adhesion_risk"]
        assert len(adhesion_issues) >= 1

    @pytest.mark.asyncio
    async def test_early_print_failure_triggers_warning(self, patch_projects_dir):
        """State goes non-Printing at progress < 5% → warning."""
        snapshots = [
            {
                "progress": 2.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
            {
                "progress": 3.0,
                "state": "Error",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 100,
                "print_time_remaining": 3500,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        failure_issues = [i for i in result["issues_detected"] if i["type"] == "early_print_failure"]
        assert len(failure_issues) >= 1


# ============================================================================
# TEST CLASS 4: Layer Shift Detection
# ============================================================================

class TestLayerShiftDetection:
    """Test layer shift detection."""

    @pytest.mark.asyncio
    async def test_normal_progression_no_shift(self, patch_projects_dir):
        """Monotonic elapsed time → no shift."""
        snapshots = [
            {
                "progress": 10.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
            {
                "progress": 20.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 600,
                "print_time_remaining": 3000,
            },
            {
                "progress": 30.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 1200,
                "print_time_remaining": 2400,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        shift_issues = [i for i in result["issues_detected"] if i["type"] == "layer_shift"]
        assert len(shift_issues) == 0

    @pytest.mark.asyncio
    async def test_elapsed_time_reset_triggers_error(self, patch_projects_dir):
        """Print time elapsed decreases → error."""
        snapshots = [
            {
                "progress": 20.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 1200,
                "print_time_remaining": 2400,
            },
            {
                "progress": 22.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 800,  # Time went backward!
                "print_time_remaining": 2800,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        shift_issues = [i for i in result["issues_detected"] if i["type"] == "layer_shift"]
        assert len(shift_issues) >= 1
        assert any(i["severity"] == "error" for i in shift_issues)

    @pytest.mark.asyncio
    async def test_no_data_returns_no_issues(self, patch_projects_dir):
        """Single snapshot → no duration-based issues."""
        snapshots = [
            {
                "progress": 10.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        shift_issues = [i for i in result["issues_detected"] if i["type"] == "layer_shift"]
        assert len(shift_issues) == 0


# ============================================================================
# TEST CLASS 5: Integration Tests
# ============================================================================

class TestDetectPrintIssues:
    """Integration tests for detect_print_issues function."""

    @pytest.mark.asyncio
    async def test_empty_project_name_returns_error(self, patch_projects_dir):
        """Empty project name → error."""
        result = await monitor_tools.detect_print_issues("")

        assert result["status"] == "error"
        assert "required" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_missing_metrics_file_returns_ok_no_issues(self, patch_projects_dir):
        """No metrics file → ok with 0 issues."""
        result = await monitor_tools.detect_print_issues("nonexistent_project")

        assert result["status"] == "ok"
        assert result["alert_count"] == 0
        assert len(result["issues_detected"]) == 0

    @pytest.mark.asyncio
    async def test_healthy_print_no_issues_detected(self, patch_projects_dir):
        """Healthy print metrics → 0 issues."""
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
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        assert result["alert_count"] == 0
        assert len(result["issues_detected"]) == 0

    @pytest.mark.asyncio
    async def test_multiple_issues_detected_in_single_run(self, patch_projects_dir):
        """Temp issue + stall issue detected in same run."""
        snapshots = [
            {
                "progress": 10.0,
                "state": "Printing",
                "bed_temp": {"current": 45.0, "target": 60.0},  # Deviation
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
            {
                "progress": 10.0,  # No progress - stall starting
                "state": "Printing",
                "bed_temp": {"current": 44.0, "target": 60.0},  # Sustained deviation
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 40,  # > 30s for temp
                "print_time_remaining": 3560,
            },
            {
                "progress": 10.0,  # Still no progress
                "state": "Printing",
                "bed_temp": {"current": 43.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 100,  # > 60s for stall
                "print_time_remaining": 3500,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        assert result["status"] == "ok"
        assert result["alert_count"] >= 2
        issue_types = {i["type"] for i in result["issues_detected"]}
        assert "temperature_deviation" in issue_types
        assert "filament_jam" in issue_types

    @pytest.mark.asyncio
    async def test_result_structure_complete(self, patch_projects_dir):
        """Result structure has all required fields."""
        snapshots = [
            {
                "progress": 10.0,
                "state": "Printing",
                "bed_temp": {"current": 60.0, "target": 60.0},
                "nozzle_temp": {"current": 210.0, "target": 210.0},
                "print_time_elapsed": 0,
                "print_time_remaining": 3600,
            },
        ]
        write_metrics(patch_projects_dir, snapshots)

        result = await monitor_tools.detect_print_issues("test_project")

        # Verify all required fields in result
        assert "status" in result
        assert "issues_detected" in result
        assert "alert_count" in result
        assert "message" in result

        # Verify issues are properly structured
        for issue in result["issues_detected"]:
            assert "type" in issue
            assert "severity" in issue
            assert "message" in issue
            assert "detected_at" in issue
            assert "data" in issue

        # Verify severity values are valid
        valid_severities = {"warning", "error"}
        for issue in result["issues_detected"]:
            assert issue["severity"] in valid_severities

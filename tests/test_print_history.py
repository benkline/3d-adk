"""Tests for print history and analytics (TICKET-021)."""

import json
import os
import time
from pathlib import Path

import pytest

from src.tools.monitor_tools import (
    store_print_history as _store_print_history,
    query_print_history as _query_print_history,
    get_print_analytics as _get_print_analytics,
)


@pytest.fixture
def tmp_projects_dir(tmp_path):
    """Create a temporary projects directory for testing."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    return str(projects_dir)


@pytest.fixture
def patch_projects_dir(tmp_projects_dir, monkeypatch):
    """Patch PROJECTS_DIR for test isolation."""
    monkeypatch.setattr("src.tools.monitor_tools.PROJECTS_DIR", tmp_projects_dir)
    # FILAMENT_COST_PER_KG and FILAMENT_G_PER_HOUR are already set via environment in conftest
    return tmp_projects_dir


def write_summary(projects_dir: str, project_name: str, summary_data: dict):
    """Write a print summary to the project's monitoring directory."""
    monitoring_dir = Path(projects_dir) / project_name / "monitoring"
    monitoring_dir.mkdir(parents=True, exist_ok=True)
    summary_file = monitoring_dir / "print_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary_data, f)


def write_quality_assessment(projects_dir: str, project_name: str, qa_data: dict):
    """Write a quality assessment to the project's monitoring directory."""
    monitoring_dir = Path(projects_dir) / project_name / "monitoring"
    monitoring_dir.mkdir(parents=True, exist_ok=True)
    qa_file = monitoring_dir / "quality_assessment.json"
    with open(qa_file, "w") as f:
        json.dump(qa_data, f)


def write_history(projects_dir: str, records: list):
    """Write history records to the global history file."""
    projects_path = Path(projects_dir)
    projects_path.mkdir(parents=True, exist_ok=True)
    history_file = projects_path / "print_history.json"
    with open(history_file, "w") as f:
        json.dump(records, f)


# ============================================================================
# TEST STORE_PRINT_HISTORY
# ============================================================================


class TestStorePrintHistory:
    """Tests for store_print_history function."""

    @pytest.mark.asyncio
    async def test_store_print_history_success(self, patch_projects_dir):
        """Test successful storage of print history."""
        project_name = "test_project"
        summary = {
            "project_name": project_name,
            "generated_at": "2024-01-01T12:00:00Z",
            "metrics": {
                "total_snapshots": 10,
                "total_print_time_s": 3600,  # 1 hour
                "avg_nozzle_temp_c": 210.0,
                "max_nozzle_temp_c": 212.5,
                "avg_bed_temp_c": 60.0,
                "max_bed_temp_c": 61.0,
            },
            "alerts_count": 1,
            "interventions_count": 0,
        }
        qa = {
            "assessment_id": "qa_1",
            "overall_quality": "good",
            "issues_encountered": "Minor stringing",
            "user_notes": "Good print",
            "photo_path": "",
        }

        write_summary(patch_projects_dir, project_name, summary)
        write_quality_assessment(patch_projects_dir, project_name, qa)

        result = await _store_print_history(project_name)

        assert result["status"] == "ok"
        assert "history_id" in result
        assert "message" in result

        # Verify history file was created
        history_file = Path(patch_projects_dir) / "print_history.json"
        assert history_file.exists()

        # Verify record was added
        with open(history_file) as f:
            history = json.load(f)
        assert len(history) == 1
        assert history[0]["project_name"] == project_name
        assert history[0]["quality"] == "good"
        assert history[0]["print_time_s"] == 3600
        assert history[0]["material_g"] == 8.0  # 1 hour * 8.0 g/hour

    @pytest.mark.asyncio
    async def test_store_print_history_material_cost_calculation(self, patch_projects_dir):
        """Test that material cost is calculated correctly."""
        project_name = "test_project"
        summary = {
            "project_name": project_name,
            "generated_at": "2024-01-01T12:00:00Z",
            "metrics": {
                "total_snapshots": 10,
                "total_print_time_s": 7200,  # 2 hours = 16g at 8g/hour
                "avg_nozzle_temp_c": 210.0,
                "max_nozzle_temp_c": 212.5,
                "avg_bed_temp_c": 60.0,
                "max_bed_temp_c": 61.0,
            },
            "alerts_count": 0,
            "interventions_count": 0,
        }
        qa = {
            "assessment_id": "qa_1",
            "overall_quality": "excellent",
        }

        write_summary(patch_projects_dir, project_name, summary)
        write_quality_assessment(patch_projects_dir, project_name, qa)

        result = await _store_print_history(project_name)

        assert result["status"] == "ok"

        history_file = Path(patch_projects_dir) / "print_history.json"
        with open(history_file) as f:
            history = json.load(f)
        record = history[0]

        assert record["material_g"] == 16.0  # 2 hours * 8.0 g/hour
        assert record["material_cost_usd"] == 0.4  # (16.0 / 1000) * 25.0

    @pytest.mark.asyncio
    async def test_store_print_history_empty_project_name(self, patch_projects_dir):
        """Test that empty project_name returns error."""
        result = await _store_print_history("")
        assert result["status"] == "error"
        assert "project_name is required" in result["message"]

    @pytest.mark.asyncio
    async def test_store_print_history_missing_summary(self, patch_projects_dir):
        """Test that missing print summary returns error."""
        project_name = "test_project"
        result = await _store_print_history(project_name)
        assert result["status"] == "error"
        assert "No print summary found" in result["message"]

    @pytest.mark.asyncio
    async def test_store_print_history_multiple_records(self, patch_projects_dir):
        """Test appending multiple records to history."""
        summary = {
            "project_name": "project1",
            "generated_at": "2024-01-01T12:00:00Z",
            "metrics": {"total_print_time_s": 3600},
            "alerts_count": 0,
            "interventions_count": 0,
        }
        qa = {"overall_quality": "good"}

        # Store first record
        write_summary(patch_projects_dir, "project1", summary)
        write_quality_assessment(patch_projects_dir, "project1", qa)
        result1 = await _store_print_history("project1")
        assert result1["status"] == "ok"

        # Store second record
        write_summary(patch_projects_dir, "project2", summary)
        write_quality_assessment(patch_projects_dir, "project2", qa)
        result2 = await _store_print_history("project2")
        assert result2["status"] == "ok"

        # Verify both records are in history
        history_file = Path(patch_projects_dir) / "print_history.json"
        with open(history_file) as f:
            history = json.load(f)
        assert len(history) == 2
        assert history[0]["project_name"] == "project1"
        assert history[1]["project_name"] == "project2"


# ============================================================================
# TEST QUERY_PRINT_HISTORY
# ============================================================================


class TestQueryPrintHistory:
    """Tests for query_print_history function."""

    @pytest.mark.asyncio
    async def test_query_empty_history(self, patch_projects_dir):
        """Test querying empty history returns empty list."""
        result = await _query_print_history()
        assert result["status"] == "ok"
        assert result["total_count"] == 0
        assert result["records"] == []

    @pytest.mark.asyncio
    async def test_query_filter_by_project(self, patch_projects_dir):
        """Test filtering history by project_name."""
        records = [
            {
                "history_id": "h1",
                "recorded_at": "2024-01-01T12:00:00Z",
                "project_name": "project1",
                "quality": "good",
                "print_time_s": 3600,
            },
            {
                "history_id": "h2",
                "recorded_at": "2024-01-02T12:00:00Z",
                "project_name": "project2",
                "quality": "excellent",
                "print_time_s": 1800,
            },
        ]
        write_history(patch_projects_dir, records)

        result = await _query_print_history(project_name="project1")

        assert result["status"] == "ok"
        assert result["total_count"] == 1
        assert result["records"][0]["project_name"] == "project1"

    @pytest.mark.asyncio
    async def test_query_filter_by_date_range(self, patch_projects_dir):
        """Test filtering history by date range."""
        records = [
            {
                "history_id": "h1",
                "recorded_at": "2024-01-01T12:00:00Z",
                "project_name": "p1",
                "quality": "good",
            },
            {
                "history_id": "h2",
                "recorded_at": "2024-01-05T12:00:00Z",
                "project_name": "p1",
                "quality": "good",
            },
            {
                "history_id": "h3",
                "recorded_at": "2024-01-10T12:00:00Z",
                "project_name": "p1",
                "quality": "good",
            },
        ]
        write_history(patch_projects_dir, records)

        result = await _query_print_history(start_date="2024-01-05", end_date="2024-01-08")

        assert result["status"] == "ok"
        assert result["total_count"] == 1
        assert result["records"][0]["recorded_at"] == "2024-01-05T12:00:00Z"

    @pytest.mark.asyncio
    async def test_query_filter_by_quality(self, patch_projects_dir):
        """Test filtering history by quality level."""
        records = [
            {"history_id": "h1", "recorded_at": "2024-01-01T12:00:00Z", "project_name": "p", "quality": "excellent"},
            {"history_id": "h2", "recorded_at": "2024-01-02T12:00:00Z", "project_name": "p", "quality": "good"},
            {"history_id": "h3", "recorded_at": "2024-01-03T12:00:00Z", "project_name": "p", "quality": "poor"},
        ]
        write_history(patch_projects_dir, records)

        result = await _query_print_history(quality_filter="excellent")

        assert result["status"] == "ok"
        assert result["total_count"] == 1
        assert result["records"][0]["quality"] == "excellent"

    @pytest.mark.asyncio
    async def test_query_invalid_quality_filter(self, patch_projects_dir):
        """Test that invalid quality_filter returns error."""
        records = [
            {"history_id": "h1", "recorded_at": "2024-01-01T12:00:00Z", "project_name": "p", "quality": "good"},
        ]
        write_history(patch_projects_dir, records)

        result = await _query_print_history(quality_filter="invalid")

        assert result["status"] == "error"
        assert "quality_filter must be one of" in result["message"]


# ============================================================================
# TEST GET_PRINT_ANALYTICS
# ============================================================================


class TestGetPrintAnalytics:
    """Tests for get_print_analytics function."""

    @pytest.mark.asyncio
    async def test_analytics_empty_history(self, patch_projects_dir):
        """Test analytics on empty history returns zeros."""
        result = await _get_print_analytics()

        assert result["status"] == "ok"
        analytics = result["analytics"]
        assert analytics["total_prints"] == 0
        assert analytics["success_rate_pct"] == 0.0
        assert analytics["avg_print_time_s"] == 0.0
        assert analytics["total_material_g"] == 0.0
        assert analytics["total_material_cost_usd"] == 0.0
        assert analytics["avg_cost_per_print_usd"] == 0.0
        assert analytics["quality_distribution"] == {}

    @pytest.mark.asyncio
    async def test_analytics_success_rate(self, patch_projects_dir):
        """Test that success_rate is calculated correctly (excellent + good)."""
        # Use days=0 to get all records (not just last 30 days)
        records = [
            {"history_id": "h1", "recorded_at": "2024-01-01T12:00:00Z", "project_name": "p", "quality": "excellent", "print_time_s": 3600, "material_g": 8.0, "material_cost_usd": 0.2},
            {"history_id": "h2", "recorded_at": "2024-01-02T12:00:00Z", "project_name": "p", "quality": "good", "print_time_s": 3600, "material_g": 8.0, "material_cost_usd": 0.2},
            {"history_id": "h3", "recorded_at": "2024-01-03T12:00:00Z", "project_name": "p", "quality": "acceptable", "print_time_s": 3600, "material_g": 8.0, "material_cost_usd": 0.2},
            {"history_id": "h4", "recorded_at": "2024-01-04T12:00:00Z", "project_name": "p", "quality": "poor", "print_time_s": 3600, "material_g": 8.0, "material_cost_usd": 0.2},
        ]
        write_history(patch_projects_dir, records)

        result = await _get_print_analytics(days=0)

        assert result["status"] == "ok"
        analytics = result["analytics"]
        assert analytics["total_prints"] == 4
        # 2 excellent/good out of 4 = 50%
        assert analytics["success_rate_pct"] == 50.0
        assert analytics["quality_distribution"]["excellent"] == 1
        assert analytics["quality_distribution"]["good"] == 1
        assert analytics["quality_distribution"]["acceptable"] == 1
        assert analytics["quality_distribution"]["poor"] == 1

    @pytest.mark.asyncio
    async def test_analytics_material_and_cost(self, patch_projects_dir):
        """Test that material usage and cost are aggregated correctly."""
        records = [
            {"history_id": "h1", "recorded_at": "2024-01-01T12:00:00Z", "project_name": "p", "quality": "good", "print_time_s": 3600, "material_g": 8.0, "material_cost_usd": 0.2},
            {"history_id": "h2", "recorded_at": "2024-01-02T12:00:00Z", "project_name": "p", "quality": "good", "print_time_s": 7200, "material_g": 16.0, "material_cost_usd": 0.4},
        ]
        write_history(patch_projects_dir, records)

        result = await _get_print_analytics(days=0)

        assert result["status"] == "ok"
        analytics = result["analytics"]
        assert analytics["total_prints"] == 2
        assert analytics["avg_print_time_s"] == 5400.0  # (3600 + 7200) / 2
        assert analytics["total_material_g"] == 24.0  # 8 + 16
        assert analytics["total_material_cost_usd"] == 0.6  # 0.2 + 0.4
        assert analytics["avg_cost_per_print_usd"] == 0.3  # 0.6 / 2

    @pytest.mark.asyncio
    async def test_analytics_filter_by_project(self, patch_projects_dir):
        """Test analytics filtering by project_name."""
        records = [
            {"history_id": "h1", "recorded_at": "2024-01-01T12:00:00Z", "project_name": "project1", "quality": "good", "print_time_s": 3600, "material_g": 8.0, "material_cost_usd": 0.2},
            {"history_id": "h2", "recorded_at": "2024-01-02T12:00:00Z", "project_name": "project2", "quality": "excellent", "print_time_s": 1800, "material_g": 4.0, "material_cost_usd": 0.1},
        ]
        write_history(patch_projects_dir, records)

        result = await _get_print_analytics(project_name="project1", days=0)

        assert result["status"] == "ok"
        analytics = result["analytics"]
        assert analytics["total_prints"] == 1
        assert analytics["avg_print_time_s"] == 3600.0

    @pytest.mark.asyncio
    async def test_analytics_invalid_days(self, patch_projects_dir):
        """Test that invalid days parameter returns error."""
        result = await _get_print_analytics(days=-1)
        assert result["status"] == "error"
        assert "days must be a non-negative integer" in result["message"]

    @pytest.mark.asyncio
    async def test_analytics_days_filter(self, patch_projects_dir):
        """Test analytics filtering by days (now - days)."""
        # Create records with old and recent dates
        now = time.time()
        old_date = now - 40 * 86400  # 40 days ago
        recent_date = now - 10 * 86400  # 10 days ago

        old_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(old_date))
        recent_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(recent_date))

        records = [
            {"history_id": "h1", "recorded_at": old_iso, "project_name": "p", "quality": "good", "print_time_s": 3600, "material_g": 8.0, "material_cost_usd": 0.2},
            {"history_id": "h2", "recorded_at": recent_iso, "project_name": "p", "quality": "good", "print_time_s": 3600, "material_g": 8.0, "material_cost_usd": 0.2},
        ]
        write_history(patch_projects_dir, records)

        # Query last 30 days (should only get recent_date)
        result = await _get_print_analytics(days=30)

        assert result["status"] == "ok"
        analytics = result["analytics"]
        assert analytics["total_prints"] == 1

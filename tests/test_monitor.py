"""Comprehensive test suite for Monitor Agent and tools (TICKET-016, TICKET-017)."""

import json
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

os.environ["ANTHROPIC_API_KEY"] = "test_key"

import src.tools.monitor_tools as monitor_tools
from src.agents.monitor import monitor_agent


class TestMonitorAgent:
    """Test monitor agent structure and configuration."""

    def test_monitor_agent_name(self):
        """Test agent has correct name."""
        assert monitor_agent.name == "monitor_phase_agent"

    def test_monitor_agent_has_four_tools(self):
        """Test agent has exactly four tools."""
        assert len(monitor_agent.tools) == 4

    def test_monitor_agent_tool_names(self):
        """Test agent has all required tools."""
        tool_names = {tool.func.__name__ for tool in monitor_agent.tools}
        expected = {"connect_to_printer", "get_print_status", "collect_metrics", "get_print_summary"}
        assert tool_names == expected

    def test_monitor_agent_model(self):
        """Test agent uses correct model."""
        from src.config import LLM_MODEL
        assert monitor_agent.model == LLM_MODEL


class TestConnectToPrinter:
    """Test OctoPrint connection validation (TICKET-016)."""

    @pytest.mark.asyncio
    async def test_connect_to_printer_empty_project_name(self):
        """Test with empty project name."""
        result = await monitor_tools.connect_to_printer("")
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "project_name" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_connect_to_printer_no_api_key(self):
        """Test when API key is not set."""
        original_key = monitor_tools.OCTOPRINT_API_KEY
        monitor_tools.OCTOPRINT_API_KEY = None

        try:
            result = await monitor_tools.connect_to_printer("test_project")
            assert result["status"] == "error"
            assert "api_key" in result["message"].lower()
        finally:
            monitor_tools.OCTOPRINT_API_KEY = original_key

    @pytest.mark.asyncio
    async def test_connect_to_printer_unreachable(self):
        """Test connection error when OctoPrint is unreachable."""
        original_key = monitor_tools.OCTOPRINT_API_KEY
        original_host = monitor_tools.OCTOPRINT_HOST
        monitor_tools.OCTOPRINT_API_KEY = "valid_key"
        monitor_tools.OCTOPRINT_HOST = "nonexistent.invalid.example"

        try:
            result = await monitor_tools.connect_to_printer("test_project")
            assert result["status"] == "pending"
            assert "cannot reach" in result["message"].lower()
        finally:
            monitor_tools.OCTOPRINT_API_KEY = original_key
            monitor_tools.OCTOPRINT_HOST = original_host

    @pytest.mark.asyncio
    async def test_connect_to_printer_success(self):
        """Test successful connection with mocked HTTP session."""
        original_key = monitor_tools.OCTOPRINT_API_KEY
        monitor_tools.OCTOPRINT_API_KEY = "valid_key"

        # Mock HTTP session
        mock_session = Mock()
        mock_version_response = Mock()
        mock_version_response.status_code = 200
        mock_version_response.json.return_value = {"api": "0.1", "server": "1.9.3"}

        mock_printer_response = Mock()
        mock_printer_response.status_code = 200
        mock_printer_response.json.return_value = {
            "state": {"operational": True, "printing": False}
        }

        mock_session.get.side_effect = [mock_version_response, mock_printer_response]

        original_get_session = monitor_tools._get_http_session
        monitor_tools._get_http_session = lambda: mock_session

        try:
            result = await monitor_tools.connect_to_printer("test_project")
            assert result["status"] == "ok"
            assert "octoprint_version" in result
            assert result["printer_connected"] is True
        finally:
            monitor_tools.OCTOPRINT_API_KEY = original_key
            monitor_tools._get_http_session = original_get_session

    @pytest.mark.asyncio
    async def test_connect_to_printer_auth_failed(self):
        """Test authentication failure (401 response)."""
        original_key = monitor_tools.OCTOPRINT_API_KEY
        monitor_tools.OCTOPRINT_API_KEY = "invalid_key"

        # Mock HTTP session with 401 response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 401

        mock_session.get.return_value = mock_response

        original_get_session = monitor_tools._get_http_session
        monitor_tools._get_http_session = lambda: mock_session

        try:
            result = await monitor_tools.connect_to_printer("test_project")
            assert result["status"] == "error"
            assert "authentication" in result["message"].lower()
        finally:
            monitor_tools.OCTOPRINT_API_KEY = original_key
            monitor_tools._get_http_session = original_get_session


class TestGetPrintStatus:
    """Test real-time print status monitoring (TICKET-016/017)."""

    @pytest.mark.asyncio
    async def test_get_print_status_empty_project_name(self):
        """Test with empty project name."""
        result = await monitor_tools.get_print_status("")
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "project_name" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_get_print_status_no_api_key(self):
        """Test when API key is not set."""
        original_key = monitor_tools.OCTOPRINT_API_KEY
        monitor_tools.OCTOPRINT_API_KEY = None

        try:
            result = await monitor_tools.get_print_status("test_project")
            assert result["status"] == "error"
            assert "api_key" in result["message"].lower()
        finally:
            monitor_tools.OCTOPRINT_API_KEY = original_key

    @pytest.mark.asyncio
    async def test_get_print_status_unreachable(self):
        """Test when OctoPrint is unreachable."""
        original_key = monitor_tools.OCTOPRINT_API_KEY
        original_host = monitor_tools.OCTOPRINT_HOST
        monitor_tools.OCTOPRINT_API_KEY = "valid_key"
        monitor_tools.OCTOPRINT_HOST = "nonexistent.invalid.example"

        try:
            result = await monitor_tools.get_print_status("test_project")
            assert result["status"] == "pending"
            assert "cannot reach" in result["message"].lower()
        finally:
            monitor_tools.OCTOPRINT_API_KEY = original_key
            monitor_tools.OCTOPRINT_HOST = original_host

    @pytest.mark.asyncio
    async def test_get_print_status_idle_printer(self):
        """Test status of idle printer with no active print."""
        original_key = monitor_tools.OCTOPRINT_API_KEY
        monitor_tools.OCTOPRINT_API_KEY = "valid_key"

        # Mock HTTP session for idle state
        mock_session = Mock()

        mock_printer_response = Mock()
        mock_printer_response.status_code = 200
        mock_printer_response.json.return_value = {
            "state": {"operational": True, "printing": False},
            "bed": {"actual": 25.0, "target": 0},
            "tool0": {"actual": 22.0, "target": 0},
        }

        mock_job_response = Mock()
        mock_job_response.status_code = 200
        mock_job_response.json.return_value = {
            "state": "Idle",
            "progress": {"completion": None, "printTime": None, "printTimeLeft": None},
        }

        mock_session.get.side_effect = [mock_printer_response, mock_job_response]

        original_get_session = monitor_tools._get_http_session
        monitor_tools._get_http_session = lambda: mock_session

        try:
            result = await monitor_tools.get_print_status("test_project")
            assert result["status"] == "ok"
            assert result["state"] == "Idle"
            assert result["progress"] is None
            assert "timestamp" in result
        finally:
            monitor_tools.OCTOPRINT_API_KEY = original_key
            monitor_tools._get_http_session = original_get_session

    @pytest.mark.asyncio
    async def test_get_print_status_active_print(self):
        """Test status during active print."""
        original_key = monitor_tools.OCTOPRINT_API_KEY
        monitor_tools.OCTOPRINT_API_KEY = "valid_key"

        # Mock HTTP session for active print
        mock_session = Mock()

        mock_printer_response = Mock()
        mock_printer_response.status_code = 200
        mock_printer_response.json.return_value = {
            "state": {"operational": True, "printing": True},
            "bed": {"actual": 60.0, "target": 60},
            "tool0": {"actual": 205.0, "target": 210},
        }

        mock_job_response = Mock()
        mock_job_response.status_code = 200
        mock_job_response.json.return_value = {
            "state": "Printing",
            "progress": {
                "completion": 45.2,
                "printTime": 3600,
                "printTimeLeft": 4400,
            },
        }

        mock_session.get.side_effect = [mock_printer_response, mock_job_response]

        original_get_session = monitor_tools._get_http_session
        monitor_tools._get_http_session = lambda: mock_session

        try:
            result = await monitor_tools.get_print_status("test_project")
            assert result["status"] == "ok"
            assert result["state"] == "Printing"
            assert result["progress"] == 45.2
            assert result["print_time_elapsed"] == 3600
            assert result["print_time_remaining"] == 4400
            assert result["bed_temp"]["current"] == 60.0
            assert result["nozzle_temp"]["current"] == 205.0
        finally:
            monitor_tools.OCTOPRINT_API_KEY = original_key
            monitor_tools._get_http_session = original_get_session


class TestCollectMetrics:
    """Test metric collection (TICKET-017)."""

    @pytest.mark.asyncio
    async def test_collect_metrics_empty_project_name(self):
        """Test with empty project name."""
        result = await monitor_tools.collect_metrics("", 1)
        assert result["status"] == "error"
        assert "project_name" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_collect_metrics_invalid_poll_count_zero(self):
        """Test with poll_count = 0."""
        result = await monitor_tools.collect_metrics("test_project", 0)
        assert result["status"] == "error"
        assert "poll_count" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_collect_metrics_invalid_poll_count_too_high(self):
        """Test with poll_count > 60."""
        result = await monitor_tools.collect_metrics("test_project", 61)
        assert result["status"] == "error"
        assert "poll_count" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_collect_metrics_invalid_poll_count_type(self):
        """Test with non-integer poll_count."""
        result = await monitor_tools.collect_metrics("test_project", "not_int")
        assert result["status"] == "error"
        assert "poll_count" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_collect_metrics_single_snapshot(self):
        """Test collecting a single metric snapshot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = monitor_tools.PROJECTS_DIR
            original_key = monitor_tools.OCTOPRINT_API_KEY
            monitor_tools.PROJECTS_DIR = tmpdir
            monitor_tools.OCTOPRINT_API_KEY = "valid_key"

            # Mock HTTP session for one snapshot
            mock_session = Mock()
            mock_printer_response = Mock()
            mock_printer_response.status_code = 200
            mock_printer_response.json.return_value = {
                "state": {"operational": True},
                "bed": {"actual": 60.0, "target": 60},
                "tool0": {"actual": 205.0, "target": 210},
            }

            mock_job_response = Mock()
            mock_job_response.status_code = 200
            mock_job_response.json.return_value = {
                "state": "Printing",
                "progress": {"completion": 25.0, "printTime": 1800, "printTimeLeft": 5400},
            }

            mock_session.get.side_effect = [mock_printer_response, mock_job_response]

            original_get_session = monitor_tools._get_http_session
            monitor_tools._get_http_session = lambda: mock_session

            try:
                result = await monitor_tools.collect_metrics("test_project", 1)
                assert result["status"] == "ok"
                assert result["snapshots_collected"] == 1
                assert "metrics.jsonl" in result["metrics_file"]

                # Verify metrics file was created
                metrics_file = monitor_tools._get_monitor_dir("test_project") / "metrics.jsonl"
                assert metrics_file.exists()

                # Verify metrics file content
                with open(metrics_file, "r") as f:
                    line = f.readline()
                    snapshot = json.loads(line)
                    assert snapshot["progress"] == 25.0
                    assert snapshot["state"] == "Printing"
            finally:
                monitor_tools.PROJECTS_DIR = original_dir
                monitor_tools.OCTOPRINT_API_KEY = original_key
                monitor_tools._get_http_session = original_get_session

    @pytest.mark.asyncio
    async def test_collect_metrics_multiple_snapshots(self):
        """Test collecting multiple metric snapshots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = monitor_tools.PROJECTS_DIR
            original_key = monitor_tools.OCTOPRINT_API_KEY
            monitor_tools.PROJECTS_DIR = tmpdir
            monitor_tools.OCTOPRINT_API_KEY = "valid_key"

            # Mock HTTP session for multiple snapshots
            mock_session = Mock()
            mock_printer_response = Mock()
            mock_printer_response.status_code = 200
            mock_printer_response.json.return_value = {
                "state": {"operational": True},
                "bed": {"actual": 60.0, "target": 60},
                "tool0": {"actual": 205.0, "target": 210},
            }

            mock_job_response = Mock()
            mock_job_response.status_code = 200
            mock_job_response.json.return_value = {
                "state": "Printing",
                "progress": {"completion": 30.0, "printTime": 2000, "printTimeLeft": 5000},
            }

            # Need to return responses multiple times
            mock_session.get.side_effect = (
                [mock_printer_response, mock_job_response] * 3  # 3 snapshots
            )

            original_get_session = monitor_tools._get_http_session
            monitor_tools._get_http_session = lambda: mock_session

            try:
                result = await monitor_tools.collect_metrics("test_project", 3)
                assert result["status"] == "ok"
                assert result["snapshots_collected"] == 3

                # Verify metrics file has 3 lines
                metrics_file = monitor_tools._get_monitor_dir("test_project") / "metrics.jsonl"
                with open(metrics_file, "r") as f:
                    lines = [line for line in f if line.strip()]
                    assert len(lines) == 3
            finally:
                monitor_tools.PROJECTS_DIR = original_dir
                monitor_tools.OCTOPRINT_API_KEY = original_key
                monitor_tools._get_http_session = original_get_session

    @pytest.mark.asyncio
    async def test_collect_metrics_unreachable(self):
        """Test collecting when OctoPrint is unreachable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = monitor_tools.PROJECTS_DIR
            original_host = monitor_tools.OCTOPRINT_HOST
            original_key = monitor_tools.OCTOPRINT_API_KEY
            monitor_tools.PROJECTS_DIR = tmpdir
            monitor_tools.OCTOPRINT_HOST = "nonexistent.invalid.example"
            monitor_tools.OCTOPRINT_API_KEY = "valid_key"

            try:
                result = await monitor_tools.collect_metrics("test_project", 1)
                assert result["status"] == "pending"
                assert result["snapshots_collected"] == 0
            finally:
                monitor_tools.PROJECTS_DIR = original_dir
                monitor_tools.OCTOPRINT_HOST = original_host
                monitor_tools.OCTOPRINT_API_KEY = original_key


class TestGetPrintSummary:
    """Test summary generation from metrics (TICKET-017)."""

    @pytest.mark.asyncio
    async def test_get_print_summary_empty_project_name(self):
        """Test with empty project name."""
        result = await monitor_tools.get_print_summary("")
        assert result["status"] == "error"
        assert "project_name" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_get_print_summary_no_metrics(self):
        """Test summary when no metrics have been collected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = monitor_tools.PROJECTS_DIR
            monitor_tools.PROJECTS_DIR = tmpdir

            try:
                result = await monitor_tools.get_print_summary("test_project")
                assert result["status"] == "ok"
                assert result["snapshot_count"] == 0
                assert result["summary"]["avg_progress"] is None
                assert result["summary"]["min_bed_temp"] is None
            finally:
                monitor_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_get_print_summary_with_metrics(self):
        """Test summary generation with collected metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = monitor_tools.PROJECTS_DIR
            monitor_tools.PROJECTS_DIR = tmpdir

            try:
                # Create metrics manually
                monitor_dir = monitor_tools._get_monitor_dir("test_project")
                metrics_file = monitor_dir / "metrics.jsonl"

                metrics = [
                    {
                        "progress": 20.0,
                        "bed_temp": {"current": 58.0, "target": 60},
                        "nozzle_temp": {"current": 203.0, "target": 210},
                        "print_time_elapsed": 1000,
                        "print_time_remaining": 4000,
                    },
                    {
                        "progress": 30.0,
                        "bed_temp": {"current": 60.0, "target": 60},
                        "nozzle_temp": {"current": 205.0, "target": 210},
                        "print_time_elapsed": 2000,
                        "print_time_remaining": 3500,
                    },
                    {
                        "progress": 40.0,
                        "bed_temp": {"current": 60.0, "target": 60},
                        "nozzle_temp": {"current": 207.0, "target": 210},
                        "print_time_elapsed": 3000,
                        "print_time_remaining": 3000,
                    },
                ]

                with open(metrics_file, "w") as f:
                    for metric in metrics:
                        f.write(json.dumps(metric) + "\n")

                result = await monitor_tools.get_print_summary("test_project")
                assert result["status"] == "ok"
                assert result["snapshot_count"] == 3
                assert result["summary"]["avg_progress"] == 30.0  # (20+30+40)/3
                assert result["summary"]["min_bed_temp"] == 58.0
                assert result["summary"]["max_bed_temp"] == 60.0
                assert result["summary"]["min_nozzle_temp"] == 203.0
                assert result["summary"]["max_nozzle_temp"] == 207.0
                assert result["summary"]["total_print_time"] == 3000  # max elapsed
                assert result["summary"]["estimated_remaining"] == 3000  # last remaining
            finally:
                monitor_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_get_print_summary_partial_metrics(self):
        """Test summary with some metrics missing values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = monitor_tools.PROJECTS_DIR
            monitor_tools.PROJECTS_DIR = tmpdir

            try:
                monitor_dir = monitor_tools._get_monitor_dir("test_project")
                metrics_file = monitor_dir / "metrics.jsonl"

                metrics = [
                    {
                        "progress": 20.0,
                        "bed_temp": {"current": 60.0},
                        "nozzle_temp": {"current": 205.0},
                        "print_time_elapsed": None,
                        "print_time_remaining": None,
                    },
                    {
                        "progress": None,
                        "bed_temp": {"current": 60.0},
                        "nozzle_temp": {"current": 205.0},
                        "print_time_elapsed": 2000,
                        "print_time_remaining": 2000,
                    },
                ]

                with open(metrics_file, "w") as f:
                    for metric in metrics:
                        f.write(json.dumps(metric) + "\n")

                result = await monitor_tools.get_print_summary("test_project")
                assert result["status"] == "ok"
                assert result["snapshot_count"] == 2
                # avg_progress should only average the non-None values
                assert result["summary"]["avg_progress"] == 20.0
                assert result["summary"]["total_print_time"] == 2000
            finally:
                monitor_tools.PROJECTS_DIR = original_dir

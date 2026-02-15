"""Tests for monitor_tools OctoPrint API integration."""

import pytest
import importlib
from unittest.mock import MagicMock, patch

# Import config before patching
import src.config
import src.tools.monitor_tools


@pytest.fixture
def mock_config(monkeypatch):
    """Mock OctoPrint configuration."""
    monkeypatch.setattr(src.config, "OCTOPRINT_HOST", "localhost")
    monkeypatch.setattr(src.config, "OCTOPRINT_PORT", "5000")
    monkeypatch.setattr(src.config, "OCTOPRINT_API_KEY", "test-api-key")

    # Reload monitor_tools to pick up patched config
    importlib.reload(src.tools.monitor_tools)

    return {
        "host": "localhost",
        "port": "5000",
        "api_key": "test-api-key",
    }


@pytest.fixture(autouse=True)
def reset_imports(mock_config):
    """Reset imports between tests."""
    yield
    importlib.reload(src.tools.monitor_tools)


# Import functions after fixtures are set up (prefix with _ to avoid pytest collection)
from src.tools.monitor_tools import (
    OctoPrintClient,
    test_connection as _test_connection,
    get_printer_status as _get_printer_status,
    get_job_status as _get_job_status,
)


class TestOctoPrintClient:
    """Test OctoPrintClient class."""

    def test_client_initialization(self):
        """Client should initialize with valid parameters."""
        client = OctoPrintClient("localhost", 5000, "api-key")
        assert client.host == "localhost"
        assert client.port == 5000
        assert client.api_key == "api-key"

    def test_client_rejects_invalid_host(self):
        """Client should reject empty host."""
        with pytest.raises(ValueError, match="host must be a non-empty string"):
            OctoPrintClient("", 5000, "api-key")

    def test_client_rejects_invalid_port(self):
        """Client should reject invalid port."""
        with pytest.raises(ValueError, match="port must be an integer"):
            OctoPrintClient("localhost", -1, "api-key")

    def test_client_rejects_invalid_api_key(self):
        """Client should reject empty API key."""
        with pytest.raises(ValueError, match="api_key must be a non-empty string"):
            OctoPrintClient("localhost", 5000, "")

    @patch("src.tools.monitor_tools.OctoRest")
    def test_client_test_connection_success(self, mock_octorest):
        """test_connection should return success dict on valid connection."""
        # Mock the OctoRest client
        mock_client = MagicMock()
        mock_octorest.return_value = mock_client
        mock_client.get_version.return_value = {
            "server": "1.8.7",
            "api": "0.1",
        }

        client = OctoPrintClient("localhost", 5000, "api-key")
        result = client.test_connection()

        assert result["status"] == "ok"
        assert result["server_version"] == "1.8.7"
        assert result["api_version"] == "0.1"
        assert "message" in result

    @patch("src.tools.monitor_tools.OctoRest")
    def test_client_test_connection_failure(self, mock_octorest):
        """test_connection should handle connection errors."""
        mock_octorest.side_effect = Exception("Connection refused")

        client = OctoPrintClient("localhost", 5000, "bad-key")
        result = client.test_connection()

        assert result["status"] == "error"
        assert "message" in result

    @patch("src.tools.monitor_tools.OctoRest")
    def test_client_get_printer_status_success(self, mock_octorest):
        """get_printer_status should return printer state and temps."""
        mock_client = MagicMock()
        mock_octorest.return_value = mock_client
        mock_client.get_printer.return_value = {
            "state": {"text": "Operational"},
            "temperature": {
                "bed": {"actual": 25.5, "target": 60},
                "tool0": {"actual": 20.0, "target": 210},
            },
        }

        client = OctoPrintClient("localhost", 5000, "api-key")
        result = client.get_printer_status()

        assert result["status"] == "ok"
        assert result["state"] == "Operational"
        assert result["bed_temp"]["current"] == 25.5
        assert result["bed_temp"]["target"] == 60
        assert result["nozzle_temp"]["current"] == 20.0
        assert result["nozzle_temp"]["target"] == 210

    @patch("src.tools.monitor_tools.OctoRest")
    def test_client_get_printer_status_no_temps(self, mock_octorest):
        """get_printer_status should handle missing temperature data."""
        mock_client = MagicMock()
        mock_octorest.return_value = mock_client
        mock_client.get_printer.return_value = {
            "state": {"text": "Offline"},
            "temperature": {},
        }

        client = OctoPrintClient("localhost", 5000, "api-key")
        result = client.get_printer_status()

        assert result["status"] == "ok"
        assert result["state"] == "Offline"
        assert result["bed_temp"] is None
        assert result["nozzle_temp"] is None

    @patch("src.tools.monitor_tools.OctoRest")
    def test_client_get_job_status_printing(self, mock_octorest):
        """get_job_status should return active job information."""
        mock_client = MagicMock()
        mock_octorest.return_value = mock_client
        mock_client.get_job.return_value = {
            "state": "Printing",
            "progress": {
                "completion": 45.5,
                "filepos": 123456,
                "printtime": 1800,
                "printtimeLeft": 2200,
            },
            "file": {"name": "phone_stand.gcode"},
        }

        client = OctoPrintClient("localhost", 5000, "api-key")
        result = client.get_job_status()

        assert result["status"] == "ok"
        assert result["state"] == "Printing"
        assert result["progress"]["completion"] == 45.5
        assert result["filename"] == "phone_stand.gcode"

    @patch("src.tools.monitor_tools.OctoRest")
    def test_client_get_job_status_idle(self, mock_octorest):
        """get_job_status should handle no active job."""
        mock_client = MagicMock()
        mock_octorest.return_value = mock_client
        mock_client.get_job.return_value = {
            "state": None,
            "progress": None,
            "file": None,
        }

        client = OctoPrintClient("localhost", 5000, "api-key")
        result = client.get_job_status()

        assert result["status"] == "ok"
        assert result["state"] is None
        assert result["progress"] is None
        assert result["filename"] is None


class TestConnectionTool:
    """Test test_connection function."""

    def test_test_connection_invalid_host_type(self):
        """test_connection should reject non-string host."""
        result = _test_connection(host=123, port="5000", api_key="key")
        assert result["status"] == "error"
        assert "string" in result["message"].lower()

    def test_test_connection_invalid_port_type(self):
        """test_connection should reject non-string port."""
        result = _test_connection(host="localhost", port=5000, api_key="key")
        assert result["status"] == "error"
        assert "string" in result["message"].lower()

    def test_test_connection_invalid_api_key_type(self):
        """test_connection should reject non-string api_key."""
        result = _test_connection(host="localhost", port="5000", api_key=123)
        assert result["status"] == "error"
        assert "string" in result["message"].lower()

    def test_test_connection_uses_config_defaults(self, mock_config):
        """test_connection should use config values when parameters are empty."""
        with patch("src.tools.monitor_tools.OctoPrintClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.test_connection.return_value = {"status": "ok", "message": "OK"}

            result = _test_connection(host="", port="", api_key="")

            # Verify client was created with config values
            mock_client_class.assert_called_once_with("localhost", 5000, "test-api-key")

    def test_test_connection_empty_credentials_fails(self, monkeypatch):
        """test_connection should fail if no credentials available."""
        monkeypatch.setattr(src.config, "OCTOPRINT_HOST", "")
        monkeypatch.setattr(src.config, "OCTOPRINT_API_KEY", "")
        importlib.reload(src.tools.monitor_tools)

        result = _test_connection(host="", port="", api_key="")

        assert result["status"] == "error"
        assert "credentials" in result["message"].lower()

    @patch("src.tools.monitor_tools.OctoPrintClient")
    def test_test_connection_success(self, mock_client_class):
        """test_connection should return success response."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.test_connection.return_value = {
            "status": "ok",
            "server_version": "1.8.7",
            "api_version": "0.1",
            "message": "OK",
        }

        result = _test_connection(host="localhost", port="5000", api_key="test-key")

        assert result["status"] == "ok"
        assert result["server_version"] == "1.8.7"

    @patch("src.tools.monitor_tools.OctoPrintClient")
    def test_test_connection_handles_error(self, mock_client_class):
        """test_connection should handle client errors."""
        mock_client_class.return_value.test_connection.return_value = {
            "status": "error",
            "message": "Connection failed",
        }

        result = _test_connection(host="localhost", port="5000", api_key="bad-key")

        assert result["status"] == "error"


class TestPrinterStatusTool:
    """Test get_printer_status function."""

    def test_get_printer_status_invalid_host_type(self):
        """get_printer_status should reject non-string host."""
        result = _get_printer_status(host=123, port="5000", api_key="key")
        assert result["status"] == "error"

    def test_get_printer_status_invalid_port_type(self):
        """get_printer_status should reject non-string port."""
        result = _get_printer_status(host="localhost", port=5000, api_key="key")
        assert result["status"] == "error"

    def test_get_printer_status_invalid_api_key_type(self):
        """get_printer_status should reject non-string api_key."""
        result = _get_printer_status(host="localhost", port="5000", api_key=123)
        assert result["status"] == "error"

    @patch("src.tools.monitor_tools.OctoPrintClient")
    def test_get_printer_status_success(self, mock_client_class, mock_config):
        """get_printer_status should return printer state."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_printer_status.return_value = {
            "status": "ok",
            "state": "Printing",
            "bed_temp": {"current": 60.0, "target": 60},
            "nozzle_temp": {"current": 210.0, "target": 210},
            "message": "OK",
        }

        result = _get_printer_status(host="localhost", port="5000", api_key="test-key")

        assert result["status"] == "ok"
        assert result["state"] == "Printing"
        assert result["bed_temp"]["current"] == 60.0

    @patch("src.tools.monitor_tools.OctoPrintClient")
    def test_get_printer_status_uses_config_defaults(self, mock_client_class, mock_config):
        """get_printer_status should use config defaults."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_printer_status.return_value = {"status": "ok", "state": "Operational"}

        result = _get_printer_status(host="", port="", api_key="")

        mock_client_class.assert_called_once_with("localhost", 5000, "test-api-key")


class TestJobStatusTool:
    """Test get_job_status function."""

    def test_get_job_status_invalid_host_type(self):
        """get_job_status should reject non-string host."""
        result = _get_job_status(host=123, port="5000", api_key="key")
        assert result["status"] == "error"

    def test_get_job_status_invalid_port_type(self):
        """get_job_status should reject non-string port."""
        result = _get_job_status(host="localhost", port=5000, api_key="key")
        assert result["status"] == "error"

    def test_get_job_status_invalid_api_key_type(self):
        """get_job_status should reject non-string api_key."""
        result = _get_job_status(host="localhost", port="5000", api_key=123)
        assert result["status"] == "error"

    @patch("src.tools.monitor_tools.OctoPrintClient")
    def test_get_job_status_success(self, mock_client_class, mock_config):
        """get_job_status should return job information."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_job_status.return_value = {
            "status": "ok",
            "state": "Printing",
            "progress": {"completion": 50.0, "filepos": 500000, "printtime": 1800, "printtime_left": 1800},
            "filename": "model.gcode",
            "message": "OK",
        }

        result = _get_job_status(host="localhost", port="5000", api_key="test-key")

        assert result["status"] == "ok"
        assert result["state"] == "Printing"
        assert result["progress"]["completion"] == 50.0
        assert result["filename"] == "model.gcode"

    @patch("src.tools.monitor_tools.OctoPrintClient")
    def test_get_job_status_no_active_job(self, mock_client_class, mock_config):
        """get_job_status should handle no active job."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_job_status.return_value = {
            "status": "ok",
            "state": None,
            "progress": None,
            "filename": None,
            "message": "No active job",
        }

        result = _get_job_status(host="localhost", port="5000", api_key="test-key")

        assert result["status"] == "ok"
        assert result["state"] is None

    @patch("src.tools.monitor_tools.OctoPrintClient")
    def test_get_job_status_uses_config_defaults(self, mock_client_class, mock_config):
        """get_job_status should use config defaults."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_job_status.return_value = {"status": "ok", "state": None}

        result = _get_job_status(host="", port="", api_key="")

        mock_client_class.assert_called_once_with("localhost", 5000, "test-api-key")

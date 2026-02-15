"""Monitor phase tools for OctoPrint API integration and print monitoring."""

import logging
import time
from typing import Optional

from octorest import OctoRest

from src.config import OCTOPRINT_HOST, OCTOPRINT_PORT, OCTOPRINT_API_KEY

logger = logging.getLogger(__name__)


class OctoPrintClient:
    """Thin wrapper around octorest.OctoRest for OctoPrint API access."""

    def __init__(self, host: str, port: int, api_key: str):
        """Initialize OctoPrint client.

        Args:
            host: OctoPrint server hostname/IP
            port: OctoPrint server port
            api_key: OctoPrint API key for authentication

        Raises:
            ValueError: If any parameter is invalid
        """
        if not isinstance(host, str) or not host.strip():
            raise ValueError("host must be a non-empty string")
        if not isinstance(port, int) or port <= 0 or port > 65535:
            raise ValueError("port must be an integer between 1 and 65535")
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("api_key must be a non-empty string")

        self.host = host
        self.port = int(port)
        self.api_key = api_key
        self._client = None

    def _get_client(self) -> OctoRest:
        """Get or create OctoRest client instance."""
        if self._client is None:
            self._client = OctoRest(
                basedir=f"http://{self.host}:{self.port}",
                apikey=self.api_key,
            )
        return self._client

    def test_connection(self) -> dict:
        """Test connection to OctoPrint server.

        Returns:
            dict with keys:
                - status: "ok" or "error"
                - server_version: OctoPrint server version (if ok)
                - api_version: OctoPrint API version (if ok)
                - message: human-readable message
        """
        try:
            client = self._get_client()
            version_info = client.get_version()

            if version_info:
                return {
                    "status": "ok",
                    "server_version": version_info.get("server", "unknown"),
                    "api_version": version_info.get("api", "unknown"),
                    "message": f"Successfully connected to OctoPrint {version_info.get('server', 'unknown')}",
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to retrieve version info from OctoPrint",
                }
        except Exception as e:
            logger.error(f"test_connection: error connecting to {self.host}:{self.port}: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to connect to OctoPrint: {str(e)}",
            }

    def get_printer_status(self) -> dict:
        """Get current printer state and temperatures.

        Returns:
            dict with keys:
                - status: "ok" or "error"
                - state: printer state (Operational, Printing, Paused, etc.)
                - bed_temp: {"current": float, "target": float} or null
                - nozzle_temp: {"current": float, "target": float} or null
                - message: human-readable message
        """
        try:
            client = self._get_client()
            printer_info = client.get_printer()

            if not printer_info:
                return {
                    "status": "error",
                    "message": "Failed to retrieve printer status",
                }

            # Extract state
            state = printer_info.get("state", {}).get("text", "Unknown")

            # Extract temperature info
            temps = printer_info.get("temperature", {})
            bed_temp = None
            nozzle_temp = None

            if "bed" in temps:
                bed_data = temps["bed"]
                bed_temp = {
                    "current": bed_data.get("actual", 0),
                    "target": bed_data.get("target", 0),
                }

            if "tool0" in temps:
                tool_data = temps["tool0"]
                nozzle_temp = {
                    "current": tool_data.get("actual", 0),
                    "target": tool_data.get("target", 0),
                }

            return {
                "status": "ok",
                "state": state,
                "bed_temp": bed_temp,
                "nozzle_temp": nozzle_temp,
                "message": f"Printer state: {state}",
            }
        except Exception as e:
            logger.error(f"get_printer_status: error: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to get printer status: {str(e)}",
            }

    def get_job_status(self) -> dict:
        """Get active print job information.

        Returns:
            dict with keys:
                - status: "ok" or "error"
                - state: job state (Printing, Paused, etc.) or null if no active job
                - progress: {"completion": float (0-100), "filepos": int, "printtime": int, "printtime_left": int} or null
                - filename: current print filename or null
                - message: human-readable message
        """
        try:
            client = self._get_client()
            job_info = client.get_job()

            if not job_info:
                return {
                    "status": "ok",
                    "state": None,
                    "progress": None,
                    "filename": None,
                    "message": "No active print job",
                }

            state = job_info.get("state", None)
            progress_data = job_info.get("progress", {})

            progress = None
            if progress_data:
                progress = {
                    "completion": progress_data.get("completion", 0),
                    "filepos": progress_data.get("filepos", 0),
                    "printtime": progress_data.get("printtime", 0),
                    "printtime_left": progress_data.get("printtimeLeft", 0),
                }

            filename = None
            file_info = job_info.get("file", {})
            if file_info:
                filename = file_info.get("name", None)

            return {
                "status": "ok",
                "state": state,
                "progress": progress,
                "filename": filename,
                "message": f"Job state: {state}" if state else "No active job",
            }
        except Exception as e:
            logger.error(f"get_job_status: error: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to get job status: {str(e)}",
            }


def _get_connection_params(host: str, port: str, api_key: str) -> tuple[str, int, str]:
    """Get connection parameters, falling back to config values.

    Args:
        host: hostname (empty string to use config)
        port: port number (empty string to use config)
        api_key: API key (empty string to use config)

    Returns:
        tuple of (host, port, api_key)
    """
    final_host = host.strip() if isinstance(host, str) else ""
    final_port = port.strip() if isinstance(port, str) else ""
    final_api_key = api_key.strip() if isinstance(api_key, str) else ""

    if not final_host:
        final_host = OCTOPRINT_HOST
    if not final_port:
        final_port = OCTOPRINT_PORT
    if not final_api_key:
        final_api_key = OCTOPRINT_API_KEY

    try:
        final_port = int(final_port)
    except (ValueError, TypeError):
        final_port = 5000

    return final_host, final_port, final_api_key


def test_connection(host: str = "", port: str = "", api_key: str = "") -> dict:
    """Test connection to OctoPrint server.

    Falls back to config values (OCTOPRINT_HOST, OCTOPRINT_PORT, OCTOPRINT_API_KEY)
    for any empty parameters.

    Args:
        host: OctoPrint hostname (optional)
        port: OctoPrint port as string (optional)
        api_key: OctoPrint API key (optional)

    Returns:
        dict with keys:
            - status: "ok" or "error"
            - server_version: server version (if ok)
            - api_version: API version (if ok)
            - message: human-readable message
    """
    # Validate input types
    if not isinstance(host, str):
        logger.warning("test_connection: host must be string")
        return {"status": "error", "message": "host must be a string"}
    if not isinstance(port, str):
        logger.warning("test_connection: port must be string")
        return {"status": "error", "message": "port must be a string"}
    if not isinstance(api_key, str):
        logger.warning("test_connection: api_key must be string")
        return {"status": "error", "message": "api_key must be a string"}

    final_host, final_port, final_api_key = _get_connection_params(host, port, api_key)

    # Validate final parameters
    if not final_host or not final_api_key:
        logger.warning(
            "test_connection: missing required parameters after fallback (host=%s, api_key=%s)",
            final_host or "[empty]",
            "[set]" if final_api_key else "[empty]",
        )
        return {
            "status": "error",
            "message": "Missing required OctoPrint credentials (host, api_key)",
        }

    try:
        client = OctoPrintClient(final_host, final_port, final_api_key)
        result = client.test_connection()
        if result["status"] == "ok":
            logger.info(f"test_connection: successfully connected to {final_host}:{final_port}")
        else:
            logger.warning(f"test_connection: failed - {result['message']}")
        return result
    except ValueError as e:
        logger.warning(f"test_connection: invalid parameters: {str(e)}")
        return {"status": "error", "message": f"Invalid parameters: {str(e)}"}
    except Exception as e:
        logger.error(f"test_connection: unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}


def get_printer_status(host: str = "", port: str = "", api_key: str = "") -> dict:
    """Get current printer state and temperatures.

    Falls back to config values for any empty parameters.

    Args:
        host: OctoPrint hostname (optional)
        port: OctoPrint port as string (optional)
        api_key: OctoPrint API key (optional)

    Returns:
        dict with keys:
            - status: "ok" or "error"
            - state: printer state string
            - bed_temp: {"current": float, "target": float} or null
            - nozzle_temp: {"current": float, "target": float} or null
            - message: human-readable message
    """
    # Validate input types
    if not isinstance(host, str):
        logger.warning("get_printer_status: host must be string")
        return {"status": "error", "message": "host must be a string"}
    if not isinstance(port, str):
        logger.warning("get_printer_status: port must be string")
        return {"status": "error", "message": "port must be a string"}
    if not isinstance(api_key, str):
        logger.warning("get_printer_status: api_key must be string")
        return {"status": "error", "message": "api_key must be a string"}

    final_host, final_port, final_api_key = _get_connection_params(host, port, api_key)

    # Validate final parameters
    if not final_host or not final_api_key:
        logger.warning("get_printer_status: missing required parameters after fallback")
        return {
            "status": "error",
            "message": "Missing required OctoPrint credentials",
        }

    try:
        client = OctoPrintClient(final_host, final_port, final_api_key)
        result = client.get_printer_status()
        logger.info(f"get_printer_status: retrieved status - {result.get('state', 'unknown')}")
        return result
    except ValueError as e:
        logger.warning(f"get_printer_status: invalid parameters: {str(e)}")
        return {"status": "error", "message": f"Invalid parameters: {str(e)}"}
    except Exception as e:
        logger.error(f"get_printer_status: unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}


def get_job_status(host: str = "", port: str = "", api_key: str = "") -> dict:
    """Get active print job information.

    Falls back to config values for any empty parameters.

    Args:
        host: OctoPrint hostname (optional)
        port: OctoPrint port as string (optional)
        api_key: OctoPrint API key (optional)

    Returns:
        dict with keys:
            - status: "ok" or "error"
            - state: job state string or null
            - progress: {"completion": float, "filepos": int, "printtime": int, "printtime_left": int} or null
            - filename: current file name or null
            - message: human-readable message
    """
    # Validate input types
    if not isinstance(host, str):
        logger.warning("get_job_status: host must be string")
        return {"status": "error", "message": "host must be a string"}
    if not isinstance(port, str):
        logger.warning("get_job_status: port must be string")
        return {"status": "error", "message": "port must be a string"}
    if not isinstance(api_key, str):
        logger.warning("get_job_status: api_key must be string")
        return {"status": "error", "message": "api_key must be a string"}

    final_host, final_port, final_api_key = _get_connection_params(host, port, api_key)

    # Validate final parameters
    if not final_host or not final_api_key:
        logger.warning("get_job_status: missing required parameters after fallback")
        return {
            "status": "error",
            "message": "Missing required OctoPrint credentials",
        }

    try:
        client = OctoPrintClient(final_host, final_port, final_api_key)
        result = client.get_job_status()
        logger.info(f"get_job_status: retrieved status - {result.get('state', 'no active job')}")
        return result
    except ValueError as e:
        logger.warning(f"get_job_status: invalid parameters: {str(e)}")
        return {"status": "error", "message": f"Invalid parameters: {str(e)}"}
    except Exception as e:
        logger.error(f"get_job_status: unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}

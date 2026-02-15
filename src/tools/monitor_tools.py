"""Monitor phase tools for OctoPrint API integration and print monitoring."""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from octorest import OctoRest

from src.config import OCTOPRINT_HOST, OCTOPRINT_PORT, OCTOPRINT_API_KEY

# Project directory for storing metrics (patchable in tests)
PROJECTS_DIR = os.getenv("PROJECTS_DIR", "./projects")

# Configurable detection thresholds (patchable in tests via environment variables)
TEMP_DEVIATION_THRESHOLD_C = float(os.getenv("TEMP_DEVIATION_THRESHOLD_C", "10.0"))
TEMP_DEVIATION_DURATION_S = int(os.getenv("TEMP_DEVIATION_DURATION_S", "30"))
FILAMENT_STALL_DURATION_S = int(os.getenv("FILAMENT_STALL_DURATION_S", "60"))
LAYER_SHIFT_THRESHOLD_MM = float(os.getenv("LAYER_SHIFT_THRESHOLD_MM", "5.0"))

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


# ============================================================================
# ISSUE DETECTION TOOLS (TICKET-018)
# ============================================================================

def _get_monitor_dir(project_name: str) -> Path:
    """Return monitoring directory path, creating it if needed."""
    monitor_dir = Path(PROJECTS_DIR) / project_name / "monitoring"
    monitor_dir.mkdir(parents=True, exist_ok=True)
    return monitor_dir


def _detect_temperature_anomalies(snapshots: list) -> list:
    """Detect sustained temperature deviations exceeding threshold."""
    issues = []
    if len(snapshots) < 2:
        return issues

    deviation_start_idx = None
    deviation_start_elapsed = None

    for i, snapshot in enumerate(snapshots):
        nozzle = snapshot.get("nozzle_temp", {})
        bed = snapshot.get("bed_temp", {})
        elapsed = snapshot.get("print_time_elapsed", 0)

        nozzle_current = nozzle.get("current") if nozzle else None
        nozzle_target = nozzle.get("target") if nozzle else None
        bed_current = bed.get("current") if bed else None
        bed_target = bed.get("target") if bed else None

        has_deviation = False
        deviation_detail = ""

        if nozzle_current and nozzle_target:
            nozzle_diff = abs(nozzle_current - nozzle_target)
            if nozzle_diff > TEMP_DEVIATION_THRESHOLD_C:
                has_deviation = True
                deviation_detail = f"Nozzle {nozzle_diff:.1f}°C"

        if bed_current and bed_target:
            bed_diff = abs(bed_current - bed_target)
            if bed_diff > TEMP_DEVIATION_THRESHOLD_C:
                has_deviation = True
                if deviation_detail:
                    deviation_detail += f" / Bed {bed_diff:.1f}°C"
                else:
                    deviation_detail = f"Bed {bed_diff:.1f}°C"

        if has_deviation:
            if deviation_start_idx is None:
                deviation_start_idx = i
                deviation_start_elapsed = elapsed
        else:
            deviation_start_idx = None
            deviation_start_elapsed = None

        # Check if deviation has lasted long enough
        if deviation_start_idx is not None and i > deviation_start_idx:
            duration = elapsed - deviation_start_elapsed
            if duration > TEMP_DEVIATION_DURATION_S:
                issues.append({
                    "type": "temperature_deviation",
                    "severity": "warning",
                    "message": f"{deviation_detail} deviation detected for {duration:.0f}s",
                    "detected_at": i,
                    "data": {
                        "nozzle_temp": nozzle if nozzle else None,
                        "bed_temp": bed if bed else None,
                        "duration_seconds": duration
                    }
                })
                deviation_start_idx = None  # Reset to avoid repeated alerts

    return issues


def _detect_filament_stall(snapshots: list) -> list:
    """Detect periods of stalled filament extrusion while printing."""
    issues = []
    if len(snapshots) < 2:
        return issues

    stall_start_idx = None
    stall_start_elapsed = None
    stall_start_progress = None

    for i, snapshot in enumerate(snapshots):
        state = snapshot.get("state", "")
        progress = snapshot.get("progress", 0)
        elapsed = snapshot.get("print_time_elapsed", 0)

        is_printing = state == "Printing"
        is_stalled = (is_printing and
                      stall_start_progress is not None and
                      abs(progress - stall_start_progress) < 0.1)  # Progress hasn't advanced

        if is_printing and stall_start_idx is None:
            stall_start_idx = i
            stall_start_elapsed = elapsed
            stall_start_progress = progress
        elif is_printing and stall_start_idx is not None and is_stalled:
            duration = elapsed - stall_start_elapsed
            if duration > FILAMENT_STALL_DURATION_S:
                issues.append({
                    "type": "filament_jam",
                    "severity": "error",
                    "message": f"Filament extrusion stalled for {duration:.0f}s at {progress:.1f}% progress",
                    "detected_at": i,
                    "data": {
                        "progress": progress,
                        "duration_seconds": duration,
                        "state": state
                    }
                })
                stall_start_idx = None
                stall_start_elapsed = None
                stall_start_progress = None
        else:
            stall_start_idx = None
            stall_start_elapsed = None
            stall_start_progress = None

    return issues


def _detect_bed_adhesion_issues(snapshots: list) -> list:
    """Detect bed adhesion problems in early printing stages."""
    issues = []
    if not snapshots:
        return issues

    # Only examine first few snapshots (progress < 10%)
    early_phase_snapshots = [s for s in snapshots if s.get("progress", 0) < 10.0]
    if not early_phase_snapshots:
        return issues

    for i, snapshot in enumerate(early_phase_snapshots):
        bed = snapshot.get("bed_temp", {})
        state = snapshot.get("state", "")
        progress = snapshot.get("progress", 0)

        bed_current = bed.get("current") if bed else None
        bed_target = bed.get("target") if bed else None

        # Check 1: Sudden bed temperature drop during early print
        if bed_current and bed_target:
            bed_diff = bed_target - bed_current
            if bed_diff > 5.0:  # More than 5°C drop
                issues.append({
                    "type": "bed_adhesion_risk",
                    "severity": "warning",
                    "message": f"Bed temperature dropped {bed_diff:.1f}°C during early print at {progress:.1f}%",
                    "detected_at": i,
                    "data": {
                        "bed_temp": bed,
                        "progress": progress
                    }
                })

        # Check 2: Print stopped during early stage
        if state not in ("Printing", "Paused") and progress < 5.0:
            issues.append({
                "type": "early_print_failure",
                "severity": "warning",
                "message": f"Print transitioned to {state} at {progress:.1f}% progress - possible bed adhesion failure",
                "detected_at": i,
                "data": {
                    "state": state,
                    "progress": progress
                }
            })
            break

    return issues


def _detect_layer_shift(snapshots: list) -> list:
    """Detect layer shifts indicated by unexpected time changes."""
    issues = []
    if len(snapshots) < 2:
        return issues

    for i in range(1, len(snapshots)):
        prev_elapsed = snapshots[i - 1].get("print_time_elapsed", 0)
        curr_elapsed = snapshots[i].get("print_time_elapsed", 0)
        curr_progress = snapshots[i].get("progress", 0)
        prev_progress = snapshots[i - 1].get("progress", 0)

        # Detect time reset/jump (non-monotonic)
        if curr_elapsed < prev_elapsed:
            issues.append({
                "type": "layer_shift",
                "severity": "error",
                "message": f"Detected possible layer shift: print time jumped backward at {curr_progress:.1f}%",
                "detected_at": i,
                "data": {
                    "previous_elapsed": prev_elapsed,
                    "current_elapsed": curr_elapsed,
                    "progress": curr_progress
                }
            })

    return issues


async def detect_print_issues(project_name: str, metrics_path: Optional[str] = None) -> dict:
    """Analyze collected metrics to detect print issues.

    Args:
        project_name: Name of the project being monitored
        metrics_path: Optional override path to metrics.jsonl file

    Returns:
        dict with status, issues_detected (list), and alert_count
    """
    # Validate input
    if not project_name:
        logger.warning("detect_print_issues: empty project_name")
        return {
            "status": "error",
            "message": "project_name is required"
        }

    # Locate metrics file
    if metrics_path:
        metrics_file = Path(metrics_path)
    else:
        metrics_file = _get_monitor_dir(project_name) / "metrics.jsonl"

    # If no metrics yet, return ok with no issues
    if not metrics_file.exists():
        logger.info(f"detect_print_issues: no metrics file found at {metrics_file}")
        return {
            "status": "ok",
            "issues_detected": [],
            "alert_count": 0,
            "message": "No metrics available for analysis"
        }

    # Parse JSONL metrics
    snapshots = []
    try:
        with open(metrics_file) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    snapshots.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"detect_print_issues: skipping malformed line {line_num} in {metrics_file}")
                    continue
    except Exception as e:
        logger.error(f"detect_print_issues: error reading metrics file: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Error reading metrics file: {str(e)}"
        }

    if not snapshots:
        logger.info(f"detect_print_issues: no valid snapshots in {metrics_file}")
        return {
            "status": "ok",
            "issues_detected": [],
            "alert_count": 0,
            "message": "No valid metrics for analysis"
        }

    # Run detection algorithms
    issues = []
    issues.extend(_detect_temperature_anomalies(snapshots))
    issues.extend(_detect_filament_stall(snapshots))
    issues.extend(_detect_bed_adhesion_issues(snapshots))
    issues.extend(_detect_layer_shift(snapshots))

    # Count alerts
    alert_count = len([i for i in issues if i["severity"] in ("warning", "error")])

    logger.info(f"detect_print_issues: analysis complete for {project_name} - {len(issues)} issue(s) detected")

    return {
        "status": "ok",
        "issues_detected": issues,
        "alert_count": alert_count,
        "message": f"Analysis complete: {len(issues)} issue(s) detected"
    }

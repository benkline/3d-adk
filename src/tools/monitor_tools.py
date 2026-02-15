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


# ============================================================================
# USER ALERTS & INTERVENTION TOOLS (TICKET-019)
# ============================================================================

# Mapping of issue types to user-facing recommended actions
ISSUE_ACTION_MAP = {
    "temperature_deviation": "Check and adjust nozzle/bed temperature",
    "filament_jam": "Pause print and inspect filament path",
    "layer_shift": "Pause print and inspect print bed adhesion",
    "bed_adhesion_risk": "Monitor closely; consider pausing to re-level bed",
    "early_print_failure": "Review first layers; consider canceling and restarting",
}


def _load_alerts(alerts_file: Path) -> list:
    """Load existing alerts from JSON file."""
    if not alerts_file.exists():
        return []
    try:
        with open(alerts_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _load_interventions(interventions_file: Path) -> list:
    """Load existing interventions from JSON file."""
    if not interventions_file.exists():
        return []
    try:
        with open(interventions_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


async def format_alert(project_name: str, issues: list) -> dict:
    """Format detected issues into user-readable alerts and persist them.

    Args:
        project_name: Name of the project being monitored
        issues: List of issues from detect_print_issues (each with type, severity, message)

    Returns:
        dict with status, alerts (list), and alert_count
    """
    if not project_name:
        logger.warning("format_alert: empty project_name")
        return {"status": "error", "message": "project_name is required"}

    if not isinstance(issues, list):
        logger.warning("format_alert: issues must be a list")
        return {"status": "error", "message": "issues must be a list"}

    try:
        monitor_dir = _get_monitor_dir(project_name)
        alerts_file = monitor_dir / "alerts.json"

        # Load existing alerts
        existing_alerts = _load_alerts(alerts_file)

        # Format new alerts from issues
        new_alerts = []
        timestamp_ms = int(time.time() * 1000)
        timestamp_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp_ms / 1000))

        for i, issue in enumerate(issues):
            alert_id = f"{issue.get('type', 'unknown')}_{timestamp_ms + i}"
            alert = {
                "alert_id": alert_id,
                "severity": issue.get("severity", "warning"),
                "message": issue.get("message", "Unknown issue detected"),
                "recommended_action": ISSUE_ACTION_MAP.get(
                    issue.get("type"), "Inspect printer and review print status"
                ),
                "timestamp": timestamp_iso,
                "issue_type": issue.get("type", "unknown"),
            }
            new_alerts.append(alert)

        # Append to persistent storage
        all_alerts = existing_alerts + new_alerts
        with open(alerts_file, "w") as f:
            json.dump(all_alerts, f, indent=2)

        logger.info(f"format_alert: {len(new_alerts)} alert(s) formatted for {project_name}")

        return {
            "status": "ok",
            "alerts": new_alerts,
            "alert_count": len(new_alerts),
            "message": f"Formatted {len(new_alerts)} alert(s)"
        }
    except Exception as e:
        logger.error(f"format_alert: unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Error formatting alerts: {str(e)}"}


async def pause_print(
    project_name: str, host: str = "", port: str = "", api_key: str = ""
) -> dict:
    """Pause the current print job.

    Args:
        project_name: Name of the project being monitored
        host: OctoPrint server hostname (empty to use config default)
        port: OctoPrint server port (empty to use config default)
        api_key: OctoPrint API key (empty to use config default)

    Returns:
        dict with status and action taken
    """
    if not project_name:
        logger.warning("pause_print: empty project_name")
        return {"status": "error", "message": "project_name is required"}

    try:
        final_host, final_port, final_api_key = _get_connection_params(host, port, api_key)
        client = OctoPrintClient(final_host, final_port, final_api_key)
        client._get_client().pause()

        # Log intervention
        monitor_dir = _get_monitor_dir(project_name)
        interventions_file = monitor_dir / "interventions.json"
        interventions = _load_interventions(interventions_file)
        interventions.append({
            "action": "pause",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "ok"
        })
        with open(interventions_file, "w") as f:
            json.dump(interventions, f, indent=2)

        logger.info(f"pause_print: print paused for {project_name}")
        return {
            "status": "ok",
            "message": "Print paused successfully",
            "action": "pause"
        }
    except ValueError as e:
        logger.warning(f"pause_print: invalid parameters: {str(e)}")
        return {"status": "error", "message": f"Invalid parameters: {str(e)}"}
    except Exception as e:
        logger.error(f"pause_print: unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Error pausing print: {str(e)}"}


async def resume_print(
    project_name: str, host: str = "", port: str = "", api_key: str = ""
) -> dict:
    """Resume a paused print job.

    Args:
        project_name: Name of the project being monitored
        host: OctoPrint server hostname (empty to use config default)
        port: OctoPrint server port (empty to use config default)
        api_key: OctoPrint API key (empty to use config default)

    Returns:
        dict with status and action taken
    """
    if not project_name:
        logger.warning("resume_print: empty project_name")
        return {"status": "error", "message": "project_name is required"}

    try:
        final_host, final_port, final_api_key = _get_connection_params(host, port, api_key)
        client = OctoPrintClient(final_host, final_port, final_api_key)
        client._get_client().resume()

        # Log intervention
        monitor_dir = _get_monitor_dir(project_name)
        interventions_file = monitor_dir / "interventions.json"
        interventions = _load_interventions(interventions_file)
        interventions.append({
            "action": "resume",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "ok"
        })
        with open(interventions_file, "w") as f:
            json.dump(interventions, f, indent=2)

        logger.info(f"resume_print: print resumed for {project_name}")
        return {
            "status": "ok",
            "message": "Print resumed successfully",
            "action": "resume"
        }
    except ValueError as e:
        logger.warning(f"resume_print: invalid parameters: {str(e)}")
        return {"status": "error", "message": f"Invalid parameters: {str(e)}"}
    except Exception as e:
        logger.error(f"resume_print: unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Error resuming print: {str(e)}"}


async def cancel_print(
    project_name: str, host: str = "", port: str = "", api_key: str = ""
) -> dict:
    """Cancel the current print job.

    Args:
        project_name: Name of the project being monitored
        host: OctoPrint server hostname (empty to use config default)
        port: OctoPrint server port (empty to use config default)
        api_key: OctoPrint API key (empty to use config default)

    Returns:
        dict with status and action taken
    """
    if not project_name:
        logger.warning("cancel_print: empty project_name")
        return {"status": "error", "message": "project_name is required"}

    try:
        final_host, final_port, final_api_key = _get_connection_params(host, port, api_key)
        client = OctoPrintClient(final_host, final_port, final_api_key)
        client._get_client().cancel()

        # Log intervention
        monitor_dir = _get_monitor_dir(project_name)
        interventions_file = monitor_dir / "interventions.json"
        interventions = _load_interventions(interventions_file)
        interventions.append({
            "action": "cancel",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "ok"
        })
        with open(interventions_file, "w") as f:
            json.dump(interventions, f, indent=2)

        logger.info(f"cancel_print: print canceled for {project_name}")
        return {
            "status": "ok",
            "message": "Print canceled successfully",
            "action": "cancel"
        }
    except ValueError as e:
        logger.warning(f"cancel_print: invalid parameters: {str(e)}")
        return {"status": "error", "message": f"Invalid parameters: {str(e)}"}
    except Exception as e:
        logger.error(f"cancel_print: unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Error canceling print: {str(e)}"}


async def adjust_temperature(
    project_name: str, component: str, target_temp: float, host: str = "", port: str = "",
    api_key: str = ""
) -> dict:
    """Adjust printer temperature (nozzle or bed).

    Args:
        project_name: Name of the project being monitored
        component: "nozzle" or "bed"
        target_temp: Target temperature in Celsius (0-350)
        host: OctoPrint server hostname (empty to use config default)
        port: OctoPrint server port (empty to use config default)
        api_key: OctoPrint API key (empty to use config default)

    Returns:
        dict with status, component, and target_temp
    """
    if not project_name:
        logger.warning("adjust_temperature: empty project_name")
        return {"status": "error", "message": "project_name is required"}

    if component not in ("nozzle", "bed"):
        logger.warning(f"adjust_temperature: invalid component: {component}")
        return {"status": "error", "message": "component must be 'nozzle' or 'bed'"}

    try:
        target_temp_float = float(target_temp)
    except (TypeError, ValueError):
        logger.warning(f"adjust_temperature: invalid temperature: {target_temp}")
        return {"status": "error", "message": "target_temp must be a number"}

    if target_temp_float < 0 or target_temp_float > 350:
        logger.warning(f"adjust_temperature: temperature out of range: {target_temp_float}")
        return {
            "status": "error",
            "message": "target_temp must be between 0 and 350 Celsius"
        }

    try:
        final_host, final_port, final_api_key = _get_connection_params(host, port, api_key)
        client = OctoPrintClient(final_host, final_port, final_api_key)
        octorest_client = client._get_client()

        if component == "nozzle":
            octorest_client.tool_target({"tool0": target_temp_float})
        else:  # bed
            octorest_client.bed_target(target_temp_float)

        # Log intervention
        monitor_dir = _get_monitor_dir(project_name)
        interventions_file = monitor_dir / "interventions.json"
        interventions = _load_interventions(interventions_file)
        interventions.append({
            "action": "adjust_temperature",
            "component": component,
            "target_temp": target_temp_float,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "ok"
        })
        with open(interventions_file, "w") as f:
            json.dump(interventions, f, indent=2)

        logger.info(f"adjust_temperature: {component} set to {target_temp_float}°C for {project_name}")
        return {
            "status": "ok",
            "message": f"Temperature for {component} set to {target_temp_float}°C",
            "component": component,
            "target_temp": target_temp_float
        }
    except ValueError as e:
        logger.warning(f"adjust_temperature: invalid parameters: {str(e)}")
        return {"status": "error", "message": f"Invalid parameters: {str(e)}"}
    except Exception as e:
        logger.error(f"adjust_temperature: unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Error adjusting temperature: {str(e)}"}


# ============================================================================
# PRINT COMPLETION & QUALITY ASSESSMENT TOOLS (TICKET-020)
# ============================================================================


def _load_quality_assessment(qa_file: Path) -> dict:
    """Load quality assessment from JSON file.

    Args:
        qa_file: Path to quality_assessment.json

    Returns:
        Quality assessment dict or {} if not found
    """
    if not qa_file.exists():
        return {}
    try:
        with open(qa_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _load_print_summary(summary_file: Path) -> dict:
    """Load print summary from JSON file.

    Args:
        summary_file: Path to print_summary.json

    Returns:
        Print summary dict or {} if not found
    """
    if not summary_file.exists():
        return {}
    try:
        with open(summary_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _load_archive(archive_file: Path) -> list:
    """Load print archive list from JSON file.

    Args:
        archive_file: Path to archive.json

    Returns:
        List of archived print records or [] if not found
    """
    if not archive_file.exists():
        return []
    try:
        with open(archive_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _aggregate_metrics_summary(snapshots: list) -> dict:
    """Aggregate statistics from metric snapshots.

    Args:
        snapshots: List of metric snapshot dicts

    Returns:
        Dict with aggregated stats
    """
    if not snapshots:
        return {
            "total_snapshots": 0,
            "total_print_time_s": 0,
            "avg_nozzle_temp_c": 0,
            "max_nozzle_temp_c": 0,
            "avg_bed_temp_c": 0,
            "max_bed_temp_c": 0,
        }

    nozzle_temps = []
    bed_temps = []
    total_time = 0

    for snap in snapshots:
        if snap.get("nozzle_temp") and snap["nozzle_temp"].get("current"):
            nozzle_temps.append(snap["nozzle_temp"]["current"])
        if snap.get("bed_temp") and snap["bed_temp"].get("current"):
            bed_temps.append(snap["bed_temp"]["current"])
        total_time = max(total_time, snap.get("print_time_elapsed", 0))

    return {
        "total_snapshots": len(snapshots),
        "total_print_time_s": total_time,
        "avg_nozzle_temp_c": sum(nozzle_temps) / len(nozzle_temps) if nozzle_temps else 0,
        "max_nozzle_temp_c": max(nozzle_temps) if nozzle_temps else 0,
        "avg_bed_temp_c": sum(bed_temps) / len(bed_temps) if bed_temps else 0,
        "max_bed_temp_c": max(bed_temps) if bed_temps else 0,
    }


def _generate_post_processing_recommendations(overall_quality: str, issues: list) -> list:
    """Generate post-processing recommendations based on quality and issues.

    Args:
        overall_quality: One of "excellent", "good", "acceptable", "poor"
        issues: List of detected issues

    Returns:
        List of recommendation strings
    """
    recommendations = []

    if overall_quality == "poor":
        recommendations.append("Consider adjusting print settings (temperature, speed) for next print")
        recommendations.append("Review nozzle and bed cleanliness")
        recommendations.append("Check for mechanical issues (bed leveling, loose belts)")

    if overall_quality == "acceptable":
        recommendations.append("Minor post-processing may be needed")
        recommendations.append("Consider fine-tuning support removal technique")

    # Check for specific issues
    has_temp_issues = any(i.get("type") == "temperature_deviation" for i in issues)
    if has_temp_issues:
        recommendations.append("Monitor nozzle temperature calibration")

    has_filament_issues = any(i.get("type") == "filament_jam" for i in issues)
    if has_filament_issues:
        recommendations.append("Clean nozzle and check filament path")

    has_bed_issues = any(i.get("type") == "bed_adhesion_risk" for i in issues)
    if has_bed_issues:
        recommendations.append("Level bed and check adhesion surface (PEI, glass, etc.)")

    if overall_quality in ("excellent", "good"):
        recommendations.append("Excellent print quality achieved - maintain current settings")

    return recommendations if recommendations else ["Standard finishing techniques sufficient"]


async def detect_print_completion(project_name: str, host: str = "", port: str = "", api_key: str = "") -> dict:
    """Detect if a print job has completed.

    Args:
        project_name: Name of the project
        host: OctoPrint hostname (optional, uses config if empty)
        port: OctoPrint port as string (optional, uses config if empty)
        api_key: OctoPrint API key (optional, uses config if empty)

    Returns:
        dict with keys:
            - status: "ok" or "error"
            - completed: bool (True if print is complete)
            - state: current job state
            - filename: name of completed print file
            - print_time_elapsed: total print time in seconds
            - message: human-readable message
    """
    if not project_name or not isinstance(project_name, str):
        logger.warning("detect_print_completion: empty or invalid project_name")
        return {"status": "error", "message": "project_name is required"}

    try:
        final_host, final_port, final_api_key = _get_connection_params(host, port, api_key)

        if not final_host or not final_api_key:
            logger.warning("detect_print_completion: missing required OctoPrint credentials")
            return {
                "status": "error",
                "message": "Missing required OctoPrint credentials (host, api_key)"
            }

        client = OctoPrintClient(final_host, final_port, final_api_key)
        job_result = client.get_job_status()

        if job_result["status"] != "ok":
            return job_result

        # Check if print is complete
        state = job_result.get("state")
        progress = job_result.get("progress")
        filename = job_result.get("filename")

        # Completed if no active job (state is None) or completion == 100%
        completed = state is None or (progress and progress.get("completion") == 100)
        print_time = progress.get("printtime", 0) if progress else 0

        logger.info(f"detect_print_completion: {project_name} - completed={completed}, state={state}")
        return {
            "status": "ok",
            "completed": completed,
            "state": state,
            "filename": filename,
            "print_time_elapsed": print_time,
            "message": f"Print completion check: {'completed' if completed else 'in progress'}"
        }
    except ValueError as e:
        logger.warning(f"detect_print_completion: invalid parameters: {str(e)}")
        return {"status": "error", "message": f"Invalid parameters: {str(e)}"}
    except Exception as e:
        logger.error(f"detect_print_completion: unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Error detecting print completion: {str(e)}"}


async def record_quality_assessment(
    project_name: str,
    overall_quality: str,
    issues_encountered: str = "",
    user_notes: str = "",
    photo_path: str = ""
) -> dict:
    """Record print quality assessment from user.

    Args:
        project_name: Name of the project
        overall_quality: One of "excellent", "good", "acceptable", "poor"
        issues_encountered: Description of any issues (optional)
        user_notes: User's additional notes (optional)
        photo_path: Path to photo/inspection image (optional)

    Returns:
        dict with keys:
            - status: "ok" or "error"
            - assessment_id: unique identifier for this assessment
            - message: human-readable message
    """
    if not project_name or not isinstance(project_name, str):
        logger.warning("record_quality_assessment: empty or invalid project_name")
        return {"status": "error", "message": "project_name is required"}

    if not overall_quality or not isinstance(overall_quality, str):
        logger.warning("record_quality_assessment: empty or invalid overall_quality")
        return {"status": "error", "message": "overall_quality is required"}

    valid_qualities = {"excellent", "good", "acceptable", "poor"}
    if overall_quality.lower() not in valid_qualities:
        logger.warning(f"record_quality_assessment: invalid quality value: {overall_quality}")
        return {
            "status": "error",
            "message": f"overall_quality must be one of: {', '.join(valid_qualities)}"
        }

    try:
        monitor_dir = _get_monitor_dir(project_name)
        qa_file = monitor_dir / "quality_assessment.json"

        # Create assessment record
        assessment_id = f"qa_{int(time.time() * 1000)}"
        assessment = {
            "assessment_id": assessment_id,
            "overall_quality": overall_quality.lower(),
            "issues_encountered": issues_encountered,
            "user_notes": user_notes,
            "photo_path": photo_path,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        # Save assessment
        with open(qa_file, "w") as f:
            json.dump(assessment, f, indent=2)

        logger.info(f"record_quality_assessment: {project_name} - quality={overall_quality}")
        return {
            "status": "ok",
            "assessment_id": assessment_id,
            "message": f"Quality assessment recorded: {overall_quality}"
        }
    except Exception as e:
        logger.error(f"record_quality_assessment: unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Error recording quality assessment: {str(e)}"}


async def generate_print_summary(project_name: str) -> dict:
    """Generate comprehensive print summary from all monitoring data.

    Args:
        project_name: Name of the project

    Returns:
        dict with keys:
            - status: "ok" or "error"
            - summary: comprehensive summary dict (if status="ok")
            - message: human-readable message
    """
    if not project_name or not isinstance(project_name, str):
        logger.warning("generate_print_summary: empty or invalid project_name")
        return {"status": "error", "message": "project_name is required"}

    try:
        monitor_dir = _get_monitor_dir(project_name)

        # Load all data sources
        metrics_file = monitor_dir / "metrics.jsonl"
        alerts_file = monitor_dir / "alerts.json"
        interventions_file = monitor_dir / "interventions.json"
        qa_file = monitor_dir / "quality_assessment.json"

        # Load metrics
        snapshots = []
        if metrics_file.exists():
            with open(metrics_file) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        snapshots.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning(f"generate_print_summary: skipping malformed metrics line {line_num}")

        # Load alerts, interventions, quality assessment
        alerts = _load_alerts(alerts_file)
        interventions = _load_interventions(interventions_file)
        quality_assessment = _load_quality_assessment(qa_file)

        # Aggregate metrics
        metrics_summary = _aggregate_metrics_summary(snapshots)

        # Generate post-processing recommendations
        issues = [a for a in alerts]  # alerts are structured issues
        recommendations = _generate_post_processing_recommendations(
            quality_assessment.get("overall_quality", "unknown"),
            issues
        )

        # Build comprehensive summary
        summary = {
            "project_name": project_name,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "metrics": metrics_summary,
            "quality_assessment": quality_assessment if quality_assessment else None,
            "alerts_count": len(alerts),
            "interventions_count": len(interventions),
            "post_processing_recommendations": recommendations
        }

        # Save summary
        summary_file = monitor_dir / "print_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"generate_print_summary: {project_name} - {len(alerts)} alerts, {len(interventions)} interventions")
        return {
            "status": "ok",
            "summary": summary,
            "message": "Print summary generated successfully"
        }
    except Exception as e:
        logger.error(f"generate_print_summary: unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Error generating print summary: {str(e)}"}


async def archive_print_metadata(project_name: str) -> dict:
    """Archive completed print metadata for historical analysis.

    Args:
        project_name: Name of the project

    Returns:
        dict with keys:
            - status: "ok" or "error"
            - archive_id: unique identifier for this archive record
            - archived_at: timestamp of archival
            - message: human-readable message
    """
    if not project_name or not isinstance(project_name, str):
        logger.warning("archive_print_metadata: empty or invalid project_name")
        return {"status": "error", "message": "project_name is required"}

    try:
        monitor_dir = _get_monitor_dir(project_name)
        summary_file = monitor_dir / "print_summary.json"
        archive_file = monitor_dir / "archive.json"

        # Check if summary exists
        if not summary_file.exists():
            logger.warning(f"archive_print_metadata: no print summary for {project_name}")
            return {
                "status": "error",
                "message": "No print summary found - run generate_print_summary first"
            }

        # Load summary
        summary = _load_print_summary(summary_file)

        # Create archive record
        archive_id = f"archive_{int(time.time() * 1000)}"
        archived_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        archive_record = {
            "archive_id": archive_id,
            "archived_at": archived_at,
            "project_name": project_name,
            "summary": summary
        }

        # Load existing archive and append
        archive_list = _load_archive(archive_file)
        archive_list.append(archive_record)

        # Save archive
        with open(archive_file, "w") as f:
            json.dump(archive_list, f, indent=2)

        logger.info(f"archive_print_metadata: {project_name} archived as {archive_id}")
        return {
            "status": "ok",
            "archive_id": archive_id,
            "archived_at": archived_at,
            "message": f"Print metadata archived: {archive_id}"
        }
    except Exception as e:
        logger.error(f"archive_print_metadata: unexpected error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Error archiving print metadata: {str(e)}"}

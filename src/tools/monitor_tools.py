"""Monitor tools for real-time OctoPrint monitoring and metrics collection."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from src.config import OCTOPRINT_API_KEY, OCTOPRINT_HOST, OCTOPRINT_PORT, PROJECTS_DIR

logger = logging.getLogger(__name__)

# Lazy HTTP session singleton
_http_session = None


def _get_http_session() -> requests.Session:
    """Get or create the HTTP session with OctoPrint API key."""
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        if OCTOPRINT_API_KEY:
            _http_session.headers.update({"X-Api-Key": OCTOPRINT_API_KEY})
    return _http_session


def _octoprint_url(path: str) -> str:
    """Construct OctoPrint API URL."""
    return f"http://{OCTOPRINT_HOST}:{OCTOPRINT_PORT}/api/{path}"


def _get_monitor_dir(project_name: str) -> Path:
    """Create and return the monitor directory for a project."""
    monitor_dir = Path(PROJECTS_DIR) / project_name / "monitor"
    monitor_dir.mkdir(parents=True, exist_ok=True)
    return monitor_dir


def _load_metrics(project_name: str) -> list:
    """Load all metrics from JSONL file. Returns empty list if file doesn't exist."""
    metrics_path = _get_monitor_dir(project_name) / "metrics.jsonl"
    if not metrics_path.exists():
        return []

    metrics = []
    try:
        with open(metrics_path, "r") as f:
            for line in f:
                if line.strip():
                    metrics.append(json.loads(line))
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Could not load metrics from {metrics_path}: {e}")
        return []

    return metrics


def _save_metric(project_name: str, snapshot: dict) -> None:
    """Append a metric snapshot to the JSONL file."""
    metrics_path = _get_monitor_dir(project_name) / "metrics.jsonl"
    with open(metrics_path, "a") as f:
        f.write(json.dumps(snapshot) + "\n")


def _format_snapshot(printer_data: dict, job_data: dict) -> dict:
    """Format printer and job data into the standard status snapshot."""
    timestamp = datetime.now(timezone.utc).isoformat()

    # Extract temperatures
    bed_temp = printer_data.get("bed", {})
    nozzle_temp = printer_data.get("tool0", {})

    # Extract job progress
    progress_data = job_data.get("progress", {})

    return {
        "timestamp": timestamp,
        "state": job_data.get("state", "unknown"),
        "progress": progress_data.get("completion"),
        "current_layer": None,  # OctoPrint API doesn't provide layer info directly
        "print_time_elapsed": job_data.get("progress", {}).get("printTime"),
        "print_time_remaining": job_data.get("progress", {}).get("printTimeLeft"),
        "bed_temp": {
            "current": bed_temp.get("actual"),
            "target": bed_temp.get("target"),
        },
        "nozzle_temp": {
            "current": nozzle_temp.get("actual"),
            "target": nozzle_temp.get("target"),
        },
    }


async def connect_to_printer(project_name: str) -> dict:
    """
    Test OctoPrint connection and validate API configuration.

    TICKET-016: OctoPrint API Integration - Connection and validation.

    Args:
        project_name: Name of the project

    Returns:
        {
            "status": "ok"|"error"|"pending",
            "octoprint_version": "string",
            "printer_connected": bool,
            "message": "string"
        }
    """
    logger.info(f"connect_to_printer called: project={project_name}")

    # Input validation
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("connect_to_printer: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string",
        }

    # Check API key
    if not OCTOPRINT_API_KEY:
        logger.warning("connect_to_printer: OCTOPRINT_API_KEY not set")
        return {
            "status": "error",
            "message": "OCTOPRINT_API_KEY environment variable not set",
        }

    try:
        session = _get_http_session()
        url = _octoprint_url("version")

        response = session.get(url, timeout=5)

        if response.status_code == 401:
            logger.error("connect_to_printer: authentication failed (401)")
            return {
                "status": "error",
                "message": "OctoPrint authentication failed. Check OCTOPRINT_API_KEY.",
            }

        if response.status_code != 200:
            logger.warning(
                f"connect_to_printer: unexpected status {response.status_code}"
            )
            return {
                "status": "pending",
                "message": f"OctoPrint not reachable at {OCTOPRINT_HOST}:{OCTOPRINT_PORT} (HTTP {response.status_code})",
            }

        version_data = response.json()

        # Get printer connection status
        printer_response = session.get(_octoprint_url("printer"), timeout=5)
        printer_connected = (
            printer_response.status_code == 200
            and printer_response.json().get("state", {}).get("operational", False)
        )

        logger.info(
            f"connect_to_printer: success - version={version_data.get('api', 'unknown')}, printer_connected={printer_connected}"
        )
        return {
            "status": "ok",
            "octoprint_version": version_data.get("api", "unknown"),
            "server_version": version_data.get("server", "unknown"),
            "printer_connected": printer_connected,
            "message": "Connected to OctoPrint successfully",
        }

    except requests.exceptions.ConnectionError:
        logger.warning(
            f"connect_to_printer: connection error to {OCTOPRINT_HOST}:{OCTOPRINT_PORT}"
        )
        return {
            "status": "pending",
            "message": f"Cannot reach OctoPrint at {OCTOPRINT_HOST}:{OCTOPRINT_PORT}",
        }
    except requests.exceptions.Timeout:
        logger.warning("connect_to_printer: timeout")
        return {
            "status": "pending",
            "message": "OctoPrint connection timeout (5s)",
        }
    except Exception as e:
        logger.error(f"connect_to_printer: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to connect to OctoPrint: {str(e)}",
        }


async def get_print_status(project_name: str) -> dict:
    """
    Query real-time printer and job status.

    TICKET-016/017: Monitors current print job progress, temperatures, and time estimates.

    Args:
        project_name: Name of the project

    Returns:
        {
            "status": "ok"|"error"|"pending",
            "timestamp": "ISO-8601",
            "state": "printing|paused|idle|...",
            "progress": 45.2,
            "current_layer": int|null,
            "print_time_elapsed": int|null (seconds),
            "print_time_remaining": int|null (seconds),
            "bed_temp": {"current": float, "target": float},
            "nozzle_temp": {"current": float, "target": float},
            "message": "string"
        }
    """
    logger.info(f"get_print_status called: project={project_name}")

    # Input validation
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("get_print_status: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string",
        }

    # Check API key
    if not OCTOPRINT_API_KEY:
        logger.warning("get_print_status: OCTOPRINT_API_KEY not set")
        return {
            "status": "error",
            "message": "OCTOPRINT_API_KEY environment variable not set",
        }

    try:
        session = _get_http_session()

        # Get printer state
        printer_response = session.get(_octoprint_url("printer"), timeout=5)
        if printer_response.status_code != 200:
            logger.warning(
                f"get_print_status: printer API returned {printer_response.status_code}"
            )
            return {
                "status": "pending",
                "message": f"OctoPrint not reachable (printer API returned {printer_response.status_code})",
            }

        printer_data = printer_response.json()

        # Get job progress
        job_response = session.get(_octoprint_url("job"), timeout=5)
        if job_response.status_code != 200:
            logger.warning(f"get_print_status: job API returned {job_response.status_code}")
            return {
                "status": "pending",
                "message": f"OctoPrint job query failed (HTTP {job_response.status_code})",
            }

        job_data = job_response.json()

        # Format and return status snapshot
        snapshot = _format_snapshot(printer_data, job_data)
        snapshot["status"] = "ok"
        snapshot["message"] = "Print status retrieved successfully"

        logger.info(f"get_print_status: success - state={snapshot['state']}, progress={snapshot['progress']}")
        return snapshot

    except requests.exceptions.ConnectionError:
        logger.warning(f"get_print_status: connection error to {OCTOPRINT_HOST}:{OCTOPRINT_PORT}")
        return {
            "status": "pending",
            "message": f"Cannot reach OctoPrint at {OCTOPRINT_HOST}:{OCTOPRINT_PORT}",
        }
    except requests.exceptions.Timeout:
        logger.warning("get_print_status: timeout")
        return {
            "status": "pending",
            "message": "OctoPrint status query timeout",
        }
    except Exception as e:
        logger.error(f"get_print_status: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to get print status: {str(e)}",
        }


async def collect_metrics(project_name: str, poll_count: int = 1) -> dict:
    """
    Collect and persist metric snapshots from the printer.

    TICKET-017: Real-time monitoring - metric collection with logging and storage.

    Args:
        project_name: Name of the project
        poll_count: Number of snapshots to collect (1-60), default 1

    Returns:
        {
            "status": "ok"|"error"|"pending",
            "snapshots_collected": int,
            "metrics_file": "path/to/metrics.jsonl",
            "message": "string"
        }
    """
    logger.info(f"collect_metrics called: project={project_name}, poll_count={poll_count}")

    # Input validation
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("collect_metrics: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string",
        }

    if not isinstance(poll_count, int) or poll_count < 1 or poll_count > 60:
        logger.warning(f"collect_metrics: invalid poll_count={poll_count}")
        return {
            "status": "error",
            "message": "poll_count must be an integer between 1 and 60",
        }

    try:
        snapshots_collected = 0

        # Collect snapshots
        for i in range(poll_count):
            status_result = await get_print_status(project_name)

            if status_result["status"] == "ok":
                # Save this snapshot to metrics
                snapshot = {k: v for k, v in status_result.items() if k != "message"}
                _save_metric(project_name, snapshot)
                snapshots_collected += 1
            elif status_result["status"] == "pending":
                # OctoPrint not reachable
                logger.warning(f"collect_metrics: OctoPrint unavailable on iteration {i+1}")
                if snapshots_collected == 0:
                    return {
                        "status": "pending",
                        "snapshots_collected": 0,
                        "message": status_result["message"],
                    }
            else:
                # Error
                logger.error(f"collect_metrics: error on iteration {i+1}: {status_result['message']}")
                if snapshots_collected == 0:
                    return {
                        "status": "error",
                        "snapshots_collected": 0,
                        "message": status_result["message"],
                    }

            # Brief delay between polls if collecting multiple
            if i < poll_count - 1:
                await asyncio.sleep(0.1)

        metrics_path = _get_monitor_dir(project_name) / "metrics.jsonl"
        logger.info(f"collect_metrics: collected {snapshots_collected} snapshots")

        return {
            "status": "ok",
            "snapshots_collected": snapshots_collected,
            "metrics_file": str(metrics_path),
            "message": f"Collected {snapshots_collected} metric snapshot(s)",
        }

    except Exception as e:
        logger.error(f"collect_metrics: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "snapshots_collected": 0,
            "message": f"Failed to collect metrics: {str(e)}",
        }


async def get_print_summary(project_name: str) -> dict:
    """
    Generate a summary report from collected metrics.

    TICKET-017: Real-time monitoring - periodic status summaries.

    Args:
        project_name: Name of the project

    Returns:
        {
            "status": "ok"|"error",
            "snapshot_count": int,
            "summary": {
                "avg_progress": float,
                "min_bed_temp": float,
                "max_bed_temp": float,
                "min_nozzle_temp": float,
                "max_nozzle_temp": float,
                "total_print_time": int (seconds),
                "estimated_remaining": int|null (seconds)
            },
            "message": "string"
        }
    """
    logger.info(f"get_print_summary called: project={project_name}")

    # Input validation
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("get_print_summary: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string",
        }

    try:
        metrics = _load_metrics(project_name)

        if not metrics:
            logger.info("get_print_summary: no metrics found")
            return {
                "status": "ok",
                "snapshot_count": 0,
                "summary": {
                    "avg_progress": None,
                    "min_bed_temp": None,
                    "max_bed_temp": None,
                    "min_nozzle_temp": None,
                    "max_nozzle_temp": None,
                    "total_print_time": None,
                    "estimated_remaining": None,
                },
                "message": "No metrics collected yet",
            }

        # Calculate summary statistics
        progress_values = [m.get("progress") for m in metrics if m.get("progress") is not None]
        bed_temps = [m.get("bed_temp", {}).get("current") for m in metrics if m.get("bed_temp", {}).get("current") is not None]
        nozzle_temps = [m.get("nozzle_temp", {}).get("current") for m in metrics if m.get("nozzle_temp", {}).get("current") is not None]
        print_times = [m.get("print_time_elapsed") for m in metrics if m.get("print_time_elapsed") is not None]
        remaining_times = [m.get("print_time_remaining") for m in metrics if m.get("print_time_remaining") is not None]

        summary = {
            "avg_progress": sum(progress_values) / len(progress_values) if progress_values else None,
            "min_bed_temp": min(bed_temps) if bed_temps else None,
            "max_bed_temp": max(bed_temps) if bed_temps else None,
            "min_nozzle_temp": min(nozzle_temps) if nozzle_temps else None,
            "max_nozzle_temp": max(nozzle_temps) if nozzle_temps else None,
            "total_print_time": max(print_times) if print_times else None,
            "estimated_remaining": remaining_times[-1] if remaining_times else None,
        }

        logger.info(f"get_print_summary: generated summary for {len(metrics)} snapshots")

        return {
            "status": "ok",
            "snapshot_count": len(metrics),
            "summary": summary,
            "message": f"Summary generated from {len(metrics)} metric snapshot(s)",
        }

    except Exception as e:
        logger.error(f"get_print_summary: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to generate summary: {str(e)}",
        }

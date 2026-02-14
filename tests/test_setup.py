"""Tests for project setup and acceptance criteria."""

import subprocess
import sys
import os


def test_imports_succeed():
    """Test that all top-level modules import without error."""
    try:
        import src
        import src.main
        import src.config
        import src.utils
        import src.agents
        import src.tools
        import src.services
    except ImportError as e:
        raise AssertionError(f"Failed to import module: {e}")


def test_config_loads():
    """Test that config loads with env vars set."""
    # Set required env var
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    try:
        # Reload the config module to pick up env var
        import importlib
        import src.config
        importlib.reload(src.config)

        assert src.config.ANTHROPIC_API_KEY == "test_key"
        assert src.config.LLM_MODEL is not None
        assert src.config.LOG_LEVEL is not None
        assert src.config.PROJECTS_DIR is not None
    finally:
        # Clean up
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]


def test_logging_setup():
    """Test that logging configures without error."""
    from src.utils import setup_logging

    try:
        setup_logging("DEBUG")
    except Exception as e:
        raise AssertionError(f"Logging setup failed: {e}")


def test_main_help():
    """Test that python src/main.py --help exits 0."""
    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = "test_key"

    result = subprocess.run(
        [sys.executable, "src/main.py", "--help"],
        capture_output=True,
        text=True,
        env=env
    )

    assert result.returncode == 0, f"Help command failed: {result.stderr}"
    assert "3D ADK" in result.stdout or "usage" in result.stdout.lower()

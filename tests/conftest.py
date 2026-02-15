"""Pytest configuration and fixtures for all tests."""

import os
import pytest

# Set required environment variables before any imports
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "claude-opus-4-6")
os.environ.setdefault("OCTOPRINT_HOST", "localhost")
os.environ.setdefault("OCTOPRINT_PORT", "5000")
os.environ.setdefault("OCTOPRINT_API_KEY", "test-api-key")
os.environ.setdefault("LOG_LEVEL", "INFO")

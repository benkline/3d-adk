"""Tests for performance tuning configuration constants."""

import pytest
from src import config


def test_sketch_prompt_cache_enabled_has_default():
    """Test that SKETCH_PROMPT_CACHE_ENABLED constant exists with correct type."""
    assert hasattr(config, "SKETCH_PROMPT_CACHE_ENABLED")
    assert isinstance(config.SKETCH_PROMPT_CACHE_ENABLED, bool)


def test_image_prompt_cache_enabled_has_default():
    """Test that IMAGE_PROMPT_CACHE_ENABLED constant exists with correct type."""
    assert hasattr(config, "IMAGE_PROMPT_CACHE_ENABLED")
    assert isinstance(config.IMAGE_PROMPT_CACHE_ENABLED, bool)


def test_openscad_output_cache_enabled_has_default():
    """Test that OPENSCAD_OUTPUT_CACHE_ENABLED constant exists with correct type."""
    assert hasattr(config, "OPENSCAD_OUTPUT_CACHE_ENABLED")
    assert isinstance(config.OPENSCAD_OUTPUT_CACHE_ENABLED, bool)


def test_octoprint_poll_interval_has_default():
    """Test that OCTOPRINT_POLL_INTERVAL_S constant exists with correct type and default."""
    assert hasattr(config, "OCTOPRINT_POLL_INTERVAL_S")
    assert isinstance(config.OCTOPRINT_POLL_INTERVAL_S, float)
    assert config.OCTOPRINT_POLL_INTERVAL_S == 5.0  # default value


def test_metrics_window_size_has_default():
    """Test that METRICS_WINDOW_SIZE constant exists with correct type and default."""
    assert hasattr(config, "METRICS_WINDOW_SIZE")
    assert isinstance(config.METRICS_WINDOW_SIZE, int)
    assert config.METRICS_WINDOW_SIZE == 500  # default value

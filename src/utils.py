"""Logging setup and shared utilities."""

import logging
from src.config import LOG_LEVEL


def setup_logging(level=None):
    """Configure root logger with consistent format.

    Args:
        level: Log level (defaults to config value)
    """
    if level is None:
        level = LOG_LEVEL

    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(name)s: %(message)s"
    )

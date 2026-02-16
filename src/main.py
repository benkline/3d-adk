"""Main entry point for 3D ADK."""

import sys
import os
import argparse
import logging

# Add parent directory to path to enable imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import __version__
from src.utils import setup_logging
from src.config import (
    LLM_MODEL,
    OCTOPRINT_HOST,
    OCTOPRINT_PORT,
    LOG_LEVEL,
    PROJECTS_DIR,
)


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="3D ADK - AI-Driven Mechanical Design Kit for 3D Printing",
        prog="3d-adk"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Start in interactive mode (default if no other action is specified)"
    )
    parser.add_argument(
        "--project",
        type=str,
        help="Project name or session ID to load (requires --interactive)"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Print welcome banner
    print(f"\n{'='*60}")
    print(f"3D ADK v{__version__}")
    print(f"{'='*60}\n")

    # Print configuration summary
    logger.info(f"LLM Model: {LLM_MODEL}")
    logger.info(f"OctoPrint Host: {OCTOPRINT_HOST}:{OCTOPRINT_PORT}")
    logger.info(f"Log Level: {LOG_LEVEL}")
    logger.info(f"Projects Directory: {PROJECTS_DIR}")
    print()

    # Start interactive CLI if requested (or default behavior if no args)
    if args.interactive or (not args.project and len(sys.argv) == 1):
        from src.cli import CLI

        cli = CLI(session_id=args.project)
        cli.run()


if __name__ == "__main__":
    main()

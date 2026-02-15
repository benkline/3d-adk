"""Configuration loader from environment variables."""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Required configuration keys
REQUIRED_KEYS = ["ANTHROPIC_API_KEY"]

# Core API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-opus-4-6")

# OctoPrint Configuration
OCTOPRINT_HOST = os.getenv("OCTOPRINT_HOST", "localhost")
OCTOPRINT_PORT = os.getenv("OCTOPRINT_PORT", "5000")
OCTOPRINT_API_KEY = os.getenv("OCTOPRINT_API_KEY")

# OpenSCAD Configuration
OPENSCAD_PATH = os.getenv("OPENSCAD_PATH", "/usr/local/bin/openscad")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Projects Directory
PROJECTS_DIR = os.getenv("PROJECTS_DIR", "./projects")

# Sessions Directory
SESSIONS_DIR = os.getenv("SESSIONS_DIR", "./sessions")

# Material Cost Configuration
FILAMENT_COST_PER_KG = float(os.getenv("FILAMENT_COST_PER_KG", "25.0"))  # USD

# Validate required keys
missing_keys = [key for key in REQUIRED_KEYS if not os.getenv(key)]
if missing_keys:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(missing_keys)}. "
        f"Please create a .env file with these keys or set them as environment variables."
    )

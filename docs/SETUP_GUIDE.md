# Setup Guide

Complete setup instructions for the 3D-ADK system. This guide covers prerequisites, installation, configuration, and verification.

## Prerequisites

- **Python:** 3.9 or later
- **OpenSCAD:** Required for the Modeling phase (3D model generation)
- **Virtual Environment:** We use `~/.venvs/3d-adk` for isolated dependencies
- **OctoPrint:** Optional, required only if using the Monitor phase

## Installation Steps

### 1. Create Virtual Environment

```bash
mkdir -p ~/.venvs
python3 -m venv ~/.venvs/3d-adk
```

(First time only. The directory `~/.venvs/3d-adk` can also be referenced by the `venv-adk` alias if configured in your shell.)

### 2. Activate Environment

```bash
source ~/.venvs/3d-adk/bin/activate
```

On Windows (PowerShell):
```powershell
~\.venvs\3d-adk\Scripts\Activate.ps1
```

### 3. Install Python Dependencies

```bash
cd ~/Projects/3d-adk
pip install -r requirements.txt
```

This installs all Python packages including Google ADK, Claude SDK, OctoPrint client, and testing tools.

### 4. Install OpenSCAD

OpenSCAD is required for the Modeling phase (3D model generation and rendering).

**macOS (Homebrew):**

Intel Mac:
```bash
brew install openscad
```

Apple Silicon Mac:
```bash
brew install openscad  # Same command; Homebrew handles universal binaries
```

After installation, verify the path:
```bash
which openscad
# Should output: /usr/local/bin/openscad (Intel) or /opt/homebrew/bin/openscad (Apple Silicon)
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install openscad
# Typical path: /usr/bin/openscad
```

**Windows (Chocolatey):**
```powershell
choco install openscad
# Typical path: C:\Program Files\OpenSCAD\openscad.exe
```

### 5. Create Configuration File

```bash
cp .env.example .env
```

Then edit `.env` with your settings (see Configuration section below).

### 6. Verify Installation

Check that everything is installed correctly:

```bash
# Python setup
python --version        # Should be 3.9+
which python            # Should be in ~/.venvs/3d-adk

# OpenSCAD setup
which openscad          # Should find the OpenSCAD binary
openscad --version      # Should print version without error

# Application setup
python src/main.py --help         # Should display usage without errors
```

## Configuration

All configuration is via environment variables in the `.env` file. Copy `.env.example` and fill in required values.

### Required Settings

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `ANTHROPIC_API_KEY` | string | Claude API key from console.anthropic.com | `sk-ant-...` |

### Important Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LLM_MODEL` | string | `claude-opus-4-6` | Which Claude model to use. Use `claude-opus-4-6` for best results. |
| `OPENSCAD_PATH` | string | `/usr/local/bin/openscad` | Full path to OpenSCAD binary. **Check with `which openscad` after installation.** |
| `OCTOPRINT_HOST` | string | `localhost` | Hostname or IP of OctoPrint server. Required for Monitor phase. |
| `OCTOPRINT_PORT` | int | `5000` | Port for OctoPrint API. |
| `OCTOPRINT_API_KEY` | string | (none) | OctoPrint authentication key. Required for Monitor phase. Generate in OctoPrint settings. |

### Optional Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | string | `INFO` | Python logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `PROJECTS_DIR` | string | `./projects` | Directory to store design/model files. Will be created if missing. |
| `SESSIONS_DIR` | string | `./sessions` | Directory to store project session state. Will be created if missing. |
| `FILAMENT_COST_PER_KG` | float | `25.0` | Material cost per kilogram (USD). Used for print cost estimation. |
| `FILAMENT_G_PER_HOUR` | float | `8.0` | Filament consumption rate (grams/hour). Used for print time estimation. |

### Configuration Example

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_MODEL=claude-opus-4-6

# OpenSCAD - important to verify path for your system
OPENSCAD_PATH=/usr/local/bin/openscad

# OctoPrint (required for Monitor phase)
OCTOPRINT_HOST=192.168.1.100
OCTOPRINT_PORT=5000
OCTOPRINT_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional
LOG_LEVEL=INFO
PROJECTS_DIR=./projects
SESSIONS_DIR=./sessions
FILAMENT_COST_PER_KG=25.0
```

## Common Configuration Issues

### OpenSCAD Path

If you get "OpenSCAD not found" errors, the path in `OPENSCAD_PATH` is incorrect:

```bash
# Find the correct path
which openscad

# Then update OPENSCAD_PATH in .env to match
```

Platform differences:
- Intel Mac: `/usr/local/bin/openscad`
- Apple Silicon Mac: `/opt/homebrew/bin/openscad`
- Linux (Ubuntu): `/usr/bin/openscad`
- Windows: `C:\Program Files\OpenSCAD\openscad.exe`

### OctoPrint Connection

If Monitor phase tools return "Cannot connect to OctoPrint":

1. Verify OctoPrint is running: `http://<OCTOPRINT_HOST>:5000` in browser
2. Verify `OCTOPRINT_API_KEY` is correct (generate a new one in OctoPrint web settings if needed)
3. Check firewall rules allow connection to the OctoPrint port

## Running the Application

### Interactive Mode (Default)

```bash
python src/main.py
```

Shows the interactive CLI prompt. Type `help` for available commands.

### With Specific Project

Load a previously created project on startup:

```bash
python src/main.py --project <session_id>
```

Or to load by project name:

```bash
python src/main.py
# Then: resume
# Select project from list
```

### Run Tests

Full test suite:
```bash
pytest
```

Specific test file:
```bash
pytest tests/test_setup.py -v
```

Single test:
```bash
pytest tests/test_setup.py::test_name -v
```

## Directory Structure

After running the application, the following directories are created:

```
projects/                           # PROJECTS_DIR setting
├── <project_name>/
│   ├── design/
│   │   ├── interview.json
│   │   ├── sketches/
│   │   ├── images/
│   │   ├── design_specs.json
│   │   └── blueprint.md
│   ├── model/
│   │   ├── project.scad
│   │   ├── previews/
│   │   ├── model.stl
│   │   ├── model.3mf
│   │   └── analysis.json
│   └── print/
│       ├── metrics.jsonl
│       ├── issues.json
│       └── quality_assessment.json
│
sessions/                           # SESSIONS_DIR setting
└── <session_id>.json              # Project session state
```

## Next Steps

- **Get Started:** Run `python src/main.py` to launch the interactive CLI
- **Development:** See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for contribution workflow
- **Troubleshooting:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- **Workflows:** See [WORKFLOW.md](WORKFLOW.md) to understand the 3-phase process
- **Implementation:** Check [../tickets.md](../tickets.md) for active work items

## Troubleshooting Setup Issues

For problems during or after setup, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) which covers:
- Module import errors
- API key validation
- OpenSCAD path issues
- OctoPrint connection problems
- Test failures

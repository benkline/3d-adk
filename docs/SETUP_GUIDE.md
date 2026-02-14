# Setup Guide

## Prerequisites

- Python 3.9+
- Virtual environment at `~/.venvs/3d-adk`

## Installation Steps

1. **Create virtual environment** (first time only):
   ```bash
   mkdir -p ~/.venvs
   python3 -m venv ~/.venvs/3d-adk
   ```

2. **Activate environment:**
   ```bash
   source ~/.venvs/3d-adk/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   cd ~/Projects/3d-adk
   pip install -r requirements.txt
   ```

4. **Create configuration:**
   ```bash
   cp .env.example .env
   ```

5. **Configure API keys in `.env`:**
   - `ANTHROPIC_API_KEY` - Claude API key
   - `OCTOPRINT_HOST` - Printer IP/hostname (monitor phase)
   - `OCTOPRINT_API_KEY` - OctoPrint authentication (monitor phase)

## Verify Installation

```bash
python src/main.py --help
```

Should display help without errors. You can also run:

```bash
python src/main.py
```

To see the banner and current configuration summary.

## Output Directories

The application will create the following directory at runtime:

- `projects/` - Output directory for design artifacts and session data (configurable via `PROJECTS_DIR` in `.env`)

## Running Tests

```bash
pytest tests/test_setup.py -v
```

All acceptance tests should pass with a green checkmark.

## Next Steps

- See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for development workflow
- Check [../tickets.md](../tickets.md) for implementation work
- Review relevant spec in `specs/` before starting a ticket

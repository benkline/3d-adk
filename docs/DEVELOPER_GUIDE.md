# Developer Guide

Complete guide for developing features in the 3D-ADK system.

## Quick Start

1. **Activate virtual environment:**
   ```bash
   source ~/.venvs/3d-adk/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit with your API keys
   ```

4. **Verify setup:**
   ```bash
   pytest tests/test_setup.py -v
   ```

## Using the Ticket System

This project uses a ticket-driven workflow. Work through tickets in order:

```bash
/next-ticket TICKET-XXX
```

This skill:
1. Loads the ticket from `planning/tickets.md`
2. Creates a git worktree for isolated work
3. Guides you through planning and implementation
4. Runs tests to validate work
5. Helps create a pull request

**Each ticket includes:**
- Clear description of what to build
- Acceptance criteria for validation
- Links to relevant specification files
- Task list (checklist style)
- Testing instructions

## Development Patterns

### Agent Development

Agents are instances of `google.adk.agents.LlmAgent` with specialized tools. Each agent:
- Has a unique name and purpose
- Implements 4-15 tool functions
- Uses `InvocationContext` to access services
- Receives structured input and returns structured dicts

**Location:** `src/agents/`

**Pattern:**
```python
from google.adk.agents import LlmAgent, FunctionTool
from src.tools import coordinator_tools

# Create agent with FunctionTool-wrapped functions
coordinator_agent = LlmAgent(
    name="coordinator",
    instructions="Orchestrate the 3D printing workflow...",
    tools=[
        FunctionTool(coordinator_tools.create_project_session),
        FunctionTool(coordinator_tools.get_project_status),
        # ... more tools
    ]
)
```

### Tool Functions (The FunctionTool Pattern)

Tools are async functions that wrap business logic. The `FunctionTool` wrapper converts them to Google ADK tools.

**Key characteristics:**
- Async function: `async def my_tool(...) -> dict:`
- Type hints: All parameters and return value typed
- Error handling: Return `{"status": "error", "message": "..."}` instead of raising
- Validation: Check inputs and return error dict if invalid
- Logging: Use `logging.info()` / `logging.error()` for debugging
- Response format: Always return dict with `"status"` key ("ok" or "error")

**Example tool:**

```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def create_project_session(project_name: str) -> dict:
    """
    Create a new project session.

    Args:
        project_name: Name of the project (required, non-empty)

    Returns:
        Dict with status, session_id (if ok), and message (if error)
    """
    # Input validation
    if not project_name or not isinstance(project_name, str):
        return {
            "status": "error",
            "message": "project_name must be a non-empty string"
        }

    logger.info(f"Creating project session: {project_name}")

    try:
        # Implementation logic here
        session_id = "abc123..."

        logger.info(f"Created session {session_id}")

        return {
            "status": "ok",
            "session_id": session_id,
            "project_name": project_name,
            "current_phase": "design"
        }
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        return {
            "status": "error",
            "message": f"Failed to create session: {str(e)}"
        }
```

**Registering the tool in an agent:**

```python
from google.adk.agents import FunctionTool

coordinator_agent = LlmAgent(
    name="coordinator_agent",
    instructions="...",
    tools=[
        FunctionTool(coordinator_tools.create_project_session),
        FunctionTool(coordinator_tools.get_project_status),
        # More tools...
    ]
)
```

### Testing Tools

Tests follow the source structure in `tests/`.

**Test pattern for a tool:**

```python
import pytest
from src.tools import coordinator_tools

@pytest.mark.asyncio
async def test_create_project_session_success():
    """Test successful session creation."""
    result = await coordinator_tools.create_project_session("test_project")

    assert result["status"] == "ok"
    assert result["session_id"]  # Should be non-empty
    assert result["project_name"] == "test_project"
    assert result["current_phase"] == "design"

@pytest.mark.asyncio
async def test_create_project_session_invalid_input():
    """Test that invalid input returns error dict."""
    result = await coordinator_tools.create_project_session("")  # Empty string

    assert result["status"] == "error"
    assert "message" in result
```

**Key testing practices:**
- Use `@pytest.mark.asyncio` for async test functions
- Test both success and failure paths
- Mock external services (OctoPrint, file I/O)
- Use temporary directories for file I/O tests (`tmp_path` fixture)
- Aim for >80% code coverage
- Test error messages, not just error paths

## Code Standards

### Formatting

Use `black` for code formatting:

```bash
# Format all code
black src/ tests/

# Check without formatting
black --check src/ tests/
```

### Linting

Check code quality with `flake8`:

```bash
flake8 src/ tests/
```

### Type Hints

All functions must have type hints:

```python
async def my_function(
    input_str: str,
    input_int: int,
    input_optional: Optional[str] = None
) -> dict:
    """Function docstring."""
    ...
```

### Documentation

Include docstrings for all public functions:

```python
async def analyze_printability(model_file: str) -> dict:
    """
    Analyze 3D model for printability issues.

    Args:
        model_file: Path to STL file

    Returns:
        Dict with analysis results
    """
```

## Environment Variables

All configuration via environment variables (loaded from `.env`).

**Access in code:**

```python
import os
from src.config import (
    ANTHROPIC_API_KEY,
    LLM_MODEL,
    OPENSCAD_PATH,
    OCTOPRINT_HOST,
    OCTOPRINT_API_KEY,
)

# Or directly from os.environ
api_key = os.environ.get("ANTHROPIC_API_KEY")
```

**All available variables:**

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `ANTHROPIC_API_KEY` | str | Yes | (none) | Claude API key |
| `LLM_MODEL` | str | No | `claude-opus-4-6` | Model to use for all LLM calls |
| `OPENSCAD_PATH` | str | No | `/usr/local/bin/openscad` | Path to OpenSCAD binary |
| `OCTOPRINT_HOST` | str | No | `localhost` | OctoPrint hostname |
| `OCTOPRINT_PORT` | int | No | `5000` | OctoPrint port |
| `OCTOPRINT_API_KEY` | str | No | (none) | OctoPrint API key (required for Monitor phase) |
| `LOG_LEVEL` | str | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `PROJECTS_DIR` | str | No | `./projects` | Directory for design/model files |
| `SESSIONS_DIR` | str | No | `./sessions` | Directory for session state |
| `FILAMENT_COST_PER_KG` | float | No | `25.0` | Cost per kg (USD) |
| `FILAMENT_G_PER_HOUR` | float | No | `8.0` | Filament consumption rate |

## Running Tests

### Full Test Suite

```bash
pytest
```

### With Coverage

```bash
pytest --cov=src --cov-report=term-missing tests/
```

### Specific Test File

```bash
pytest tests/test_coordinator.py -v
```

### Specific Test Function

```bash
pytest tests/test_coordinator.py::test_create_project_session -v
```

### With Debug Output

```bash
pytest -vv -s tests/test_coordinator.py
```

The `-s` flag shows `print()` and `logging` output.

## Contribution Workflow

### Branch Naming

Create branches for features using the ticket system:

```bash
git checkout -b feature/TICKET-028
```

Or the git worktree created by `/next-ticket` does this automatically.

### Making Changes

1. **Implement feature** - Write code in worktree
2. **Write tests** - Add comprehensive tests (>80% coverage)
3. **Format code** - Run `black src/ tests/`
4. **Check linting** - Run `flake8 src/ tests/`
5. **Run tests** - Run `pytest` to verify all tests pass
6. **Update docs** - Update `docs/API_REFERENCE.md` if adding public APIs

### Creating a Pull Request

The `/next-ticket` skill handles this, but manual process:

```bash
git add src/ tests/ docs/
git commit -m "[TICKET-028] Add documentation

- Expand ARCHITECTURE.md with diagrams
- Add configuration guide to SETUP_GUIDE.md
- Create example projects
- Update API_REFERENCE.md table of contents

Fixes #028"

git push origin feature/TICKET-028

# Create PR via GitHub CLI
gh pr create \
  --title "[TICKET-028] Add documentation" \
  --body "Completes the Polish phase with comprehensive docs"
```

## End-to-End Development Example

**Scenario:** Adding a new tool to the Design Agent

### 1. Plan the feature

- Tool name: `refine_design`
- Purpose: User requests refinements to design
- Input: `session_id`, `feedback_text`
- Output: Updated `design_specs.json`

### 2. Write tests first (TDD)

Create `tests/test_design_tools.py` (or add to existing):

```python
import pytest
from src.tools import design_tools

@pytest.mark.asyncio
async def test_refine_design_success(tmp_path, monkeypatch):
    """Test design refinement."""
    # Setup
    monkeypatch.setenv("PROJECTS_DIR", str(tmp_path))

    # Execute
    result = await design_tools.refine_design(
        session_id="test123",
        feedback_text="Make it more modern"
    )

    # Assert
    assert result["status"] == "ok"
    assert "updated_specs" in result
```

### 3. Implement the tool

Add to `src/tools/design_tools.py`:

```python
async def refine_design(session_id: str, feedback_text: str) -> dict:
    """Refine design based on user feedback."""
    # Validation
    if not session_id or not feedback_text:
        return {"status": "error", "message": "Missing required inputs"}

    # Implementation
    logger.info(f"Refining design for {session_id}")

    # ... logic to update design_specs.json ...

    return {"status": "ok", "updated_specs": { ... }}
```

### 4. Register in agent

Update `src/agents/design.py`:

```python
design_agent = LlmAgent(
    name="design_agent",
    instructions="...",
    tools=[
        FunctionTool(design_tools.conduct_interview),
        FunctionTool(design_tools.generate_sketches),
        FunctionTool(design_tools.generate_images),
        FunctionTool(design_tools.generate_blueprint),
        FunctionTool(design_tools.refine_design),  # NEW
    ]
)
```

### 5. Update documentation

Add to `docs/API_REFERENCE.md` under Design Agent section:

```markdown
#### `refine_design(session_id: str, feedback_text: str) -> dict`
Refine design based on user feedback.

**Parameters:**
- `session_id` (str): Session to refine
- `feedback_text` (str): User feedback text

**Returns:** dict with `status`, `updated_specs`

**Example:**
```python
result = await refine_design("abc123", "Make it more modern")
```
```

### 6. Run tests

```bash
pytest tests/test_design_tools.py -v
```

### 7. Create PR

```bash
git add src/ tests/ docs/
git commit -m "[TICKET-XXX] Add design refinement tool"
git push origin feature/TICKET-XXX
gh pr create --title "[TICKET-XXX] Add design refinement tool"
```

## Useful Commands

```bash
# Activate venv
source ~/.venvs/3d-adk/bin/activate

# Run app interactively
python src/main.py

# Run specific test
pytest tests/test_coordinator.py::test_create_project_session -v

# Check test coverage
pytest --cov=src --cov-report=html

# Format code
black src/ tests/

# Check linting
flake8 src/ tests/

# Get next ticket
/next-ticket --list
```

## Troubleshooting Development

**Import errors:** Ensure venv is activated and dependencies installed
```bash
source ~/.venvs/3d-adk/bin/activate
pip install -r requirements.txt
```

**Tests fail:** Check that all env vars are set
```bash
pytest -vv  # Verbose output
```

**Type errors:** Use type hints and mypy (optional)
```bash
pip install mypy
mypy src/
```

## Next Steps

- Review [ARCHITECTURE.md](ARCHITECTURE.md) to understand system structure
- Check [../tickets.md](../tickets.md) for available work
- Start with `/next-ticket TICKET-XXX` to begin implementation
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues

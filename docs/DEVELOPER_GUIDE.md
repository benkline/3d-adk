# Developer Guide

## Quick Start

1. **Activate venv:**
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

## Using Tickets

Work through tickets in order using `/next-ticket` skill:
- Shows next available ticket
- Guides implementation
- Runs tests
- Updates documentation

Each ticket includes acceptance criteria, task list, and testing instructions.

## Development Patterns

- **Agents** - Inherit from `LlmAgent`, located in `src/agents/`
- **Tools** - Inherit from `BaseTool`, grouped by domain in `src/tools/`
- **Services** - Implement base service interfaces in `src/services/`
- **Tests** - Mirror source structure in `tests/`

## Code Standards

```bash
# Format with black
black src/ tests/

# Check with flake8
flake8 src/ tests/
```

Use type hints and docstrings. See ticket-specific specs for implementation patterns.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_agents.py::TestDesignAgent
```

## Documentation Updates

When completing a ticket, update `docs/API_REFERENCE.md`:
- Add new agents/tools/services
- Include method signatures
- Add usage examples

**For detailed patterns:** See [../specs/ADK_IMPLEMENTATION_SPEC.md](../specs/ADK_IMPLEMENTATION_SPEC.md)

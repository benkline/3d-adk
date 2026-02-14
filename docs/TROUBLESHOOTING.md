# Troubleshooting

## Common Issues

### Import Errors
**Error:** `ModuleNotFoundError: No module named 'adk'`

**Solution:** Ensure virtual environment is activated and dependencies installed:
```bash
source ~/.venvs/3d-adk/bin/activate
pip install -r requirements.txt
```

### API Key Issues
**Error:** `Anthropic API key not found` or OctoPrint connection fails

**Solution:** Check `.env` file has valid API keys:
```bash
grep ANTHROPIC_API_KEY .env
grep OCTOPRINT .env
```

### Tests Fail
**Error:** Tests not running or all failing

**Solution:**
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run with verbose output
pytest -v tests/
```

### Virtual Environment Issues
**Error:** `venv-adk` alias not working

**Solution:** Activate venv directly:
```bash
source ~/.venvs/3d-adk/bin/activate
```

## Getting Help

1. **Check the relevant spec** - Most implementation guidance is in `specs/`
2. **Review test examples** - Tests show usage patterns
3. **Check ticket acceptance criteria** - Details what should be implemented
4. **Run with debug logging** - Add logging to see what's happening

## Common Development Tasks

### Starting a new ticket
1. Review ticket in `tickets.md`
2. Check its spec file (e.g., `DESIGN_AGENT_SPEC.md`)
3. Use `/next-ticket` skill for guided workflow

### Adding a new tool
1. Create tool class in `src/tools/{category}_tools.py`
2. Inherit from `BaseTool`
3. Implement `run_async()` method
4. Add to agent's tool list
5. Update `docs/API_REFERENCE.md`

### Debugging agent execution
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now run agent with debug output
```

---

For component-specific issues, see the relevant spec file.

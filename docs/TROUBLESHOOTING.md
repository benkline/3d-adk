# Troubleshooting Guide

Solutions for common problems when installing, configuring, or developing 3D-ADK.

## Installation & Setup Issues

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'adk'` or `No module named 'src'`

**Causes:**
- Virtual environment not activated
- Dependencies not installed
- Wrong working directory

**Solutions:**
```bash
# 1. Activate virtual environment
source ~/.venvs/3d-adk/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify working directory
pwd  # Should be the project root (~/Projects/3d-adk)

# 4. Try again
python src/main.py --help
```

### OpenSCAD Not Found

**Error:** `openscad: command not found` or `No such file or directory`

**Causes:**
- OpenSCAD not installed
- `OPENSCAD_PATH` environment variable is wrong
- OpenSCAD binary is in different location than expected

**Solutions:**

1. **Verify OpenSCAD is installed:**
   ```bash
   which openscad
   ```
   If nothing returns, install it (see SETUP_GUIDE.md).

2. **Update OPENSCAD_PATH in .env:**
   ```bash
   # Find where OpenSCAD actually is
   which openscad

   # Update .env with that path
   # Edit .env and set:
   OPENSCAD_PATH=/path/to/openscad
   ```

3. **Platform-specific paths:**
   - Intel Mac: `/usr/local/bin/openscad`
   - Apple Silicon Mac: `/opt/homebrew/bin/openscad`
   - Linux (Ubuntu): `/usr/bin/openscad`
   - Windows: `C:\Program Files\OpenSCAD\openscad.exe`

4. **Test OpenSCAD directly:**
   ```bash
   /path/to/openscad --version
   # Should print version without errors
   ```

### API Key Issues

**Error:** `Anthropic API key not found` or `Invalid API key`

**Causes:**
- `ANTHROPIC_API_KEY` not set in `.env`
- Typo or incomplete API key
- Key doesn't have proper permissions

**Solutions:**
```bash
# 1. Check .env exists and has the key
grep ANTHROPIC_API_KEY .env

# 2. Verify it's not empty
cat .env | grep ANTHROPIC_API_KEY  # Should show: ANTHROPIC_API_KEY=sk-ant-...

# 3. Get a fresh key from console.anthropic.com if needed
```

### Tests Fail to Run

**Error:** `ModuleNotFoundError` or `ImportError` when running tests

**Causes:**
- Test dependencies not installed
- PYTHONPATH not set correctly
- Working directory not correct

**Solutions:**
```bash
# 1. Install test dependencies explicitly
pip install pytest pytest-asyncio pytest-cov

# 2. Run from project root directory
cd ~/Projects/3d-adk

# 3. Run tests with verbose output to see what's failing
pytest -vv tests/test_setup.py

# 4. Check specific test
pytest tests/test_setup.py::test_app_starts -v
```

### Virtual Environment Issues

**Error:** Command not found or venv commands not working

**Causes:**
- Venv not activated
- Shell doesn't have the alias configured
- Zsh vs bash path issues

**Solutions:**
```bash
# 1. Activate venv directly (most reliable)
source ~/.venvs/3d-adk/bin/activate

# 2. If using bash instead of zsh:
source ~/.venvs/3d-adk/bin/activate  # Same command works

# 3. Verify activation
which python  # Should show ~/.venvs/3d-adk/...
python --version  # Should be 3.9+

# 4. To create an alias (add to ~/.zshrc or ~/.bashrc):
# echo "alias venv-adk='source ~/.venvs/3d-adk/bin/activate'" >> ~/.zshrc
```

## Runtime Issues

### OctoPrint Connection Failures

**Error:** `Cannot connect to OctoPrint at {host}:{port}` or `401 Unauthorized`

**Causes:**
- OctoPrint not running or wrong host/port
- API key is invalid or missing
- Firewall blocking connection
- SSL/HTTPS issues

**Solutions:**

1. **Verify OctoPrint is running:**
   ```bash
   # Try to access via browser
   http://192.168.1.100:5000/  # Replace with your IP/port

   # Should show OctoPrint web interface (login page or dashboard)
   ```

2. **Check host and port in .env:**
   ```bash
   grep OCTOPRINT .env
   # Should show:
   # OCTOPRINT_HOST=192.168.1.100
   # OCTOPRINT_PORT=5000
   ```

3. **Verify API key:**
   - Log into OctoPrint web interface
   - Go to Settings → API → API key
   - Copy the key and update OCTOPRINT_API_KEY in .env
   - Verify it's the **Application key**, not the API announcement key

4. **Test connection manually:**
   ```bash
   # Test with curl (replace IP, port, key)
   curl -X GET \
     http://192.168.1.100:5000/api/version \
     -H "X-API-Key: YOUR_API_KEY_HERE"

   # Should return JSON with version info, not 401/403 error
   ```

5. **Firewall issues:**
   - Check firewall allows connections to OctoPrint port (5000)
   - If accessing from different subnet, verify network routing
   - If OctoPrint is on HTTPS, update host to `https://192.168.1.100:5000`

### Phase Transition Errors

**Error:** `Cannot advance to {phase}` or `Transition not allowed`

**Causes:**
- Phase gates/preconditions not met
- State corruption or missing flags
- Trying to go backwards to an earlier phase

**Solutions:**

1. **Understand phase transition guards:**
   - Design → Modeling: Requires `design_approved = True`
   - Modeling → Monitor: Requires `model_exported = True`
   - Backtrack to earlier phase: Generally allowed unless print has started

2. **Check current status:**
   ```bash
   # In CLI
   status
   # Shows: current_phase, design_approved, model_exported, print_started
   ```

3. **Complete required steps before advancing:**
   - Design phase: Conductor must approve design before you can advance
   - Modeling phase: Model must be exported before Monitor phase

4. **Reset a stuck project:**
   If session state is corrupted, you may need to restart:
   ```bash
   # List sessions
   resume

   # Delete the corrupted session folder
   rm -rf sessions/{session_id}.json
   rm -rf projects/{project_name}/

   # Create a new session
   new my_project
   ```

### Session/State Issues

**Error:** `Session not found` or `Cannot load project state`

**Causes:**
- Session ID is invalid or was deleted
- Session file corrupted
- Working directory changed
- SESSIONS_DIR or PROJECTS_DIR misconfigured

**Solutions:**

1. **List available sessions:**
   ```bash
   # In CLI
   resume
   # Shows all available sessions with IDs
   ```

2. **Check session directory:**
   ```bash
   ls -la sessions/
   # Should show .json files for each session
   ```

3. **Verify config paths:**
   ```bash
   grep SESSIONS_DIR .env
   grep PROJECTS_DIR .env

   # Make sure directories exist
   mkdir -p projects/ sessions/
   ```

4. **Inspect session state (debugging):**
   ```bash
   cat sessions/{session_id}.json | python -m json.tool
   # Shows the actual session structure
   ```

## Development & Testing Issues

### Tests Fail with Async Errors

**Error:** `RuntimeError: Event loop is closed` or `asyncio` errors

**Causes:**
- Missing `@pytest.mark.asyncio` decorator
- Async fixtures not set up correctly
- Event loop cleanup issues

**Solutions:**

1. **Ensure test is marked async:**
   ```python
   import pytest

   @pytest.mark.asyncio  # This is required!
   async def test_my_async_function():
       result = await my_async_function()
       assert result
   ```

2. **Use conftest.py fixtures (already set up):**
   ```python
   @pytest.mark.asyncio
   async def test_with_fixture(tmp_path):
       # tmp_path is provided by pytest
       ...
   ```

3. **If using mocking:**
   ```python
   from unittest.mock import patch, AsyncMock

   @pytest.mark.asyncio
   async def test_with_mock():
       with patch('src.tools.module.function', new_callable=AsyncMock) as mock:
           mock.return_value = {"status": "ok"}
           result = await my_function()
   ```

### Code Formatting Errors

**Error:** Tests fail on `black` or `flake8` checks

**Causes:**
- Code not formatted with `black`
- Linting errors in `flake8`
- Type hints missing

**Solutions:**

1. **Auto-format with black:**
   ```bash
   black src/ tests/
   # This will reformat all files in-place
   ```

2. **Check what flake8 complains about:**
   ```bash
   flake8 src/ tests/
   # Shows line-by-line errors
   ```

3. **Common flake8 fixes:**
   - Remove unused imports: `isort src/ tests/`
   - Fix line length: Use black (handles automatically)
   - Add type hints to all functions

### Coverage Too Low

**Error:** `Coverage is below threshold` or `Need >80% coverage`

**Causes:**
- Not all code paths tested
- Dead code or untested functions
- Missing edge case tests

**Solutions:**

1. **Check coverage report:**
   ```bash
   pytest --cov=src --cov-report=html tests/
   # Opens browser with detailed coverage report
   ```

2. **Look for missing lines:**
   - Report shows which lines aren't covered (red lines)
   - Add tests for those lines

3. **Test both success and failure:**
   ```python
   # Success path
   async def test_function_success():
       result = await function(valid_input)
       assert result["status"] == "ok"

   # Failure path
   async def test_function_error():
       result = await function(invalid_input)
       assert result["status"] == "error"
   ```

## Google ADK & Model Issues

### Agent Model Not Found

**Error:** `Model not found` or `Invalid model: {model_name}`

**Causes:**
- `LLM_MODEL` env var points to invalid model
- API credentials don't have access to requested model

**Solutions:**

1. **Check which model is configured:**
   ```bash
   grep LLM_MODEL .env
   # Should be a valid Claude model like:
   # claude-opus-4-6, claude-sonnet-4-5, claude-haiku-4-5
   ```

2. **Verify API key has model access:**
   - Log into console.anthropic.com
   - Check which models are available in your plan

3. **Use a stable model:**
   ```bash
   # In .env, use latest stable model
   LLM_MODEL=claude-opus-4-6
   ```

### Tool Registration Errors

**Error:** `Tool not registered` or `Tool not callable`

**Causes:**
- `FunctionTool` wrapper not applied to async function
- Tool name conflicts
- Tool function signature doesn't match expectations

**Solutions:**

1. **Verify tool is wrapped:**
   ```python
   from google.adk.agents import FunctionTool

   # Correct:
   tools=[
       FunctionTool(coordinator_tools.create_project_session),
       # ☝️ Note: FunctionTool() wrapping
   ]

   # Incorrect:
   tools=[
       coordinator_tools.create_project_session,  # ✗ Not wrapped!
   ]
   ```

2. **Check tool function signature:**
   ```python
   # Tools must be async with type hints
   async def my_tool(param: str) -> dict:  # ✓ Correct
       return {"status": "ok"}

   # Not async = error
   def my_tool(param: str) -> dict:  # ✗ Must be async
       return {"status": "ok"}
   ```

## Getting More Help

1. **Check the specs:**
   - `specs/ADK_IMPLEMENTATION_SPEC.md` - Framework patterns
   - `specs/COORDINATOR_AGENT_SPEC.md` - Coordinator details
   - Etc. for other agents

2. **Review test examples:**
   - Tests show working implementations
   - Look for the test pattern you need

3. **Enable debug logging:**
   ```bash
   # In .env
   LOG_LEVEL=DEBUG

   # Then run with verbose pytest
   pytest -vv -s tests/
   ```

4. **Check current ticket acceptance criteria:**
   - Look in `tickets.md` for the ticket you're working on
   - Acceptance criteria describe what should work

5. **Use the CLI for testing:**
   ```bash
   python src/main.py
   # Type: help
   # Use commands to test individual pieces
   ```

## Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| Import errors | `source ~/.venvs/3d-adk/bin/activate && pip install -r requirements.txt` |
| OpenSCAD not found | Update `OPENSCAD_PATH` in `.env` with `which openscad` output |
| API key errors | Check `ANTHROPIC_API_KEY` in `.env` |
| OctoPrint won't connect | Verify with `curl http://host:5000/api/version -H "X-API-Key: ..."` |
| Tests won't run | Add `@pytest.mark.asyncio` to async tests |
| Tests fail linting | Run `black src/ tests/` |
| Can't advance phase | Check `status` to see required flags |

---

**Still stuck?** Check [SETUP_GUIDE.md](SETUP_GUIDE.md) for installation help or [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for development patterns.

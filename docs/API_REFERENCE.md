# API Reference

## Agents

### Coordinator Agent
**Purpose:** Orchestrates workflow across all phases

**Methods:**
- `run_async(user_input, session_id)` → agent response

**Tools:**
- Routes to sub-agents based on current phase
- Manages phase transitions
- Maintains session state

See: [../specs/COORDINATOR_AGENT_SPEC.md](../specs/COORDINATOR_AGENT_SPEC.md)

### Design Agent
**Purpose:** Transform design ideas into blueprints

**Workflow:** Interview → Sketches → Images → Blueprint

See: [../specs/DESIGN_AGENT_SPEC.md](../specs/DESIGN_AGENT_SPEC.md)

### Modeling Agent
**Purpose:** Convert designs to STL files

**Workflow:** Specs → OpenSCAD → Validation → Export

See: [../specs/MODELING_AGENT_SPEC.md](../specs/MODELING_AGENT_SPEC.md)

### Monitor Agent
**Purpose:** Monitor 3D print execution

**Workflow:** Connect → Monitor → Detect Issues → Complete

See: [../specs/MONITOR_AGENT_SPEC.md](../specs/MONITOR_AGENT_SPEC.md)

## Services

### Memory Service
Stores conversation history and design decisions.
- `add_events_to_memory(events)` - Store conversation
- `search_memory(query)` - Retrieve design context

### Artifact Service
Persists generated files.
- `save_artifact(artifact_id, data, metadata)` - Store file
- `load_artifact(artifact_id, project_id)` - Retrieve file

### Session Service
Manages persistent project state using ADK BaseSessionService with JSON filesystem backend.

**Implementation:** `ProjectSessionService` (extends `google.adk.sessions.BaseSessionService`)

**Core Methods:**

#### `create_session(*, app_name: str, user_id: str, state: Optional[dict] = None, session_id: Optional[str] = None) -> Session`
Create a new project session with persistent state.

- **Parameters:**
  - `app_name` (str): Application identifier (e.g., "3d-adk")
  - `user_id` (str): User identifier for multi-user support
  - `state` (dict, optional): Initial project state; must contain `project_name` key
  - `session_id` (str, optional): Custom session ID; UUID generated if omitted

- **Returns:** `Session` object with:
  - `id`: Unique session identifier
  - `state`: Project state dict containing:
    - `project_name`: Name of the project
    - `current_phase`: One of "design", "modeling", "monitor"
    - `created_at`: ISO timestamp
    - `updated_at`: ISO timestamp
    - `design_approved`: Boolean flag
    - `model_exported`: Boolean flag
    - `print_started`: Boolean flag

- **Storage:** Persists to `{SESSIONS_DIR}/{app_name}/{user_id}/{session_id}.json`

- **Error:** Raises `ValueError` if `project_name` not provided in state

- **Side Effect:** Creates project directory tree at `{PROJECTS_DIR}/{project_name}/` with subdirectories: `design/sketches`, `design/images`, `model/exports`, `print`

#### `get_session(*, app_name: str, user_id: str, session_id: str, config=None) -> Optional[Session]`
Retrieve an existing session by ID.

- **Parameters:**
  - `app_name` (str): Application identifier
  - `user_id` (str): User identifier
  - `session_id` (str): Session ID to retrieve
  - `config` (optional): Configuration object (unused)

- **Returns:** `Session` object if found, `None` if not found

- **Storage:** Loads from `{SESSIONS_DIR}/{app_name}/{user_id}/{session_id}.json`

#### `list_sessions(*, app_name: str, user_id: Optional[str] = None) -> ListSessionsResponse`
List sessions for an application or specific user.

- **Parameters:**
  - `app_name` (str): Application identifier
  - `user_id` (str, optional): Filter by user; if omitted, returns all users' sessions

- **Returns:** `ListSessionsResponse` with `sessions: list[Session]`

- **Storage:** Scans directory tree `{SESSIONS_DIR}/{app_name}/{user_id}/`

#### `delete_session(*, app_name: str, user_id: str, session_id: str) -> None`
Delete a session.

- **Parameters:**
  - `app_name` (str): Application identifier
  - `user_id` (str): User identifier
  - `session_id` (str): Session ID to delete

- **Storage:** Removes JSON file from disk

- **Note:** Project directory (at `{PROJECTS_DIR}/{project_name}/`) is NOT deleted

#### `append_event(session: Session, event: Event) -> Event`
Append an event to session history and persist to disk.

- **Parameters:**
  - `session` (Session): Session to append event to
  - `event` (Event): Event to append

- **Returns:** The appended event

- **Storage:** Re-persists entire session to disk with new event in `events` array

**Convenience Module:** `src.session` provides single-user helpers:
- `create_project(project_name: str) -> Session` — Creates a project with defaults
- `get_project(session_id: str) -> Optional[Session]` — Retrieves a project
- `update_project_phase(session_id: str, phase: str) -> Session` — Updates current phase
- `list_projects() -> list[Session]` — Lists all projects
- `recover_session(session_id: str) -> Optional[Session]` — Alias for get_project

See: [../specs/ADK_IMPLEMENTATION_SPEC.md](../specs/ADK_IMPLEMENTATION_SPEC.md)

## Tools

Tools are implemented per agent. See specific agent specs for:
- Input/output schemas
- Error handling
- Example usage

**By Phase:**
- Design: Interview, Sketches, Images, Blueprint generation
- Modeling: OpenSCAD generation, STL export, validation
- Monitor: OctoPrint connection, monitoring, issue detection

---

**Implementation details:** See spec files in `specs/` folder

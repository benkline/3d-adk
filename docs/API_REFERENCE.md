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

**Implementation:** `google.adk.agents.LlmAgent` with four `FunctionTool`-wrapped async functions

**Agent Name:** `design_phase_agent`

**Model:** Uses configured `LLM_MODEL` from `src.config`

**Tools:**

#### `conduct_interview(user_input: str, project_name: str) -> dict`
Conduct structured multi-turn interview to gather design requirements. Persists state to `projects/{project_name}/design/interview.json`.

**Parameters:**
- `user_input` (str): User's response to the current interview question (non-empty)
- `project_name` (str): Name of the project (non-empty)

**Interview Flow:**
Asks 7 sequential questions to gather design requirements:
1. Object name and initial description
2. Dimensions (e.g., "100mm x 80mm x 60mm")
3. Materials (e.g., "PLA, PETG")
4. Aesthetic style (e.g., "minimalist")
5. Constraints (e.g., "must fit iPhone 14")
6. Moving parts/assembly info
7. Special requirements

**Returns:** dict with keys:
- `status` (str): "in_progress", "complete", or "error"
- `interview_complete` (bool): Whether all questions have been answered
- `question_number` (int): Current question number (1-indexed)
- `total_questions` (int): Total number of interview questions
- `next_question` (str): Next question to ask (if status is "in_progress")
- `design_brief` (dict or None): Structured design brief (when complete)
- `summary` (str): Human-readable summary of design (when complete)
- `message` (str): Error message (if status is "error")

**Design Brief Structure (when complete):**
```json
{
  "name": "object name",
  "purpose": "primary purpose",
  "dimensions": {"width": "100", "height": "80", "depth": "60"},
  "materials": ["PLA"],
  "aesthetics": "minimalist",
  "constraints": ["must fit iPhone 14"],
  "special_requirements": []
}
```

**Error Handling:** Returns error dict with message rather than raising exceptions

---

#### `generate_sketches(project_name: str, design_brief: dict) -> dict`
Generate 3-5 conceptual sketch variations from design brief.

**Parameters:**
- `project_name` (str): Name of the project (non-empty)
- `design_brief` (dict): Design brief containing object details (non-empty dict)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `sketches` (list): List of sketch dicts with metadata
- `sketch_count` (int): Number of sketches generated
- `output_dir` (str): Directory where sketches are stored
- `message` (str): Error message (if status is "error")

**Error Handling:** Returns error dict with message rather than raising exceptions

---

#### `generate_images(project_name: str, sketch_id: str, perspective: str = "front", feedback: Optional[str] = None) -> dict`
Generate production-quality render images from sketch with specified perspective, with support for user feedback and regeneration.

**Parameters:**
- `project_name` (str): Name of the project (non-empty)
- `sketch_id` (str): ID of the sketch to render (non-empty)
- `perspective` (str): Viewing perspective ("front", "side", "3d", "top"), defaults to "front"
  - `"front"`: Front-facing view with clear detail and lighting
  - `"side"`: Side profile view showing depth and form
  - `"3d"`: Three-quarter isometric view showing multiple surfaces
  - `"top"`: Top-down overhead view with shadows for depth
- `feedback` (str, optional): User feedback for image regeneration (e.g., "brighter lighting", "less glossy finish")

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `images` (list): List of image record dicts with full metadata
- `image_count` (int): Number of images generated (always 1 per call)
- `output_dir` (str): Directory where images are stored (`design/images/`)
- `perspective` (str): The perspective that was generated
- `message` (str): Success or error message

**Image Record Structure:**
```json
{
  "id": "image_a1b2c3d4",
  "sketch_id": "sketch_xyz789",
  "perspective": "front",
  "prompt": "High-quality product render of a phone stand, minimalist design...",
  "material_context": "PLA with professional finish",
  "created_at": "2025-02-14T10:30:45.123456",
  "status": "pending_generation",
  "image_path": null
}
```

**Prompt Engineering:**
- Uses Claude to generate production-quality render prompts (NOT conceptual sketches)
- Incorporates design brief context (materials, aesthetics, constraints, dimensions)
- Includes material and lighting details for photorealistic rendering
- Supports regeneration via `feedback` parameter for iterative refinement
- Falls back to hardcoded production-quality prompts if Claude fails

**Output Directory Structure:**
```
design/images/
├── metadata.json          # Index of all generated images
├── image_a1b2c3d4/        # Per-image directory
│   └── prompt.txt         # Generation prompt
├── image_b2c3d4e5/
│   └── prompt.txt
└── ...
```

**Metadata Storage:**
- All image records persisted to `design/images/metadata.json`
- Includes `last_updated` timestamp for tracking generation history
- Supports iterative regeneration with user feedback

**Error Handling:**
- Validates perspective against allowed set; returns error dict if invalid
- Validates project_name and sketch_id; returns error dict if empty
- Returns error dict with descriptive message on any failures
- Never raises exceptions

**Regeneration Workflow:**
Call again with same `project_name`, `sketch_id`, `perspective` but different `feedback` to regenerate:
```python
# Initial generation
result1 = await generate_images("my-project", "sketch_abc", "front")

# Regenerate with feedback
result2 = await generate_images("my-project", "sketch_abc", "front",
                                feedback="brighter, more dramatic lighting")
# Returns new image record with updated prompt reflecting feedback
```

---

#### `generate_blueprint(project_name: str, design_brief: dict, approved_images: list = None) -> dict`
Generate formal technical blueprint and specifications document.

**Parameters:**
- `project_name` (str): Name of the project (non-empty)
- `design_brief` (dict): Design brief with object details (non-empty dict)
- `approved_images` (list, optional): List of approved image IDs (defaults to None)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `blueprint_path` (str): Absolute path to blueprint markdown file
- `specs_path` (str): Absolute path to design_specs JSON file
- `message` (str): Error message (if status is "error") or success message

**Blueprint Markdown Structure:**
The generated `blueprint.md` contains:
- **Design Summary:** Project name, purpose, aesthetics, constraints, special requirements
- **Specifications:** Dimensions, material, wall thickness, infill percentage
- **Print Parameters:** Orientation, supports, estimated print time, estimated weight
- **Assembly:** (if multi-part design)
- **Notes:** Design validation tips and adjustment guidelines

**Specs JSON Structure:**
The generated `design_specs.json` is input for the modeling agent:
```json
{
  "project_id": "uuid",
  "project_name": "string",
  "created_at": "timestamp",
  "design_brief": {},
  "specifications": {
    "overall_dimensions": {"width": "number", "height": "number", "depth": "number"},
    "material": "string",
    "wall_thickness_mm": number,
    "infill_percentage": number,
    "print_orientation": "string",
    "supports_required": boolean,
    "support_type": "string",
    "estimated_weight_g": number,
    "estimated_print_time_hours": number
  },
  "approved_images": [],
  "parts": [{"name": "string", "quantity": number, "dimensions": {}, "tolerance_mm": number}],
  "assembly_instructions": []
}
```

**Error Handling:** Returns error dict with message rather than raising exceptions

---

**Output Structure:**
All design phase outputs stored in `{PROJECTS_DIR}/{project_name}/design/`:
```
design/
├── sketches/            # Conceptual sketches
├── images/              # Rendered images
├── interview.json       # Interview responses and design brief
├── blueprint.md         # Technical blueprint (markdown)
└── design_specs.json    # Specifications document (JSON for modeling agent)
```

See: [../specs/DESIGN_AGENT_SPEC.md](../specs/DESIGN_AGENT_SPEC.md)

### Modeling Agent
**Purpose:** Convert design specifications to OpenSCAD models and exports for 3D printing

**Workflow:** Validation → Setup → Generation → Export

**Implementation:** `google.adk.agents.LlmAgent` with four `FunctionTool`-wrapped async functions

**Agent Name:** `modeling_phase_agent`

**Model:** Uses configured `LLM_MODEL` from `src.config`

**Tools:**

#### `validate_design_specs(project_name: str, specs_path: Optional[str] = None) -> dict`
Validate design specifications from the design phase output.

**Parameters:**
- `project_name` (str): Name of the project (non-empty)
- `specs_path` (str, optional): Path to design_specs.json (defaults to `{project}/design/design_specs.json`)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `specs` (dict or None): Validated design specifications (if status is "ok")
- `message` (str): Success or error message

**Validation Rules:**
- Checks required keys: `project_name`, `specifications`, `design_brief`
- Validates `specifications` contains: `overall_dimensions`, `material`
- Returns error dict if any validation fails

**Error Handling:** Returns error dict with message rather than raising exceptions

---

#### `setup_openscad_workspace(project_name: str) -> dict`
Set up OpenSCAD workspace directory structure for a project.

**Parameters:**
- `project_name` (str): Name of the project (non-empty)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `workspace_dir` (str): Path to the modeling directory
- `message` (str): Success or error message

**Directory Structure Created:**
```
modeling/
├── scad/           # OpenSCAD source files (.scad)
├── exports/        # Exported 3D files (STL, 3MF)
├── previews/       # Preview images from OpenSCAD
└── metadata.json   # Workspace metadata and history
```

**Metadata Structure:**
```json
{
  "project_name": "string",
  "created_at": "ISO timestamp",
  "scad_models": [],
  "exports": []
}
```

**Error Handling:** Returns error dict with message rather than raising exceptions

---

#### `generate_scad_code(project_name: str, design_specs: dict) -> dict`
Generate OpenSCAD code from design specifications.

**Parameters:**
- `project_name` (str): Name of the project (non-empty)
- `design_specs` (dict): Design specifications from design phase (non-empty dict)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `scad_path` (str): Path to generated .scad file
- `scad_content` (str): The OpenSCAD code as string
- `message` (str): Success or error message

**Implementation Details:**
- Uses `solidpython2` library to generate parametric OpenSCAD models
- Extracts dimensions and material from `design_specs["specifications"]`
- Generates parametric box module with configurable dimensions and wall thickness
- Falls back to manual SCAD generation if `solidpython2` unavailable
- Writes `.scad` file to `{project}/modeling/scad/model.scad`
- Updates workspace metadata with model record

**Generated SCAD Structure:**
- Header comments with project name, material, dimensions, wall thickness
- Parametric `module box(width, height, depth, wall)` definition
- Module instantiation with calculated parameters
- Clean, readable code suitable for further manual editing

**Output File Location:** `{PROJECTS_DIR}/{project_name}/modeling/scad/model.scad`

**Error Handling:** Returns error dict with message rather than raising exceptions

---

#### `export_model(project_name: str, export_format: str = "stl") -> dict`
Export OpenSCAD model to printable format (STL or 3MF).

**Parameters:**
- `project_name` (str): Name of the project (non-empty)
- `export_format` (str): Export format ("stl" or "3mf"), defaults to "stl"

**Returns:** dict with keys:
- `status` (str): "ok", "pending", or "error"
- `export_path` (str): Path to exported file (if generated)
- `export_format` (str): Format of the export
- `message` (str): Status or error message

**Export Behavior:**
- Validates `export_format` against allowed set: `{"stl", "3mf"}`
- Checks that OpenSCAD model exists at `{project}/modeling/scad/model.scad`
- **If OpenSCAD binary found:** Invokes OpenSCAD CLI to render `.scad` → `.stl`/`.3mf` file
  - Creates `{project}/modeling/exports/model.{format}` file
  - Returns status "ok" with export path
  - Timeout: 300 seconds per render
- **If OpenSCAD binary not found:** Returns status "pending" (graceful degradation)
  - Model `.scad` file is ready for manual rendering
  - User can install OpenSCAD and render manually
  - No error thrown — supports environments without OpenSCAD installed

**OpenSCAD Binary Detection:**
- Looks for binary at `OPENSCAD_PATH` from environment (see `src/config.py`)
- Default: `/usr/local/bin/openscad`
- Configurable via `OPENSCAD_PATH` env var

**Error Cases (return status "error"):**
- Invalid `export_format`
- Model `.scad` file not found
- OpenSCAD process failed (non-zero exit code)
- Subprocess timeout (>300 seconds)
- Other I/O or OS errors

**Metadata Update:**
On successful export, updates `{project}/modeling/metadata.json` with export record:
```json
{
  "id": "uuid",
  "filename": "model.stl",
  "format": "stl",
  "path": "/absolute/path/to/model.stl",
  "created_at": "ISO timestamp",
  "status": "exported"
}
```

**Error Handling:** Returns error/pending dict with message rather than raising exceptions

---

**Output Structure:**
All modeling phase outputs stored in `{PROJECTS_DIR}/{project_name}/modeling/`:
```
modeling/
├── scad/           # OpenSCAD source files
│   └── model.scad  # Generated parametric model
├── exports/        # Exported 3D files ready for printing
│   └── model.stl   # (or model.3mf)
├── previews/       # (for future preview images)
└── metadata.json   # Workspace and export history
```

---

**Workflow Example:**
```python
# 1. Validate design specs from design phase
result = await validate_design_specs("my_project")
# → status "ok" with validated specs

# 2. Set up modeling workspace
result = await setup_openscad_workspace("my_project")
# → status "ok", workspace directories created

# 3. Generate OpenSCAD code
result = await generate_scad_code("my_project", design_specs)
# → status "ok" with model.scad file at {project}/modeling/scad/

# 4. Export to STL for printing
result = await export_model("my_project", "stl")
# → status "ok" with model.stl file at {project}/modeling/exports/
# OR status "pending" if OpenSCAD not installed (model.scad is ready)
```

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

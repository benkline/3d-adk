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

**Workflow:** Validation → Setup → Generation → Preview → Export

**Implementation:** `google.adk.agents.LlmAgent` with seven `FunctionTool`-wrapped async functions

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

#### `render_preview(project_name: str, perspectives: Optional[list] = None, resolution: int = 512) -> dict`
Generate preview images of OpenSCAD models from multiple viewing angles.

**Parameters:**
- `project_name` (str): Name of the project (non-empty)
- `perspectives` (list, optional): List of view angles to render. Valid options: "front", "back", "left", "right", "top", "bottom", "isometric". Defaults to `["front", "isometric", "top"]`
- `resolution` (int, optional): Output resolution in pixels (256-1024). Defaults to 512

**Returns:** dict with keys:
- `status` (str): "ok", "pending", or "error"
- `preview_paths` (list[str]): Paths to generated preview images (if status is "ok")
- `perspectives` (list[str]): Successfully rendered perspective views (if status is "ok")
- `resolution` (int): Resolution of generated previews (if status is "ok")
- `message` (str): Status or error message

**Rendering Behavior:**
- Validates OpenSCAD model exists at `{project}/modeling/scad/model.scad`
- **If OpenSCAD binary found:** Invokes OpenSCAD CLI to render each perspective
  - Creates `{project}/modeling/previews/preview_{perspective}.png` files
  - Uses camera parameters specific to each viewing angle
  - Returns status "ok" with list of preview paths
  - Timeout: 120 seconds per perspective
  - Gracefully handles per-perspective failures (continues rendering other perspectives)
- **If OpenSCAD binary not found:** Returns status "pending" (graceful degradation)
  - Preview images cannot be generated without OpenSCAD
  - User can install OpenSCAD and retry
  - No error thrown — supports environments without OpenSCAD installed

**Supported Perspectives:**
- `"front"`: Front-facing view (0° rotation)
- `"back"`: Rear-facing view (180° rotation)
- `"left"`: Left side view (270° rotation)
- `"right"`: Right side view (90° rotation)
- `"top"`: Top-down view (90° pitch)
- `"bottom"`: Bottom-up view (-90° pitch)
- `"isometric"`: Standard isometric 3D view (55°, 25°, 140 distance)

**OpenSCAD Binary Detection:**
- Looks for binary at `OPENSCAD_PATH` from environment (see `src/config.py`)
- Default: `/usr/local/bin/openscad`
- Configurable via `OPENSCAD_PATH` env var

**Error Cases (return status "error"):**
- Empty `project_name`
- Invalid `resolution` (outside 256-1024 range)
- Invalid perspective names
- Model `.scad` file not found
- All perspective renders failed
- Other I/O or OS errors

**Metadata Update:**
On successful generation, updates `{project}/modeling/metadata.json` with preview record:
```json
{
  "id": "preview_xxxxxxxx",
  "perspectives": ["front", "isometric", "top"],
  "resolution": 512,
  "paths": ["/path/to/preview_front.png", …],
  "created_at": "ISO timestamp",
  "status": "generated"
}
```

**Error Handling:** Returns error/pending dict with message rather than raising exceptions

---

#### `export_model(project_name: str, export_format: str = "stl") -> dict`
Export OpenSCAD model to printable format (STL or 3MF).

**Parameters:**
- `project_name` (str): Name of the project (non-empty)
- `export_format` (str): Export format ("stl" or "3mf"), defaults to "stl"
- `parts` (list, optional): List of part names for multi-part export. If None, exports single model.scad file. If provided, exports each part as `scad/{part_name}.scad`

**Returns:** dict with keys:
- `status` (str): "ok", "pending", or "error"
- `export_path` (str): Path to exported file (single-part only, if status is "ok")
- `export_paths` (list[str]): Paths to exported files (multi-part only, if status is "ok")
- `parts` (list[str]): Successfully exported part names (multi-part only, if status is "ok")
- `export_format` (str): Format of the export
- `message` (str): Status or error message

**Export Behavior:**

**Single-Part Export (parts=None):**
- Validates `export_format` against allowed set: `{"stl", "3mf"}`
- Checks that OpenSCAD model exists at `{project}/modeling/scad/model.scad`
- Validates OpenSCAD binary exists at `OPENSCAD_PATH`
- **If binary found:** Invokes OpenSCAD CLI to render `.scad` → `.stl`/`.3mf` file
  - Creates `{project}/modeling/exports/model.{format}` file
  - Validates exported file is non-empty (size > 0 bytes)
  - Returns status "ok" with single `export_path`
  - Timeout: 300 seconds per render
- **If binary not found:** Returns status "pending" (graceful degradation)

**Multi-Part Export (parts=["part1", "part2", ...]):**
- Validates that all part SCAD files exist at `scad/{part_name}.scad`
- If any parts are missing, returns status "error" listing missing parts
- **If binary found:** Exports each part separately
  - Creates `{project}/modeling/exports/{part_name}.{format}` for each part
  - Validates each exported file is non-empty
  - Returns status "ok" with list of `export_paths` and successfully exported `parts`
  - Continues exporting remaining parts if one fails (graceful degradation)
  - If any parts fail, returns status "ok" with warning message listing failed parts
  - Timeout: 300 seconds per part
- **If binary not found:** Returns status "pending" (graceful degradation)

**OpenSCAD Binary Detection:**
- Looks for binary at `OPENSCAD_PATH` from environment (see `src/config.py`)
- Default: `/usr/local/bin/openscad`
- Configurable via `OPENSCAD_PATH` env var

**File Validation:**
- After successful export, validates that output file exists and is non-empty
- Returns status "error" if exported file is zero-sized or missing
- For multi-part: skips zero-sized parts and continues with remaining parts

**Error Cases (return status "error"):**
- Empty `project_name`
- Invalid `export_format`
- Invalid `parts` parameter (non-list or empty list)
- Model `.scad` file not found (single-part)
- Required part `.scad` files not found (multi-part)
- All parts failed to export (multi-part)
- OpenSCAD process failed (non-zero exit code)
- Subprocess timeout (>300 seconds per part)
- Exported file is empty or invalid
- Other I/O or OS errors

**Metadata Update:**

Single-part success, updates `{project}/modeling/metadata.json` with:
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

Multi-part success, updates `{project}/modeling/metadata.json` with:
```json
{
  "id": "uuid",
  "type": "multi_part",
  "parts": ["base", "lid"],
  "format": "stl",
  "paths": ["/absolute/path/to/base.stl", "/absolute/path/to/lid.stl"],
  "created_at": "ISO timestamp",
  "status": "exported"
}
```

**Error Handling:** Returns error/pending dict with message rather than raising exceptions

---

#### `analyze_printability(project_name: str, specs_path: Optional[str] = None) -> dict`
Analyze design specifications for 3D printability and generate warnings and recommendations.

**Parameters:**
- `project_name` (str): Name of the project (non-empty)
- `specs_path` (str, optional): Path to design_specs.json (defaults to `{project}/design/design_specs.json`)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `report` (dict): Printability report (if status is "ok") with keys:
  - `feasible` (bool): Whether model is printable
  - `wall_thickness_ok` (bool): Wall thickness meets material minimum
  - `overhang_ok` (bool): No unsupported overhangs detected
  - `assemblies_ok` (bool): Multi-part tolerances acceptable
  - `warnings` (list[str]): Printability warnings
  - `suggestions` (list[str]): Recommendations
  - `estimates` (dict): `print_hours` (float) and `weight_g` (float)
- `message` (str): Success or error message

**Analysis Checks:**

**Wall Thickness Validation:**
- Compares `specifications.wall_thickness_mm` against material-specific minimums
- Material thresholds: PLA 1.2mm, PETG 1.5mm, ABS 1.5mm, TPU 0.8mm, Resin 0.5mm, Nylon 1.5mm
- Returns warning if thickness is below minimum for selected material
- Primary gate for feasibility

**Overhang Detection:**
- Checks `specifications.supports_required` flag
- Analyzes dimension ratios using `overall_dimensions`
- Flags designs with height > 2x horizontal dimensions as potential overhangs
- Suggests appropriate support strategy (tree supports recommended)

**Hollow Section Analysis:**
- Evaluates `infill_percentage` for structural adequacy
- Flags extremely low infill (< 10%) as structural weakness risk
- For load-bearing parts (identified in constraints), suggests minimum 20% infill

**Assembly Tolerance Check:**
- Validates multi-part designs have adequate tolerances (>= 0.1mm)
- Sets `assemblies_ok: false` for parts with poor tolerance

**Error Cases (return status "error"):**
- Empty `project_name`
- Design specs file not found
- Invalid or corrupted JSON in design specs
- Other I/O or JSON parsing errors

**Metadata Update:**
On successful analysis, updates `{project}/modeling/metadata.json` with:
```json
{
  "id": "analysis_xxxxxxxx",
  "created_at": "ISO timestamp",
  "status": "analyzed",
  "report": {
    "feasible": true,
    "wall_thickness_ok": true,
    "overhang_ok": false,
    "assemblies_ok": true,
    "warnings": ["Model requires support structures"],
    "suggestions": ["Use tree supports for better surface quality"],
    "estimates": {"print_hours": 2.5, "weight_g": 45.0}
  }
}
```

**Error Handling:** Returns error dict with message rather than raising exceptions

---

#### `optimize_parameters(project_name: str, specs_path: Optional[str] = None, printability_report: Optional[dict] = None) -> dict`
Generate print parameter recommendations for optimal printing outcomes.

**Parameters:**
- `project_name` (str): Name of the project (non-empty)
- `specs_path` (str, optional): Path to design_specs.json (defaults to `{project}/design/design_specs.json`)
- `printability_report` (dict, optional): Printability analysis report from `analyze_printability` (used to refine recommendations)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `project_name` (str): Name of the project
- `recommendations` (dict): Optimization recommendations (if status is "ok") with keys:
  - `print_orientation` (str): Recommended orientation ("flat", "upright", or "side")
  - `orientation_rationale` (str): Explanation of orientation choice
  - `infill_percentage` (int): Recommended infill (10, 20, 35, or 50)
  - `infill_rationale` (str): Explanation of infill choice
  - `supports_required` (bool): Whether support structures are needed
  - `support_type` (str): Type of support ("none", "touching_buildplate", or "tree")
  - `support_rationale` (str): Explanation of support choice
  - `estimated_weight_g` (float): Estimated part weight in grams
  - `estimated_print_time_hours` (float): Estimated print time in hours
  - `estimated_material_cost_usd` (str): Estimated material cost in "$X.XX" format
- `message` (str): Success or error message

**Optimization Strategy:**

**Print Orientation:**
- Analyzes overall dimensions from specifications
- Selects orientation that minimizes print height (z-axis)
- Trade-off: "flat" (fast but more supports) vs "upright" (slower but fewer supports)
- Uses printability report overhang data if provided

**Infill Percentage Recommendations:**
- `10%`: Decorative parts, non-structural, minimal strength needed
- `20%`: Standard parts, everyday use, baseline strength
- `35%`: Functional/mechanical parts, moving components, moderate load-bearing
- `50%`: Structural/load-bearing parts, high stress areas, maximum strength
- Selection driven by `design_brief.constraints` keywords: "lightweight" → lower infill, "strong"/"load" → higher infill

**Support Strategy:**
- `"none"`: No supports needed (part prints without overhangs)
- `"touching_buildplate"`: Linear supports touching only build plate (fewer supports, easier removal)
- `"tree"`: Advanced tree supports (material-efficient, best surface quality)
- Selection based on printability report overhang analysis and orientation

**Material Cost Calculation:**
- Uses material density and print volume to estimate weight
- Multiplies weight by configured `FILAMENT_COST_PER_KG` from `src/config` (default: $25.00/kg)
- Formula: `cost_usd = (estimated_weight_g / 1000) * FILAMENT_COST_PER_KG`

**Print Time Estimation:**
- Default: 8g/hour (conservative for most 0.4mm nozzle FDM printers)
- Adjusts based on infill percentage (higher infill → longer time)
- Formula: `hours = (estimated_weight_g / 8) * (1 + (infill_percentage / 100))`

**Integration with Printability Report:**
- If `printability_report` provided (from `analyze_printability`), uses report data to refine:
  - Support requirements based on overhang detection
  - Orientation to minimize support material usage
  - Infill to address structural concerns flagged in report

**Error Cases (return status "error"):**
- Empty `project_name`
- Design specs file not found
- Invalid or corrupted JSON in design specs
- Missing critical specification keys
- Other I/O or JSON parsing errors

**Metadata Update:**
On successful optimization, updates `{project}/modeling/metadata.json` with:
```json
{
  "id": "optimization_xxxxxxxx",
  "created_at": "ISO timestamp",
  "status": "optimized",
  "recommendations": {
    "print_orientation": "flat",
    "orientation_rationale": "Minimizes print height for faster printing",
    "infill_percentage": 20,
    "infill_rationale": "Standard part with everyday use - 20% provides good balance",
    "supports_required": false,
    "support_type": "none",
    "support_rationale": "Flat orientation eliminates overhangs",
    "estimated_weight_g": 45.5,
    "estimated_print_time_hours": 5.7,
    "estimated_material_cost_usd": "$1.14"
  }
}
```

**Error Handling:** Returns error dict with message rather than raising exceptions

---

**Output Structure:**
All modeling phase outputs stored in `{PROJECTS_DIR}/{project_name}/modeling/`:
```
modeling/
├── scad/           # OpenSCAD source files
│   └── model.scad  # Generated parametric model
├── exports/        # Exported 3D files ready for printing
│   └── model.stl   # (or model.3mf)
├── previews/       # Preview images from different viewing angles
│   ├── preview_front.png
│   ├── preview_isometric.png
│   └── preview_top.png
└── metadata.json   # Workspace, export, and preview history
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

# 4. Generate preview images from multiple angles
result = await render_preview("my_project")
# → status "ok" with preview images at {project}/modeling/previews/
# OR status "pending" if OpenSCAD not installed

# 5. Export to STL for printing
result = await export_model("my_project", "stl")
# → status "ok" with model.stl file at {project}/modeling/exports/
# OR status "pending" if OpenSCAD not installed (model.scad is ready)

# 6. Analyze printability
result = await analyze_printability("my_project")
# → status "ok" with printability report (feasibility, warnings, suggestions)

# 7. Optimize print parameters
result = await optimize_parameters("my_project", printability_report=result["report"])
# → status "ok" with optimization recommendations (orientation, infill, supports, cost/time estimates)
```

### Monitor Agent
**Purpose:** Monitor 3D printer status and print jobs via OctoPrint, detect issues, and capture quality assessments

**Workflow:** Connect → Printer Status → Job Status → Monitoring Loop → Completion Detection → Quality Assessment → Summary & Archive

**Implementation:** `google.adk.agents.LlmAgent` with twelve `FunctionTool`-wrapped functions

**Agent Name:** `monitor_phase_agent`

**Model:** Uses configured `LLM_MODEL` from `src.config`

**Tools:**

#### `test_connection(host: str = "", port: str = "", api_key: str = "") -> dict`
Test connection to OctoPrint server.

**Parameters:**
- `host` (str): OctoPrint server hostname/IP (empty string to use config default)
- `port` (str): OctoPrint port as string (empty string to use config default)
- `api_key` (str): OctoPrint API key (empty string to use config default)

**Config Fallbacks:**
When parameters are empty, falls back to environment variables:
- `OCTOPRINT_HOST` (default: "localhost")
- `OCTOPRINT_PORT` (default: "5000")
- `OCTOPRINT_API_KEY` (no default; required)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `server_version` (str): OctoPrint server version (if ok)
- `api_version` (str): OctoPrint API version (if ok)
- `message` (str): Human-readable status or error message

**Example Success Response:**
```json
{
  "status": "ok",
  "server_version": "1.8.7",
  "api_version": "0.1",
  "message": "Successfully connected to OctoPrint 1.8.7"
}
```

**Example Error Response:**
```json
{
  "status": "error",
  "message": "Failed to connect to OctoPrint: Connection refused"
}
```

**Error Handling:** Returns error dict with message rather than raising exceptions

---

#### `get_printer_status(host: str = "", port: str = "", api_key: str = "") -> dict`
Get current printer state and temperature readings.

**Parameters:**
- `host` (str): OctoPrint server hostname/IP (empty to use config default)
- `port` (str): OctoPrint port as string (empty to use config default)
- `api_key` (str): OctoPrint API key (empty to use config default)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `state` (str): Printer state ("Operational", "Printing", "Paused", "Offline", etc.)
- `bed_temp` (dict or null): `{"current": float, "target": float}` or null if unavailable
- `nozzle_temp` (dict or null): `{"current": float, "target": float}` or null if unavailable
- `message` (str): Human-readable status or error message

**Example Response:**
```json
{
  "status": "ok",
  "state": "Printing",
  "bed_temp": {
    "current": 60.0,
    "target": 60
  },
  "nozzle_temp": {
    "current": 210.0,
    "target": 210
  },
  "message": "Printer state: Printing"
}
```

**Error Handling:** Returns error dict with message rather than raising exceptions

---

#### `get_job_status(host: str = "", port: str = "", api_key: str = "") -> dict`
Get active print job information and progress.

**Parameters:**
- `host` (str): OctoPrint server hostname/IP (empty to use config default)
- `port` (str): OctoPrint port as string (empty to use config default)
- `api_key` (str): OctoPrint API key (empty to use config default)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `state` (str or null): Job state ("Printing", "Paused", etc.) or null if no active job
- `progress` (dict or null): Progress information or null if no active job
  - `completion` (float): Percentage complete (0-100)
  - `filepos` (int): Current position in file (bytes)
  - `printtime` (int): Elapsed print time (seconds)
  - `printtime_left` (int): Estimated remaining time (seconds)
- `filename` (str or null): Current print filename or null if no active job
- `message` (str): Human-readable status or error message

**Example Response - Active Job:**
```json
{
  "status": "ok",
  "state": "Printing",
  "progress": {
    "completion": 45.5,
    "filepos": 123456,
    "printtime": 1800,
    "printtime_left": 2200
  },
  "filename": "phone_stand.gcode",
  "message": "Job state: Printing"
}
```

**Example Response - No Active Job:**
```json
{
  "status": "ok",
  "state": null,
  "progress": null,
  "filename": null,
  "message": "No active print job"
}
```

**Error Handling:** Returns error dict with message rather than raising exceptions

---

#### `format_alert(project_name: str, issues: list) -> dict`
Format detected print issues into user-readable alerts and persist them.

**Parameters:**
- `project_name` (str): Name of the project being monitored
- `issues` (list): List of detected issues (same format as `detect_print_issues` returns)

Each issue should have:
- `type` (str): Issue type (e.g., "temperature_deviation", "filament_jam", "layer_shift")
- `severity` (str): "warning" or "error"
- `message` (str): Description of the detected issue
- `detected_at` (int): Index where issue was detected
- `data` (dict): Additional issue data

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `alerts` (list): Formatted alerts with recommendations
- `alert_count` (int): Number of alerts created
- `message` (str): Human-readable status message

**Example Call:**
```python
issues = [
    {
        "type": "temperature_deviation",
        "severity": "warning",
        "message": "Nozzle 15°C deviation detected",
        "detected_at": 5,
        "data": {"nozzle_temp": {...}, "duration_seconds": 45}
    }
]
result = await format_alert("my_project", issues)
```

**Example Response:**
```json
{
  "status": "ok",
  "alerts": [
    {
      "alert_id": "temperature_deviation_1707912345000",
      "severity": "warning",
      "message": "Nozzle 15°C deviation detected",
      "recommended_action": "Check and adjust nozzle/bed temperature",
      "timestamp": "2024-02-15T12:45:45Z",
      "issue_type": "temperature_deviation"
    }
  ],
  "alert_count": 1,
  "message": "Formatted 1 alert(s)"
}
```

**Recommended Action Mapping:**
- `temperature_deviation` → "Check and adjust nozzle/bed temperature"
- `filament_jam` → "Pause print and inspect filament path"
- `layer_shift` → "Pause print and inspect print bed adhesion"
- `bed_adhesion_risk` → "Monitor closely; consider pausing to re-level bed"
- `early_print_failure` → "Review first layers; consider canceling and restarting"
- (default) → "Inspect printer and review print status"

**Persistence:** Alerts are appended to `{PROJECTS_DIR}/{project_name}/monitoring/alerts.json`

---

#### `pause_print(project_name: str, host: str = "", port: str = "", api_key: str = "") -> dict`
Pause the current print job.

**Parameters:**
- `project_name` (str): Name of the project being monitored
- `host` (str): OctoPrint server hostname/IP (empty to use config default)
- `port` (str): OctoPrint port as string (empty to use config default)
- `api_key` (str): OctoPrint API key (empty to use config default)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `message` (str): Human-readable status message
- `action` (str): "pause" (on success)

**Example Response - Success:**
```json
{
  "status": "ok",
  "message": "Print paused successfully",
  "action": "pause"
}
```

**Logging:** Intervention is logged to `{PROJECTS_DIR}/{project_name}/monitoring/interventions.json`

---

#### `resume_print(project_name: str, host: str = "", port: str = "", api_key: str = "") -> dict`
Resume a paused print job.

**Parameters:**
- `project_name` (str): Name of the project being monitored
- `host` (str): OctoPrint server hostname/IP (empty to use config default)
- `port` (str): OctoPrint port as string (empty to use config default)
- `api_key` (str): OctoPrint API key (empty to use config default)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `message` (str): Human-readable status message
- `action` (str): "resume" (on success)

**Example Response - Success:**
```json
{
  "status": "ok",
  "message": "Print resumed successfully",
  "action": "resume"
}
```

**Logging:** Intervention is logged to `{PROJECTS_DIR}/{project_name}/monitoring/interventions.json`

---

#### `cancel_print(project_name: str, host: str = "", port: str = "", api_key: str = "") -> dict`
Cancel the current print job.

**Parameters:**
- `project_name` (str): Name of the project being monitored
- `host` (str): OctoPrint server hostname/IP (empty to use config default)
- `port` (str): OctoPrint port as string (empty to use config default)
- `api_key` (str): OctoPrint API key (empty to use config default)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `message` (str): Human-readable status message
- `action` (str): "cancel" (on success)

**Example Response - Success:**
```json
{
  "status": "ok",
  "message": "Print canceled successfully",
  "action": "cancel"
}
```

**Logging:** Intervention is logged to `{PROJECTS_DIR}/{project_name}/monitoring/interventions.json`

---

#### `adjust_temperature(project_name: str, component: str, target_temp: float, host: str = "", port: str = "", api_key: str = "") -> dict`
Adjust printer temperature (nozzle or bed).

**Parameters:**
- `project_name` (str): Name of the project being monitored
- `component` (str): "nozzle" or "bed"
- `target_temp` (float): Target temperature in Celsius (0-350)
- `host` (str): OctoPrint server hostname/IP (empty to use config default)
- `port` (str): OctoPrint port as string (empty to use config default)
- `api_key` (str): OctoPrint API key (empty to use config default)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `message` (str): Human-readable status message
- `component` (str): Component adjusted ("nozzle" or "bed")
- `target_temp` (float): Target temperature set

**Validation:**
- `component` must be "nozzle" or "bed" (returns error otherwise)
- `target_temp` must be between 0 and 350°C (returns error otherwise)

**Example Response - Nozzle Success:**
```json
{
  "status": "ok",
  "message": "Temperature for nozzle set to 210°C",
  "component": "nozzle",
  "target_temp": 210.0
}
```

**Example Response - Invalid Component:**
```json
{
  "status": "error",
  "message": "component must be 'nozzle' or 'bed'"
}
```

**Logging:** Intervention is logged to `{PROJECTS_DIR}/{project_name}/monitoring/interventions.json`

---

#### `detect_print_completion(project_name: str, host: str = "", port: str = "", api_key: str = "") -> dict`
Detect if a print job has completed.

**Parameters:**
- `project_name` (str): Name of the project being monitored
- `host` (str): OctoPrint server hostname/IP (empty to use config default)
- `port` (str): OctoPrint port as string (empty to use config default)
- `api_key` (str): OctoPrint API key (empty to use config default)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `completed` (bool): True if print has completed, False if still in progress
- `state` (str or null): Current job state
- `filename` (str or null): Name of the print file
- `print_time_elapsed` (int): Total print time in seconds
- `message` (str): Human-readable status message

**Completion Criteria:**
A print is considered completed when:
- No active job (state is null), OR
- Job completion percentage equals 100%

**Example Response - Complete:**
```json
{
  "status": "ok",
  "completed": true,
  "state": null,
  "filename": "phone_stand.gcode",
  "print_time_elapsed": 3600,
  "message": "Print completion check: completed"
}
```

**Example Response - In Progress:**
```json
{
  "status": "ok",
  "completed": false,
  "state": "Printing",
  "filename": "phone_stand.gcode",
  "print_time_elapsed": 1800,
  "message": "Print completion check: in progress"
}
```

---

#### `record_quality_assessment(project_name: str, overall_quality: str, issues_encountered: str = "", user_notes: str = "", photo_path: str = "") -> dict`
Record user's print quality assessment after job completion.

**Parameters:**
- `project_name` (str): Name of the project being monitored
- `overall_quality` (str): Overall quality rating - must be one of: "excellent", "good", "acceptable", "poor"
- `issues_encountered` (str): Description of any issues observed (optional)
- `user_notes` (str): User's additional notes about the print (optional)
- `photo_path` (str): Path to a photo/inspection image (optional)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `assessment_id` (str): Unique identifier for this assessment record
- `message` (str): Human-readable status message

**Validation:**
- `overall_quality` must be one of the four valid options (returns error otherwise)

**Example Response - Success:**
```json
{
  "status": "ok",
  "assessment_id": "qa_1707912345000",
  "message": "Quality assessment recorded: excellent"
}
```

**Example Response - Invalid Quality:**
```json
{
  "status": "error",
  "message": "overall_quality must be one of: excellent, good, acceptable, poor"
}
```

**Persistence:** Assessment is stored to `{PROJECTS_DIR}/{project_name}/monitoring/quality_assessment.json`

---

#### `generate_print_summary(project_name: str) -> dict`
Generate comprehensive print summary from all monitoring data collected during the print.

**Parameters:**
- `project_name` (str): Name of the project being monitored

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `summary` (dict): Comprehensive print summary (if status="ok")
- `message` (str): Human-readable status message

**Summary Structure:**
```json
{
  "project_name": "phone_stand",
  "generated_at": "2024-02-15T12:45:45Z",
  "metrics": {
    "total_snapshots": 10,
    "total_print_time_s": 3600,
    "avg_nozzle_temp_c": 209.5,
    "max_nozzle_temp_c": 212.0,
    "avg_bed_temp_c": 59.8,
    "max_bed_temp_c": 60.0
  },
  "quality_assessment": {
    "assessment_id": "qa_1707912345000",
    "overall_quality": "good",
    "issues_encountered": "Minor warping on corners",
    "user_notes": "Good overall quality",
    "photo_path": "/path/to/photo.jpg",
    "timestamp": "2024-02-15T12:46:00Z"
  },
  "alerts_count": 2,
  "interventions_count": 1,
  "post_processing_recommendations": [
    "Monitor nozzle temperature calibration",
    "Standard finishing techniques sufficient"
  ]
}
```

**Post-Processing Recommendations** are automatically generated based on:
- Overall quality assessment (poor quality triggers more recommendations)
- Detected issues during printing (temperature, filament, bed adhesion, layer shift)
- Print complexity and requirements

**Persistence:** Summary is stored to `{PROJECTS_DIR}/{project_name}/monitoring/print_summary.json`

---

#### `archive_print_metadata(project_name: str) -> dict`
Archive completed print metadata for historical analysis (for TICKET-021 print history/analytics).

**Parameters:**
- `project_name` (str): Name of the project being monitored

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `archive_id` (str): Unique identifier for this archive record
- `archived_at` (str): ISO-8601 timestamp of archival
- `message` (str): Human-readable status message

**Prerequisites:**
Must have called `generate_print_summary` first - this tool requires a print_summary.json file to exist.

**Example Response - Success:**
```json
{
  "status": "ok",
  "archive_id": "archive_1707912345000",
  "archived_at": "2024-02-15T12:47:00Z",
  "message": "Print metadata archived: archive_1707912345000"
}
```

**Example Response - No Summary:**
```json
{
  "status": "error",
  "message": "No print summary found - run generate_print_summary first"
}
```

**Persistence:** Archives are stored to `{PROJECTS_DIR}/{project_name}/monitoring/archive.json` as a list of archive records.

**Archive Record Structure:**
```json
{
  "archive_id": "archive_1707912345000",
  "archived_at": "2024-02-15T12:47:00Z",
  "project_name": "phone_stand",
  "summary": { ... } // Full print_summary.json content
}
```

Multiple print completions can be archived for the same project, creating a complete print history.

---

### Monitor Agent Integration Testing (TICKET-022)

Comprehensive integration tests verify the complete monitoring workflow end-to-end. Tests cover the full pipeline from OctoPrint connection through print completion, quality assessment, and history storage.

**Test File:** `tests/test_monitor_integration.py`

**Test Coverage:** 20 tests across 4 test classes

#### Test Classes

**TestFullPipelineWorkflow (5 tests)**
- Tests the complete monitoring lifecycle sequentially
- Verifies OctoPrint connection, printer status, issue detection, interventions, and quality assessment
- Key tests:
  - `test_connection_test_returns_ok_with_mock`: Validates OctoPrint connection via mocked client
  - `test_printer_status_returns_state_and_temps`: Verifies temperature and state readings
  - `test_issue_detection_with_healthy_metrics`: Confirms healthy print produces no issues
  - `test_intervention_logs_to_file`: Validates intervention logging
  - `test_quality_assessment_persists`: Confirms quality assessment storage

**TestFullPipelineOutputFiles (4 tests)**
- Verifies that each workflow stage creates expected output files
- Key files verified:
  - `alerts.json` - Created by format_alert
  - `quality_assessment.json` - Created by record_quality_assessment
  - `print_summary.json` - Created by generate_print_summary
  - `completed_prints.json` - Created by archive_print_metadata

**TestIssueDetectionAndAlerts (5 tests)**
- Tests issue detection → alert formatting → intervention pipeline
- Issue types tested:
  - Temperature anomalies (sustained deviation)
  - Filament stalls (frozen progress)
  - Temperature alert formatting with recommendations
  - Intervention logging (pause/resume/cancel/adjust_temperature)

**TestHistoryAndAnalytics (5 tests)**
- Tests print completion, quality, summary, archive, and history workflow
- Key operations:
  - Summary aggregation of all monitoring data
  - Archive requirement validation (requires summary)
  - History storage and query
  - Analytics computation across multiple prints

**Additional Tests (1 test)**
- `test_monitor_agent_has_fifteen_tools`: Verifies agent has all 15 tools configured

#### Mock OctoPrint Pattern

Tests use `@patch("src.tools.monitor_tools.OctoPrintClient")` decorator for mocking OctoPrint connections:

```python
@patch("src.tools.monitor_tools.OctoPrintClient")
async def test_example(self, mock_class, patch_projects_dir):
    mock_client = Mock()
    mock_octorest = Mock()
    mock_client._get_client.return_value = mock_octorest
    mock_class.return_value = mock_client
    # ... test code ...
```

#### Metrics Format for Testing

Tests write metrics in JSONL format with the following snapshot structure:

```json
{
  "progress": 50.0,
  "state": "Printing",
  "bed_temp": {"current": 60.0, "target": 60.0},
  "nozzle_temp": {"current": 210.0, "target": 210.0},
  "print_time_elapsed": 300,
  "print_time_remaining": 1800
}
```

#### Running Integration Tests

```bash
# Run all integration tests
pytest tests/test_monitor_integration.py -v

# Run specific test class
pytest tests/test_monitor_integration.py::TestFullPipelineWorkflow -v

# Run with detailed output
pytest tests/test_monitor_integration.py -vv --tb=short
```

#### Test Statistics

- Total integration tests: 20
- All tests passing: ✅
- Test coverage: Complete monitoring workflow end-to-end
- Mock OctoPrint testing: ✅
- Real file I/O testing: ✅
- History/analytics testing: ✅

---

## Print History & Analytics (TICKET-021)

Store and analyze print history across projects for success rate tracking and cost estimation.

#### `store_print_history(project_name: str) -> dict`
Store completed print data in global print history for cross-project analytics.

**Parameters:**
- `project_name` (str): Name of the project being stored

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `history_id` (str): Unique identifier for this history record
- `message` (str): Human-readable status message

**Prerequisites:**
Must have called `generate_print_summary` and `record_quality_assessment` first.

**Example Response - Success:**
```json
{
  "status": "ok",
  "history_id": "history_1707912345000",
  "message": "Print history stored: history_1707912345000"
}
```

**Persistence:** Records are stored to `{PROJECTS_DIR}/print_history.json` as a global list of history records.

**History Record Structure:**
```json
{
  "history_id": "history_1707912345000",
  "recorded_at": "2024-02-15T12:47:00Z",
  "project_name": "phone_stand",
  "quality": "good",
  "print_time_s": 3600,
  "material_g": 8.0,
  "material_cost_usd": 0.2,
  "alerts_count": 1,
  "interventions_count": 0
}
```

---

#### `query_print_history(project_name: str = "", start_date: str = "", end_date: str = "", quality_filter: str = "") -> dict`
Query print history with optional filters for specific projects, date ranges, and quality levels.

**Parameters:**
- `project_name` (str, optional): Filter by exact project name
- `start_date` (str, optional): Filter start date as "YYYY-MM-DD"
- `end_date` (str, optional): Filter end date as "YYYY-MM-DD"
- `quality_filter` (str, optional): Filter by quality level ("excellent", "good", "acceptable", "poor")

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `records` (list): Matching history records
- `total_count` (int): Number of matching records
- `message` (str): Human-readable status message

**Example Response - Success:**
```json
{
  "status": "ok",
  "records": [
    {
      "history_id": "history_1",
      "recorded_at": "2024-02-15T12:00:00Z",
      "project_name": "phone_stand",
      "quality": "good",
      "print_time_s": 3600,
      "material_g": 8.0,
      "material_cost_usd": 0.2,
      "alerts_count": 1,
      "interventions_count": 0
    }
  ],
  "total_count": 1,
  "message": "Found 1 record(s)"
}
```

**Filtering Examples:**
- `query_print_history(project_name="phone_stand")` — Get all prints for a project
- `query_print_history(start_date="2024-02-01", end_date="2024-02-15")` — Get prints in date range
- `query_print_history(quality_filter="excellent")` — Get only excellent prints
- `query_print_history(project_name="phone_stand", quality_filter="good")` — Combine filters

---

#### `get_print_analytics(project_name: str = "", days: int = 30) -> dict`
Generate analytics and statistics from print history for success rate, material usage, and cost tracking.

**Parameters:**
- `project_name` (str, optional): Filter analytics by project name (empty = all projects)
- `days` (int, optional): Number of past days to include (default: 30, use 0 for all time)

**Returns:** dict with keys:
- `status` (str): "ok" or "error"
- `analytics` (dict): Aggregated statistics
- `message` (str): Human-readable status message

**Analytics Fields:**
- `total_prints` (int): Total number of prints
- `success_rate_pct` (float): Percentage of excellent + good prints (0-100)
- `avg_print_time_s` (float): Average print time in seconds
- `total_material_g` (float): Total material used in grams
- `total_material_cost_usd` (float): Total material cost in USD
- `avg_cost_per_print_usd` (float): Average cost per print
- `quality_distribution` (dict): Count of prints by quality level

**Example Response - Success:**
```json
{
  "status": "ok",
  "analytics": {
    "total_prints": 10,
    "success_rate_pct": 80.0,
    "avg_print_time_s": 4320.0,
    "total_material_g": 320.0,
    "total_material_cost_usd": 8.0,
    "avg_cost_per_print_usd": 0.8,
    "quality_distribution": {
      "excellent": 4,
      "good": 4,
      "acceptable": 1,
      "poor": 1
    }
  },
  "message": "Analytics generated from 10 print(s)"
}
```

**Example Response - No History:**
```json
{
  "status": "ok",
  "analytics": {
    "total_prints": 0,
    "success_rate_pct": 0.0,
    "avg_print_time_s": 0.0,
    "total_material_g": 0.0,
    "total_material_cost_usd": 0.0,
    "avg_cost_per_print_usd": 0.0,
    "quality_distribution": {}
  },
  "message": "No print history found for given filters"
}
```

**Configuration:**
Material usage estimation uses:
- `FILAMENT_G_PER_HOUR` (default: 8.0) — Estimated filament usage rate
- `FILAMENT_COST_PER_KG` (default: 25.0) — Cost per kilogram of filament in USD

Configure via environment variables:
```bash
FILAMENT_G_PER_HOUR=8.0
FILAMENT_COST_PER_KG=25.0
```

**Workflow:**
1. After print completes, call `detect_print_completion`
2. Call `record_quality_assessment` to capture user assessment
3. Call `generate_print_summary` to aggregate monitoring data
4. Call `archive_print_metadata` to save per-project archive
5. Call `store_print_history` to add to global print history
6. Use `query_print_history` to retrieve historical records
7. Use `get_print_analytics` to analyze trends and costs

---

**OctoPrintClient Class:**
Internal class used by tool functions. Provides low-level OctoPrint API access.

**Constructor:**
```python
client = OctoPrintClient(host: str, port: int, api_key: str)
```

**Methods:**
- `test_connection() -> dict` — Test server connectivity
- `get_printer_status() -> dict` — Get printer state and temps
- `get_job_status() -> dict` — Get active job information
- `pause() -> None` — Pause current print
- `resume() -> None` — Resume paused print
- `cancel() -> None` — Cancel current print
- `tool_target(targets: dict) -> None` — Set nozzle temperature
- `bed_target(target: float) -> None` — Set bed temperature

**Validation:** Constructor validates all parameters and raises `ValueError` if invalid

---

**Configuration:**
Configure OctoPrint connection via environment variables or `.env` file:
```bash
OCTOPRINT_HOST=192.168.1.100
OCTOPRINT_PORT=5000
OCTOPRINT_API_KEY=your-api-key-here
```

Optional config variables (with defaults):
- `OCTOPRINT_HOST` (default: "localhost")
- `OCTOPRINT_PORT` (default: "5000")
- `OCTOPRINT_API_KEY` (no default; must be provided)

**Requirements:**
- OctoPrint server must be running and accessible
- Valid API key required for authentication
- Network connectivity to printer server

---

**Output Structure:**
Monitor phase outputs stored in `{PROJECTS_DIR}/{project_name}/monitoring/`:
```
projects/
├── print_history.json       # Global print history for cross-project analytics (TICKET-021)
└── {project_name}/
    └── monitoring/
        ├── metrics.jsonl            # Time-series metric snapshots (TICKET-017)
        ├── alerts.json              # Persisted formatted alerts (TICKET-018)
        ├── interventions.json       # Log of user actions (pause/resume/cancel/temp adjust) (TICKET-019)
        ├── quality_assessment.json  # User quality assessment after completion (TICKET-020)
        ├── print_summary.json       # Comprehensive print summary with recommendations (TICKET-020)
        └── archive.json             # Historical archive of completed prints (TICKET-020)
```

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

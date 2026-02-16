# System Architecture

The 3D-ADK system is a multi-agent 3D printing automation platform built on Google ADK. It orchestrates a complete workflow from design concept to print monitoring.

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Interface (CLI)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                   Coordinator Agent (LlmAgent)                   │
│  - Create projects, manage sessions                             │
│  - Route to sub-agents, validate phase transitions              │
│  - 14 FunctionTools: create_session, advance_phase, etc.        │
└────────────────────────────┬────────────────────────────────────┘
                    ┌────────┴────────┬─────────────┐
                    │                 │             │
        ┌───────────▼──────┐  ┌──────▼────────┐   │
        │  Design Agent    │  │ Modeling Agent │   │
        │  (Phase 1)       │  │ (Phase 2)      │   │
        │  4 tools         │  │ 7 tools        │   │
        └──────────────────┘  └────────────────┘   │
                                                   │
                                        ┌──────────▼──────────┐
                                        │  Monitor Agent      │
                                        │  (Phase 3)          │
                                        │  15 tools           │
                                        └─────────────────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
     ┌──────▼──────┐  ┌──────▼──────┐  ┌────▼───────┐
     │   Memory    │  │  Artifacts  │  │  Sessions  │
     │  Service    │  │  Service    │  │  Service   │
     │             │  │             │  │            │
     │ Conversation│  │ File Storage│  │ State      │
     │ History     │  │ (JSON, STL) │  │ Persistence│
     └─────────────┘  └─────────────┘  └────────────┘
```

## Component Details

### Agents (4 total)

#### Coordinator Agent
- **Responsibility:** Orchestrate the entire workflow
- **Implementation:** `LlmAgent` with 14 `FunctionTool`-wrapped functions
- **Tools:**
  - Session Management: `create_project_session`, `get_project_status`, `list_project_sessions`
  - Phase Control: `advance_phase`, `backtrack_phase`, `approve_design`, `mark_model_exported`, `mark_print_started`
  - File Management: `get_project_structure`, `organize_project_files`, `create_design_version`, `list_design_versions`, `backup_project`, `export_project`
- **Sub-Agents:** Delegates to design_agent, modeling_agent, monitor_agent based on phase

#### Design Agent
- **Responsibility:** Conduct design interviews and generate conceptual sketches/renderings
- **Phase:** Design (Phase 1)
- **Implementation:** `LlmAgent` with 4 `FunctionTool` tools
- **Tools:** `conduct_interview`, `generate_sketches`, `generate_images`, `generate_blueprint`
- **Outputs:** `interview.json`, sketch images, rendered images, `design_specs.json`, technical blueprints

#### Modeling Agent
- **Responsibility:** Generate 3D models and export to printer-ready formats
- **Phase:** Modeling (Phase 2)
- **Implementation:** `LlmAgent` with 7 `FunctionTool` tools
- **Tools:** `generate_model`, `render_preview`, `export_model`, `analyze_printability`, `optimize_parameters`, and helper tools
- **Inputs:** `design_specs.json` from Design Agent
- **Outputs:** OpenSCAD (.scad), preview images, STL/3MF files, printability analysis, print recommendations

#### Monitor Agent
- **Responsibility:** Connect to OctoPrint, monitor print progress, detect issues, track quality
- **Phase:** Monitor (Phase 3)
- **Implementation:** `LlmAgent` with 15 `FunctionTool` tools
- **Tools:** OctoPrint integration, metrics collection, issue detection, alerts, quality assessment, history tracking (19 tools total)
- **Integrations:** OctoPrint API, real-time print metrics
- **Outputs:** Print logs, metrics JSONL, quality assessments, print history

### Services Layer

Services provide persistent state and data management across the agent lifecycle.

#### Session Service (`src/services/sessions.py`)
- **Purpose:** Persist project state across restarts
- **Data:** Project name, current phase, phase flags (design_approved, model_exported, print_started)
- **Storage:** JSON files in `SESSIONS_DIR/`
- **Lifecycle:** Created by coordinator on `create_project_session`, updated by agents on phase transitions

#### Artifact Service (`src/services/artifacts.py`)
- **Purpose:** Manage file organization and artifact persistence
- **Data:** Design files, models, renders, exports
- **Storage:** Hierarchical directory structure: `projects/{project_name}/{design,model,print}/`
- **Features:** File versioning, cleanup, export packaging

#### Memory Service (`src/services/memory.py`)
- **Purpose:** Track conversation history and design decisions
- **Data:** Interview responses, refinement requests, agent reasoning traces
- **Storage:** JSON format in `projects/{project_name}/memory/`
- **Usage:** Context for regeneration requests, design consistency

### Data Flow

```
1. Design Phase:
   User Input → Interview → interview.json
            → Sketches → sketch images (5 variations)
            → Refined Images → rendered views (perspective variations)
            → Blueprint → design_specs.json + technical blueprint

2. Modeling Phase:
   design_specs.json → OpenSCAD Generation → project.scad
                   → Validation → printability_analysis.json
                   → Optimization → optimization_recommendations.json
                   → Export → model.stl / model.3mf + preview images

3. Monitor Phase:
   OctoPrint Connection → Print Status → metrics.jsonl (real-time updates)
                      → Issue Detection → issues.json
                      → Completion → quality_assessment.json + print_history.json
```

## Module Organization

```
src/
├── agents/              # 4 LlmAgent implementations
│   ├── coordinator.py   # Coordinator agent + sub-agent routing
│   ├── design.py        # Design phase agent
│   ├── modeling.py      # Modeling phase agent
│   └── monitor.py       # Monitor phase agent
│
├── tools/               # Tool implementations (FunctionTool-wrapped functions)
│   ├── coordinator_tools.py    # 14 tools: session/file/phase management
│   ├── design_tools.py         # 4 tools: interview, sketch, image, blueprint
│   ├── modeling_tools.py       # 7 tools: model generation, export, optimization
│   └── monitor_tools.py        # 15 tools: OctoPrint, metrics, issues, history
│
├── services/            # Business logic layer
│   ├── sessions.py      # Session state persistence
│   ├── artifacts.py     # File management
│   └── memory.py        # Conversation history
│
├── config.py            # Configuration loading from environment
├── session.py           # Session data model
├── cli.py               # Interactive CLI interface
├── main.py              # Entry point
└── utils.py             # Shared utilities
```

## Communication Patterns

### Agent-to-Agent Communication
Agents communicate through **AgentTool delegation** via the Google ADK framework:
- Each agent has access to `InvocationContext` which provides access to other agents
- Sub-agents are called via `AgentTool` within the coordinator
- Messages flow through the LLM (coordinator doesn't directly call sub-agent functions)

### Agent-to-Service Communication
Agents access services through imported modules:
```python
from src.services.sessions import ProjectSessionService
from src.services.artifacts import ArtifactService
```
Services are stateless; all data persists to disk (JSON files).

### Tool Input/Output
All tools:
1. Accept typed parameters with validation
2. Return structured dict responses with `status` ("ok"/"error") and relevant data
3. Never raise exceptions (return error dict instead)
4. Log all execution via Python `logging` module

Example:
```python
async def create_project_session(project_name: str) -> dict:
    if not project_name or not isinstance(project_name, str):
        return {"status": "error", "message": "Invalid project name"}

    # ... implementation ...

    return {
        "status": "ok",
        "session_id": "abc123...",
        "project_name": project_name,
        "current_phase": "design"
    }
```

## Configuration & Environment

All configuration is loaded from environment variables (see `src/config.py`):

**Required:**
- `ANTHROPIC_API_KEY` - Claude API access

**Recommended:**
- `LLM_MODEL` - Model to use (default: `claude-opus-4-6`)
- `OPENSCAD_PATH` - Path to OpenSCAD binary (default: `/usr/local/bin/openscad`)
- `OCTOPRINT_HOST`, `OCTOPRINT_PORT`, `OCTOPRINT_API_KEY` - OctoPrint integration

**Optional:**
- `LOG_LEVEL` - Logging verbosity
- `PROJECTS_DIR`, `SESSIONS_DIR` - Storage locations
- `FILAMENT_COST_PER_KG`, `FILAMENT_G_PER_HOUR` - Cost/weight estimation

## External Dependencies

- **Google ADK** - Agent framework (`google.adk` library)
- **Claude API** - LLM backend via Anthropic SDK
- **OpenSCAD** - 3D modeling engine (external binary)
- **OctoPrint** - 3D printer management API
- **PIL/Pillow** - Image generation
- **octorest** - OctoPrint Python client

## Key Design Principles

1. **Modularity** - Each agent is independent; tools are composable
2. **Async/Await** - All tools are async for concurrent operations
3. **Error Handling** - Return error dicts, never raise exceptions
4. **Persistence** - All state saved to disk for reliability
5. **Type Safety** - Full type hints throughout
6. **Logging** - Comprehensive logging for debugging

---

**For detailed specifications, see:**
- [../specs/ADK_IMPLEMENTATION_SPEC.md](../specs/ADK_IMPLEMENTATION_SPEC.md)
- [../specs/COORDINATOR_AGENT_SPEC.md](../specs/COORDINATOR_AGENT_SPEC.md)
- [../specs/DESIGN_AGENT_SPEC.md](../specs/DESIGN_AGENT_SPEC.md)
- [../specs/MODELING_AGENT_SPEC.md](../specs/MODELING_AGENT_SPEC.md)
- [../specs/MONITOR_AGENT_SPEC.md](../specs/MONITOR_AGENT_SPEC.md)

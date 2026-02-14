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
Manages project state.
- `create_session(session_id, metadata)` - Start project
- `get_session(session_id)` - Load project
- `update_session(session_id, updates)` - Update state

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

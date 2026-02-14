# User Workflow

## Three-Phase Workflow

### Phase 1: Design
User describes what they want to 3D print. The Design Agent:
- Conducts an interview to gather requirements
- Generates conceptual sketches
- Creates detailed rendered images
- Produces technical blueprint and specifications

**Output:** `design_specs.json` with all design information

### Phase 2: Modeling
Converts approved design into a 3D printable model. The Modeling Agent:
- Generates parametric OpenSCAD code
- Validates printability
- Exports STL/3MF files

**Output:** `project.scad` and `model.stl` ready for printing

### Phase 3: Monitor
Oversees actual 3D print execution. The Monitor Agent:
- Connects to OctoPrint printer interface
- Tracks print metrics in real-time
- Detects issues and alerts user
- Documents completion and quality

**Output:** Print logs and quality assessment

## User Commands

- `status` - Show current phase and progress
- `next` - Advance to next phase
- `back` - Return to previous phase
- `help` - Show available commands
- `regenerate` - Regenerate design outputs (design phase only)

## Data Flow

```
Interview Responses
  ↓
[Design Agent] → Sketches, Images, Blueprint
  ↓
[Approve Design]
  ↓
[Modeling Agent] → OpenSCAD Model, STL File
  ↓
[Export to Printer]
  ↓
[Monitor Agent] → Real-time Print Monitoring
  ↓
[Print Complete]
```

**For detailed workflow specifications:** See [../specs/DESIGN_AGENT_SPEC.md](../specs/DESIGN_AGENT_SPEC.md), [../specs/MODELING_AGENT_SPEC.md](../specs/MODELING_AGENT_SPEC.md), [../specs/MONITOR_AGENT_SPEC.md](../specs/MONITOR_AGENT_SPEC.md)

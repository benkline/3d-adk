# User Workflow

Complete guide to the 3D-ADK three-phase printing workflow.

## Three-Phase Workflow Overview

### Phase 1: Design
User describes what they want to 3D print. The Design Agent:
- Conducts an interview to gather requirements (form factor, materials, constraints)
- Generates conceptual sketches (5 variations)
- Creates detailed rendered images (multiple perspectives)
- Produces technical blueprint and detailed specifications

**Key outputs:**
- `interview.json` - Raw interview responses
- Sketch images (5 variations)
- Rendered images (4+ perspectives)
- `design_specs.json` - Technical specifications for modeling
- `blueprint.md` - Human-readable technical blueprint

**Status flags:**
- `design_approved: bool` - Must be true to advance to Modeling

### Phase 2: Modeling
Converts approved design into a 3D printable model. The Modeling Agent:
- Generates parametric OpenSCAD code from design specs
- Validates printability (wall thickness, overhangs, supports)
- Provides optimization recommendations
- Exports STL/3MF files ready for slicing

**Key outputs:**
- `project.scad` - Parametric OpenSCAD source code
- Preview images (7 perspectives)
- `model.stl` - Ready-to-print STL file
- `model.3mf` - 3MF with metadata
- `printability_analysis.json` - Feasibility and warnings
- `optimization_recommendations.json` - Print settings

**Status flags:**
- `model_exported: bool` - Must be true to advance to Monitor

### Phase 3: Monitor
Oversees actual 3D print execution. The Monitor Agent:
- Connects to OctoPrint printer interface
- Tracks print metrics in real-time (progress, temps, filament)
- Detects issues (temperature anomalies, filament jams, etc.)
- Alerts user to problems requiring intervention
- Documents completion and quality assessment
- Maintains print history and analytics

**Key outputs:**
- `metrics.jsonl` - Real-time print metrics (streaming format)
- `issues.json` - Issues detected during print
- `quality_assessment.json` - User-provided quality rating
- `print_history.json` - Global print history

**Status flags:**
- `print_started: bool` - Prevents backtracking to earlier phases once set

## CLI Commands

The interactive CLI (`3d-adk>` prompt) provides these commands:

### Session Management

#### `new <project_name>`
Create a new 3D printing project session.

```bash
3d-adk> new phone_stand
✓ Created project: phone_stand
✓ Session ID: 8f4a9c2a
✓ Current phase: design
```

Starts in the Design phase automatically.

#### `resume`
List all existing sessions and resume one.

```bash
3d-adk> resume
Available sessions:
  1. phone_stand (8f4a9c2a) - design phase
  2. cable_organizer (3b7f1e44) - modeling phase
  3. plant_pot (9d2b5e11) - monitor phase

Enter session number to load (or press Enter to cancel): 1
Loaded project: phone_stand
```

#### `status`
Show current project status and phase progress.

```bash
3d-adk> status
Project: phone_stand
Current Phase: design
Session ID: 8f4a9c2a (shows first 8 chars)

Progress:
  ✓ Design Approved: No (design_approved=false)
  ✓ Model Exported: No (model_exported=false)
  ✓ Print Started: No (print_started=false)

Created: 2025-02-15 10:00:00
Updated: 2025-02-15 10:05:00
```

### Phase Control

#### `next`
Advance to the next phase (Design → Modeling → Monitor).

```bash
3d-adk> next
Advancing from design to modeling...

Requirements check:
  ✓ Design approval: true

✓ Successfully advanced to modeling phase
Current phase: modeling
```

**Phase transition gates:**
- Design → Modeling: Requires `design_approved = true`
  - Design Agent must approve design before you can proceed
  - Run design tools to completion first
- Modeling → Monitor: Requires `model_exported = true`
  - Model must be exported to STL/3MF format
- Cannot skip phases (Design → Monitor requires going through Modeling)

#### `back`
Return to the previous phase (Monitor → Modeling, Modeling → Design).

```bash
3d-adk> back
Backtracking from modeling to design...

Safety checks:
  ✓ No active print (print_started=false)

✓ Successfully backed up to design phase
Current phase: design
```

**Backtrack constraints:**
- Design → Can always go back (no constraints)
- Modeling → Can go back if print hasn't started
- Monitor → Cannot backtrack if print_started=true (safety)

**Data preservation:** Backtracking keeps all design/model files intact; you can advance again later.

#### `help`
Display available commands and syntax.

```bash
3d-adk> help
Available commands:
  new <name>      Create new project
  resume          List and resume existing project
  status          Show current project status
  next            Advance to next phase
  back            Go back to previous phase
  exit / quit     Exit the CLI

Type 'help' for this message.
```

### Design Phase Specific

#### `regenerate`
(Design phase only) Regenerate sketches, images, or blueprints.

```bash
3d-adk> regenerate
What would you like to regenerate?
  1. Sketches
  2. Rendered images
  3. Complete blueprint
  4. All outputs

Enter choice (1-4): 2
Regenerating rendered images...
✓ Generated 4 new image variations
```

**Usage:** Use when you want different creative directions or refine based on feedback.

### Project Management Commands

Additional commands available for file/backup management:

#### `list_sessions` / `get_project_status`
(Advanced) Query session or file information.

#### File Management (via status/details)
The coordinator maintains:
- Version history: Design snapshots saved before major changes
- Backups: Automatic backup before advancing phases
- Exports: Package entire project as .zip

See [ARCHITECTURE.md](ARCHITECTURE.md) for details on backup/export tools available through the coordinator agent.

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Phase 1: Design                          │
│  User describes desired object → Design Agent conducts          │
│  interview and generates sketches, images, blueprint            │
│  Outputs: interview.json, design_specs.json, images, blueprint  │
└─────────────────────────────────────────────┬───────────────────┘
                                              │
                                   [Approve Design]
                                   (design_approved = true)
                                              │
┌─────────────────────────────────────────────▼───────────────────┐
│                     Phase 2: Modeling                           │
│  Modeling Agent generates OpenSCAD code from design specs       │
│  Validates printability, creates rendered previews, exports STL │
│  Outputs: project.scad, model.stl, printability_analysis.json  │
└─────────────────────────────────────────────┬───────────────────┘
                                              │
                                  [Export to Printer]
                                  (model_exported = true)
                                              │
┌─────────────────────────────────────────────▼───────────────────┐
│                     Phase 3: Monitor                            │
│  Monitor Agent connects to OctoPrint, tracks real-time metrics  │
│  Detects issues, alerts user, completes print, tracks quality  │
│  Outputs: metrics.jsonl, issues.json, quality_assessment.json  │
└─────────────────────────────────────────────┬───────────────────┘
                                              │
                                       [Print Complete]
                                       (print_started = true)
                                              │
                          Project archived to print history
```

## Session State Model

Each session maintains state flags that control workflow:

```json
{
  "session_id": "8f4a9c2a",
  "project_name": "phone_stand",
  "current_phase": "design",
  "design_approved": false,
  "model_exported": false,
  "print_started": false,
  "created_at": "2025-02-15T10:00:00",
  "updated_at": "2025-02-15T10:05:00"
}
```

**Flag meanings:**
- `design_approved`: User has approved design, ready for modeling
- `model_exported`: Model successfully exported to STL/3MF, ready for printing
- `print_started`: Print job has begun on OctoPrint (blocks backtracking)

Flags advance from left to right:
1. Start: All false
2. After Design phase: `design_approved = true`
3. After Modeling phase: `model_exported = true`
4. During Monitor phase: `print_started = true`

## Complete Example Workflow

### 1. Create Project

```bash
$ python src/main.py
3d-adk> new "coffee_mug_holder"
✓ Project created: coffee_mug_holder
✓ Session: 9c4f2e8b
3d-adk [9c4...]>
```

### 2. Design Phase

```bash
3d-adk [9c4...]> # Design Agent is working...
# Agent conducts interview, generates sketches/images/blueprint
# User reviews and approves

[Design outputs available]:
- interview.json: {object_name: "coffee mug holder", ...}
- Sketches: 5 design variations
- Images: front, side, isometric views of best design
- Blueprint: Technical specs and dimensions
```

### 3. Approve and Advance

```bash
3d-adk [9c4...]> next
Advancing to modeling phase...
✓ Design approved (design_approved flag set)
✓ Now in modeling phase
```

### 4. Modeling Phase

```bash
3d-adk [9c4...]> # Modeling Agent is working...
# Agent generates OpenSCAD code, validates printability
# Exports STL file for printing
# Provides optimization recommendations

[Modeling outputs available]:
- project.scad: Parametric source code
- model.stl: Ready-to-print file
- model.3mf: Alternative format
- printability_analysis.json: Feasibility report
- optimization_recommendations.json: Slice settings
```

### 5. Export and Move to Monitoring

```bash
3d-adk [9c4...]> next
Advancing to monitor phase...
✓ Model exported (model_exported flag set)
✓ Now in monitor phase
```

### 6. Monitor Phase

```bash
3d-adk [9c4...]> # Monitor Agent connects to OctoPrint
# Real-time tracking begins
# Temperature, progress, filament usage monitored
# Any issues detected and alerts shown

[Print underway]:
Progress: 45%
Temperature: Nozzle 210°C (target 210°C) ✓
Filament: 12.3g used / 87.7g remaining
Elapsed: 2h 15m / Est. 5h total
```

### 7. Print Complete

```bash
# Monitor phase completes after print finishes
✓ Print completed successfully
✓ Quality assessment recorded
✓ Project archived to print history

3d-adk [9c4...]> status
Project: coffee_mug_holder
Current Phase: monitor (complete)
Print Quality: Excellent
Duration: 5h 23m
```

## Troubleshooting Workflows

### Stuck in Design Phase?
- Check if sketches and blueprint were generated
- Review `design_specs.json` for completeness
- Use `regenerate` command if designs don't match requirements
- Then advance to modeling

### Model Not Exporting?
- Check `printability_analysis.json` for warnings
- Use optimization recommendations
- Ensure OpenSCAD binary is at correct path (see SETUP_GUIDE.md)
- Review error logs: `LOG_LEVEL=DEBUG python src/main.py`

### Can't Connect to OctoPrint?
- Verify OctoPrint is running: `http://printer-ip:5000`
- Check API key is correct in `.env`
- Verify network connectivity: `ping printer-ip`
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed OctoPrint debugging

### Need to Go Back and Fix Design?
```bash
3d-adk> back
# Returns to design phase
# All design files preserved
# Can regenerate sketches/images
# Re-approve when ready
3d-adk> next
# Resumes to modeling
```

## Advanced Usage

### Batch Project Creation
```bash
# Script to create multiple projects
for name in phone_stand cable_organizer plant_pot; do
  echo "new $name" | python src/main.py --interactive
done
```

### Export Projects
```bash
# From CLI (if implemented in coordinator tools)
3d-adk> export_project
# Creates zip archive of entire project
```

### View Print History
```bash
# Query completed prints
# Shows success rates, material usage, costs
# Analytics by project, date range, etc.
```

---

**For technical details:**
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [../specs/DESIGN_AGENT_SPEC.md](../specs/DESIGN_AGENT_SPEC.md) - Design phase details
- [../specs/MODELING_AGENT_SPEC.md](../specs/MODELING_AGENT_SPEC.md) - Modeling phase details
- [../specs/MONITOR_AGENT_SPEC.md](../specs/MONITOR_AGENT_SPEC.md) - Monitor phase details

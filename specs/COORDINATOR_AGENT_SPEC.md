# 3D-ADK Coordinator Agent Specification

## Overview
The main orchestrating agent that manages workflow progression through all three phases and coordinates sub-agents.

## Responsibilities

### 1. Workflow State Management
- Track current phase (design, modeling, monitor)
- Maintain session state across phase transitions
- Store user context and previous decisions
- Handle phase backtracking and iterations

### 2. Sub-Agent Routing
- Route user inputs to appropriate sub-agent based on current phase
- Receive and validate outputs from sub-agents
- Handle data transformation between agents
- Manage inter-agent communication

### 3. File and Context Management
- Maintain project directory structure
- Store design specifications
- Manage model files and exports
- Archive print history and logs
- Version control for design iterations

### 4. User Interface & Experience
- Provide clear phase indicators
- Display available actions in current phase
- Offer phase navigation options (next, back, restart)
- Summarize progress and current state
- Present consolidated information from all sub-agents

## Data Model

### Session State
```json
{
  "session_id": "uuid",
  "project_name": "string",
  "current_phase": "design|modeling|monitor",
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "design_approved": boolean,
  "model_exported": boolean,
  "print_started": boolean
}
```

### Project Context
```json
{
  "design_specs": {...},
  "design_images": [...],
  "blueprint_path": "string",
  "model_path": "string",
  "stl_exports": [...],
  "print_logs": [...]
}
```

## Phase Transitions

### Design → Modeling
- Requires: Design approval confirmation
- Validates: Blueprint completeness
- Transfers: Design specs and blueprints
- Creates: Model workspace

### Modeling → Monitor
- Requires: Model export confirmation
- Validates: STL file readiness
- Transfers: Exported STL files
- Connects: OctoPrint integration

### Backtrack Options
- Modeling → Design: For design changes
- Monitor → Modeling: For model adjustments (if print not started)

## API Contract with Sub-Agents

### Design Agent Interface
```
Input: user_message (string), design_context (dict)
Output: {
  "action": "interview|generate_sketches|generate_images|create_blueprint",
  "content": {...},
  "design_approved": boolean,
  "next_action": string
}
```

### Modeling Agent Interface
```
Input: blueprint (dict), design_specs (dict)
Output: {
  "status": "processing|ready|error",
  "model_preview": "image_path",
  "exported_files": [paths],
  "printability_report": {...},
  "next_action": string
}
```

### Monitor Agent Interface
```
Input: stl_files (list), octoprint_config (dict)
Output: {
  "status": "connected|printing|paused|completed|error",
  "print_metrics": {...},
  "issues_detected": [...],
  "next_action": string
}
```

## Error Handling

### Sub-Agent Failures
- Log error with context
- Offer retry option
- Allow user to backtrack to previous phase
- Store error logs for diagnostics

### State Inconsistencies
- Validate state transitions
- Prevent invalid phase changes
- Recover from partial updates
- Maintain data integrity

## Configuration

### Project Structure
```
project_name/
├── design/
│   ├── interview.json
│   ├── sketches/
│   ├── images/
│   └── blueprint.md
├── model/
│   ├── project.scad
│   ├── preview.png
│   └── exports/
│       ├── model.stl
│       └── model.3mf
├── print/
│   ├── print_log.json
│   └── status_history.jsonl
└── session.json
```

## Success Criteria

- [ ] Seamless phase transitions
- [ ] Context preserved across all phases
- [ ] User can navigate between phases without losing data
- [ ] All sub-agent outputs properly integrated
- [ ] Clear status reporting at each stage

# 3D-ADK Agent System Plan

## Overview
A multi-phase Google-ADK agent system that guides users through the complete 3D printing workflow: from initial design conception through final print monitoring. The system coordinates three specialized sub-agents working within a larger orchestrating agent.

---

## Architecture

### Main Coordinator Agent
- Manages workflow progression through three phases
- Routes user inputs to appropriate sub-agents
- Maintains context across phase transitions
- Provides unified UI/UX experience
- Handles cross-phase decisions and file management

### Three Sub-Agents

1. **Design Phase Agent** - Concept to Blueprint
2. **Modeling Phase Agent** - CAD Generation
3. **Print Monitor Agent** - OctoPrint Integration

---

## Phase 1: Design Phase

### Objective
Translate user requirements into visual design specifications and technical blueprints.

### Workflow
1. **Interview Mode**
   - Conducts structured conversation with user about desired object
   - Gathers constraints (size, material, function, aesthetics, etc.)
   - Asks clarifying follow-up questions
   - Refines understanding through iterative prompts

2. **Sketch Generation**
   - Creates initial conceptual sketches based on interview
   - Shows multiple design options/angles
   - Presents ideas for user feedback

3. **Image Generation**
   - Produces detailed visual renders of approved sketches
   - Shows multiple perspectives and variations
   - Allows user to request modifications/regeneration
   - Documents aesthetic and functional requirements visually

4. **Blueprint Creation**
   - Generates technical specifications
   - Documents dimensions, tolerances, materials
   - Creates assembly diagrams if multi-part
   - Specifies print orientation, support requirements
   - Outputs formal blueprint documentation

### Regeneration Loop
- User can request image/blueprint regenerations at any point
- Maintains conversation context for consistent design language
- Updates stored design specs with refinements

### Outputs
- Collection of concept sketches
- High-quality rendered images
- Technical blueprint document
- Design specifications JSON/file

---

## Phase 2: Modeling Phase

### Objective
Convert approved designs into ready-to-print 3D CAD models.

### Workflow
1. **Design Input Processing**
   - Receives finalized blueprints from Design Phase Agent
   - Extracts technical specifications and constraints
   - Validates model feasibility

2. **OpenSCAD Model Generation**
   - Creates parametric 3D models using OpenSCAD
   - Builds modular/parametric design when appropriate
   - Generates preview renderings
   - Applies design-phase specifications (dimensions, tolerances)

3. **Model Refinement**
   - Validates model printability
   - Checks for structural integrity
   - Optimizes geometry for print settings
   - Adjusts infill, wall thickness, support requirements

4. **Export & Preparation**
   - Generates STL/3MF files for 3D printer
   - Creates sliced files if multi-part
   - Documents model parameters
   - Saves OpenSCAD source code for future modifications

### Quality Assurance
- Model preview validation
- Dimension verification against blueprints
- Printability analysis
- Support structure planning

### Outputs
- OpenSCAD source files (parametric)
- Rendered 3D model previews
- Sliced/ready-to-print files (STL/3MF)
- Model specification document

---

## Phase 3: Print Monitor Agent

### Objective
Oversee actual 3D printing process and provide real-time monitoring/intervention.

### Workflow
1. **OctoPrint Integration**
   - Connects to OctoPrint API
   - Monitors print queue and active prints
   - Tracks real-time print status and metrics

2. **Print Monitoring**
   - Reports current layer, print time, ETA
   - Monitors print bed temperature, nozzle temperature
   - Detects potential issues (layer shifts, adhesion problems, filament jams)
   - Provides periodic status updates

3. **Issue Detection & Response**
   - Identifies print anomalies in real-time
   - Provides intervention suggestions
   - Can pause/resume prints if needed
   - Documents print failures with diagnostics

4. **Print Completion**
   - Confirms successful print completion
   - Documents print time, filament used, quality assessment
   - Archives print metadata
   - Suggests post-processing steps

### User Interaction Points
- Pause/resume/cancel commands
- Print history and statistics
- Quality assessment feedback
- Troubleshooting assistance

### Outputs
- Print logs and metrics
- Issue reports with diagnostics
- Print completion confirmation
- Quality assessment documentation

---

## Workflow Integration

### Phase Transitions
```
[User Interview]
    ↓
[Design Phase Agent] → Sketches, Images, Blueprints
    ↓
[Approve Design]
    ↓
[Modeling Phase Agent] → OpenSCAD Model, STL Files
    ↓
[Export to Printer]
    ↓
[Print Monitor Agent] → Real-time Monitoring
    ↓
[Print Completion]
```

### Context Persistence
- All design decisions and files maintained across phases
- User can backtrack to previous phases for modifications
- Design changes trigger re-modeling automatically
- Historical record of all iterations

### File Management
- Design phase outputs → Blueprint documents
- Modeling phase inputs from blueprint → OpenSCAD scripts
- Modeling phase outputs → STL files → OctoPrint queue
- All phases maintain versioning and change logs

---

## Key Features

### Design Phase
- ✓ Conversational interview system
- ✓ AI-generated sketches & renders
- ✓ Iterative regeneration on feedback
- ✓ Technical blueprint extraction
- ✓ Design spec documentation

### Modeling Phase
- ✓ Parametric CAD generation (OpenSCAD)
- ✓ Automatic printability analysis
- ✓ Multi-part model support
- ✓ Print-ready file generation
- ✓ Model preview visualization

### Print Monitor Phase
- ✓ Real-time OctoPrint integration
- ✓ Automated issue detection
- ✓ Print failure analysis
- ✓ Quality metrics tracking
- ✓ Post-print recommendations

---

## Future Enhancements

- AI-driven print failure prediction
- Automatic model optimization for specific printer models
- Multi-material design support
- Design template library
- Print history analytics
- Integration with filament inventory management
- Automatic support structure generation optimization
- Cost estimation for prints

---

## Technology Stack

- **Framework**: Google ADK
- **Design Visualization**: Image generation API
- **CAD**: OpenSCAD
- **3D Printer Interface**: OctoPrint API
- **File Formats**: STL, 3MF, OpenSCAD scripts
- **Data Storage**: Design specs, print logs, model archives

---

## Success Criteria

1. **Design Phase**: User can describe an object and receive professional-quality blueprints
2. **Modeling Phase**: Generate print-ready models from any approved design
3. **Print Monitor Phase**: Track and manage prints with real-time feedback
4. **Integration**: Seamless workflow from concept to finished print
5. **UX**: Intuitive phase transitions and context preservation

---

## Notes for Context Rebuild

This plan establishes three distinct agents with clear responsibilities:
- **Design Agent**: Vision & Specification
- **Modeling Agent**: Technical Implementation
- **Monitor Agent**: Execution & Diagnostics

Each agent maintains independence while the coordinator ensures seamless data flow and user experience across all three phases.

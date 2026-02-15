# 3D-ADK Project Tickets

This file tracks all work items for the 3D-ADK agent system. Use `/next-ticket` skill to work through these iteratively.

---

## PHASE 0: Infrastructure & Foundation

### TICKET-001: Project Setup & Dependencies
**Status:** DONE
**Priority:** P0 (Critical)
**Phase:** Foundation

**Description:**
Set up the basic project infrastructure and install required dependencies.

**Tasks:**
- [x] Start venv with the existing alias 'venv-adk'
- [x] Create `src/` directory structure
- [x] Create `main.py` entry point for coordinator agent
- [x] Install Google ADK SDK
- [x] Install image generation libraries (PIL, requests for API calls)
- [x] Install OpenSCAD python bindings
- [x] Install OctoPrint client library
- [x] Create `requirements.txt`
- [x] Create `.env.example` for configuration
- [x] Create basic logging setup
- [x] Update `docs/SETUP_GUIDE.md` with installation steps

**Acceptance Criteria:**
- ✅ All dependencies installable without conflicts
- ✅ Project structure matches spec
- ✅ Logging configured and working
- ✅ Entry point can be executed (prints version/help)

**Testing:**
```bash
python -m venv test_env
source test_env/bin/activate
pip install -r requirements.txt
python src/main.py --help
```

---

### TICKET-002: Configuration & Session Management System
**Status:** DONE
**Priority:** P0
**Phase:** Foundation
**Depends on:** TICKET-001

**Description:**
Implement configuration loading and session state management for the coordinator agent.

**Tasks:**
- [x] Create `src/config.py` for environment configuration
- [x] Create `src/session.py` for session state management
- [x] Implement session storage (JSON-based or SQLite)
- [x] Create project directory structure generator
- [x] Implement session recovery on restart
- [x] Update `docs/API_REFERENCE.md` with Session Service API

**Acceptance Criteria:**
- ✅ Configuration loads from `.env` correctly
- ✅ Sessions persist and reload correctly
- ✅ Project directories created with proper structure
- ✅ Session state can be serialized/deserialized

**Testing:**
- ✅ Created test session and verified persistence
- ✅ Verified session recovery on restart
- ✅ All 10 acceptance tests passing

---

## PHASE 1: Design Agent Implementation

### TICKET-003: Design Agent Core Framework
**Status:** DONE
**Priority:** P1
**Phase:** Design Agent
**Depends on:** TICKET-002

**Description:**
Create the basic structure and communication interface for the Design Phase Agent.

**Tasks:**
- [x] Create `src/agents/design.py` with `LlmAgent` instantiation
- [x] Implement four async tool functions with input validation
- [x] Create error handling (returning error dicts instead of raising)
- [x] Implement logging for all tool calls
- [x] Update `docs/API_REFERENCE.md` with Design Agent API
- [x] Create 8 acceptance tests (TDD approach)

**Acceptance Criteria:**
- ✅ Agent initializes without errors
- ✅ Four tools properly wrapped with FunctionTool
- ✅ Input validation working (returns error dict on invalid input)
- ✅ Returns properly formatted dict responses
- ✅ All 8 new tests pass + all 14 prior tests still pass
- ✅ Logging implemented for tool calls

**Testing:**
- ✅ 4 agent structure tests (initialization, name, tools, model)
- ✅ 6 tool function tests (response format, validation)
- ✅ 100% of tests passing (24 total: 10 new + 14 existing)

---

### TICKET-004: Interview Mode Implementation
**Status:** DONE
**Priority:** P1
**Phase:** Design Agent
**Depends on:** TICKET-003

**Description:**
Implement the structured interview workflow to gather design requirements.

**Tasks:**
- [x] Create interview question set and flow logic
- [x] Implement multi-turn conversation handling
- [x] Create structured prompt engineering for design intent capture
- [x] Build `interview.json` storage format
- [x] Implement clarification question logic
- [x] Create interview summary generation
- [x] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- ✅ Interview completes with all required information
- ✅ Questions flow naturally based on responses
- ✅ All responses stored in interview.json
- ✅ Summary is comprehensive and accurate

**Example Interview Output:**
```json
{
  "object_name": "custom phone stand",
  "purpose": "desk organization",
  "dimensions": {"width": 100, "depth": 80, "height": 60},
  "materials": ["PLA", "PETG"],
  "aesthetics": "minimalist modern",
  "constraints": ["must fit iPhone 14", "non-slip bottom"],
  "special_requirements": []
}
```

---

### TICKET-005: Sketch Generation Implementation
**Status:** DONE
**Priority:** P2
**Phase:** Design Agent
**Depends on:** TICKET-004

**Description:**
Implement conceptual sketch generation from interview results.

**Tasks:**
- [x] Create image prompt engineering from design brief (Claude-based)
- [x] Implement image generation API calls (structure prepared)
- [x] Handle multiple sketch variations (3-5 options)
- [x] Add sketch annotation and metadata
- [x] Create sketch storage and organization
- [x] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- ✅ Generates 3-5 distinct sketch variations with engineered prompts
- ✅ Sketches stored with metadata in organized structure
- ✅ Prompts designed to match design brief requirements
- ✅ File organization is logical with per-sketch directories
- ✅ All 6 new tests passing + all 9 existing tests still passing

**Implementation Details:**
- Uses Claude Opus to engineer 5 distinct image generation prompts from design brief
- Creates unique sketch records with metadata (ID, variation, prompt, timestamp)
- Stores sketches in `projects/{project}/design/sketches/` with per-sketch directories
- Maintains metadata.json for tracking all sketches and generation history
- Includes robust error handling and fallback prompt generation

**Prompting Guidance Implemented:**
- ✅ Emphasize form and proportion over detail
- ✅ Request multiple viewing angles
- ✅ Include material/finish in generation

---

### TICKET-006: Image Generation & Refinement
**Status:** DONE
**Priority:** P2
**Phase:** Design Agent
**Depends on:** TICKET-005

**Description:**
Implement high-quality image rendering and iteration.

**Tasks:**
- [x] Create refined image generation prompts
- [x] Implement multi-perspective rendering (front, side, 3/4, top)
- [x] Add material and finish variations
- [x] Implement image regeneration on user feedback
- [x] Create image metadata storage
- [x] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- ✅ Generates production-quality renders (using Claude-engineered prompts)
- ✅ Multiple perspectives available (front, side, 3d, top with validation)
- ✅ Material/finish variations work correctly (included in prompt context)
- ✅ Regeneration maintains design consistency (feedback parameter for iterative refinement)

**Implementation Details:**
- Added helper functions: _get_images_dir, _load_images_metadata, _save_images_metadata, _create_image_record, _engineer_image_prompts, _generate_fallback_image_prompts
- Fully implemented generate_images() with perspective validation and feedback support
- Added 7 comprehensive tests (TestImageGeneration class)
- All 22 tests passing (15 existing + 7 new)
- Created PR: https://github.com/benkline/3d-adk/pull/3

---

### TICKET-007: Blueprint Generation & Specifications
**Status:** DONE
**Priority:** P2
**Phase:** Design Agent
**Depends on:** TICKET-006

**Description:**
Generate formal technical blueprints and specifications document.

**Tasks:**
- [x] Create blueprint markdown template
- [x] Implement dimension extraction and calculation
- [x] Build technical specifications generator
- [x] Create assembly instructions generator (for multi-part)
- [x] Implement print parameter recommendations
- [x] Generate design_specs.json for modeling phase
- [x] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- ✅ Blueprint contains all required technical information
- ✅ Specifications are unambiguous and precise
- ✅ JSON schema matches modeling agent expectations
- ✅ Assembly instructions are clear if applicable

**Implementation Details:**
- ✅ Added 4 helper functions: _get_blueprint_design_dir, _calculate_specifications, _generate_blueprint_markdown, _generate_specs_json
- ✅ Full generate_blueprint implementation with error handling
- ✅ Automatic calculation of wall thickness (material-aware), infill (constraint-aware), weight, print time
- ✅ 8 comprehensive tests all passing
- ✅ API_REFERENCE.md fully documented with JSON schema and markdown structure

**Created PR:** https://github.com/benkline/3d-adk/pull/4

---

### TICKET-008: Design Phase Integration Testing
**Status:** DONE
**Priority:** P2
**Phase:** Design Agent
**Depends on:** TICKET-007

**Description:**
Test the complete design agent workflow end-to-end.

**Tasks:**
- [x] Create test cases for each design workflow
- [x] Test interview-to-blueprint pipeline
- [x] Test regeneration workflows
- [x] Verify all outputs are generated correctly
- [x] Test error handling and edge cases
- [x] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- ✅ Complete workflow produces all required outputs (TestFullPipelineOutputFiles: 3 tests)
- ✅ Regenerations work correctly (TestRegenerationWorkflows: 4 tests)
- ✅ Error handling is robust (TestErrorHandlingIntegration: 4 tests)
- ✅ Test coverage > 80% (15 integration tests + 26 existing unit tests = 41 total)

**Implementation Details:**
- Created `tests/test_design_integration.py` with 15 comprehensive integration tests
- 4 test classes: Pipeline, OutputFiles, Regeneration, ErrorHandling
- All 15 tests passing, all existing 26 tests still passing
- Tests cover: complete workflows, file creation, regenerations, error scenarios, state isolation

**Created PR:** https://github.com/benkline/3d-adk/pull/5

---

## PHASE 2: Modeling Agent Implementation

### TICKET-009: Modeling Agent Core Framework
**Status:** DONE
**Priority:** P1
**Phase:** Modeling Agent
**Depends on:** TICKET-002

**Description:**
Create the basic structure for the Modeling Phase Agent.

**Tasks:**
- [x] Create `src/agents/modeling.py` with LlmAgent definition
- [x] Implement agent initialization with four tools
- [x] Create input validation from design specs (validate_design_specs)
- [x] Implement output formatting for exports (export_model with STL/3MF support)
- [x] Setup OpenSCAD integration (generate_scad_code using solidpython2)
- [x] Update relevant documentation in `docs/API_REFERENCE.md`
- [x] Create comprehensive test suite (15 tests, all passing)

**Acceptance Criteria:**
- ✅ Agent initializes and validates design input
- ✅ OpenSCAD integration working (solidpython2 + subprocess)
- ✅ Proper response formatting (status dict pattern)
- ✅ All 15 new tests passing
- ✅ No regressions (all 14 existing tests still passing)

**Implementation:**
- Created `src/agents/modeling.py` with modeling_agent (LlmAgent with 4 tools)
- Implemented `src/tools/modeling_tools.py` with 4 async functions + 9 helpers
- Added `OPENSCAD_PATH` to `src/config.py`
- Created `tests/test_modeling.py` with 15 comprehensive tests
- Updated `docs/API_REFERENCE.md` with full Modeling Agent documentation

**PR:** https://github.com/benkline/3d-adk/pull/6

---

### TICKET-010: OpenSCAD Code Generation Engine
**Status:** TODO
**Priority:** P1
**Phase:** Modeling Agent
**Depends on:** TICKET-009

**Description:**
Implement Python-to-OpenSCAD code generation from design specifications.

**Tasks:**
- [ ] Create OpenSCAD generation engine
- [ ] Implement parametric design patterns
- [ ] Build geometric primitive generation
- [ ] Create multi-part assembly generation
- [ ] Implement module and function generation
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Generates valid, compilable OpenSCAD code
- Supports parametric dimensions
- Handles simple to moderately complex geometries
- Code is well-documented and readable

**Example Generated Code:**
```scad
// Generate parametric cube
module simple_box(width=100, height=80, depth=60, wall=2) {
  difference() {
    cube([width, height, depth]);
    translate([wall, wall, wall])
      cube([width-2*wall, height-2*wall, depth-2*wall]);
  }
}
simple_box();
```

---

### TICKET-011: Model Rendering & Preview
**Status:** TODO
**Priority:** P2
**Phase:** Modeling Agent
**Depends on:** TICKET-010

**Description:**
Generate preview images of OpenSCAD models.

**Tasks:**
- [ ] Integrate OpenSCAD CLI for rendering
- [ ] Generate multiple perspective views
- [ ] Create preview image storage
- [ ] Implement quality/resolution settings
- [ ] Add error handling for render failures
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Generates preview images successfully
- Multiple viewing angles available
- Images are clear and properly scaled
- Handles render errors gracefully

---

### TICKET-012: STL Export & File Generation
**Status:** TODO
**Priority:** P2
**Phase:** Modeling Agent
**Depends on:** TICKET-010

**Description:**
Export OpenSCAD models to 3D printer-ready formats.

**Tasks:**
- [ ] Implement STL export via OpenSCAD
- [ ] Generate 3MF format exports
- [ ] Create separate part exports for multi-part models
- [ ] Implement file validation
- [ ] Create export metadata documentation
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- STL files are valid and importable to slicers
- 3MF exports preserve metadata
- Multi-part exports organized correctly
- Export process is automated

---

### TICKET-013: Printability Analysis & Validation
**Status:** TODO
**Priority:** P2
**Phase:** Modeling Agent
**Depends on:** TICKET-010

**Description:**
Analyze models for printability and generate warnings/recommendations.

**Tasks:**
- [ ] Implement wall thickness validation
- [ ] Create overhang detection algorithm
- [ ] Build hollow section analysis
- [ ] Implement support structure recommendations
- [ ] Generate printability report
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Detects wall thickness violations
- Identifies overhangs requiring support
- Flags hollow internal sections
- Report is clear and actionable

**Printability Report:**
```json
{
  "feasible": true,
  "wall_thickness_ok": true,
  "warnings": ["Large overhang on top (55°)"],
  "suggestions": ["Orient 45° for reduced supports"],
  "estimates": {"print_hours": 12, "weight_g": 45}
}
```

---

### TICKET-014: Model Parameter Optimization
**Status:** TODO
**Priority:** P3
**Phase:** Modeling Agent
**Depends on:** TICKET-013

**Description:**
Optimize model parameters for printing (infill, supports, orientation).

**Tasks:**
- [ ] Implement print orientation optimization algorithm
- [ ] Create infill percentage recommendation engine
- [ ] Build support material strategy generator
- [ ] Calculate print time and weight estimates
- [ ] Implement cost estimation
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Recommends optimal print orientations
- Calculates realistic print times
- Estimates weight and material costs
- Recommendations reduce support material where possible

---

### TICKET-015: Modeling Agent Integration Testing
**Status:** TODO
**Priority:** P2
**Phase:** Modeling Agent
**Depends on:** TICKET-014

**Description:**
Test the complete modeling workflow end-to-end.

**Tasks:**
- [ ] Create test design specifications
- [ ] Test OpenSCAD generation and rendering
- [ ] Test STL export pipeline
- [ ] Test printability analysis
- [ ] Verify parameter optimization
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Complete workflow generates all required files
- Quality of outputs meets specifications
- Error handling is robust
- Test coverage > 80%

---

## PHASE 3: Print Monitor Agent Implementation

### TICKET-016: OctoPrint API Integration
**Status:** TODO
**Priority:** P1
**Phase:** Monitor Agent
**Depends on:** TICKET-002

**Description:**
Implement OctoPrint API connection and communication.

**Tasks:**
- [ ] Create `src/agents/monitor_agent.py`
- [ ] Implement OctoPrint API client wrapper
- [ ] Build connection testing and validation
- [ ] Implement authentication handling
- [ ] Create error handling and retry logic
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Successfully connects to OctoPrint instance
- API calls work correctly
- Connection errors handled gracefully
- Can query printer status

**Testing:**
```bash
# Test with OctoPrint instance (local or mock)
python -c "from src.agents.monitor_agent import OctoPrintClient; \
  client = OctoPrintClient('localhost', 'api_key'); \
  print(client.get_printer_status())"
```

---

### TICKET-017: Real-time Print Monitoring
**Status:** TODO
**Priority:** P1
**Phase:** Monitor Agent
**Depends on:** TICKET-016

**Description:**
Implement real-time monitoring of active print jobs.

**Tasks:**
- [ ] Create polling system for print status
- [ ] Implement metric collection (progress, temps, filament)
- [ ] Build status update formatting
- [ ] Create periodic status summaries
- [ ] Implement metric logging and storage
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Metrics collected accurately
- Updates generated in real-time
- Logging works correctly
- Status data properly stored

**Status Update Format:**
```json
{
  "timestamp": "2026-02-14T10:30:45Z",
  "state": "printing",
  "progress": 45.2,
  "current_layer": 120,
  "print_time_elapsed": 3600,
  "print_time_remaining": 4400,
  "bed_temp": {"current": 60, "target": 60},
  "nozzle_temp": {"current": 205, "target": 210}
}
```

---

### TICKET-018: Print Issue Detection System
**Status:** TODO
**Priority:** P2
**Phase:** Monitor Agent
**Depends on:** TICKET-017

**Description:**
Implement detection of common print issues and anomalies.

**Tasks:**
- [ ] Build temperature anomaly detection
- [ ] Implement filament jam detection logic
- [ ] Create layer shift detection (if applicable)
- [ ] Build bed adhesion issue detection
- [ ] Create nozzle clogging indicators
- [ ] Implement configurable alert thresholds
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Detects common issues with reasonable accuracy
- False positives minimized
- Alerts are timely and informative
- Configurable thresholds available

**Detection Rules:**
- Temp deviation > 10°C for > 30 seconds → warning
- No filament movement for > 60 seconds → error
- Nozzle contact detection failures → alert

---

### TICKET-019: User Alerts & Intervention System
**Status:** TODO
**Priority:** P2
**Phase:** Monitor Agent
**Depends on:** TICKET-018

**Description:**
Implement user notification and intervention capabilities.

**Tasks:**
- [ ] Create alert message formatting
- [ ] Implement pause/resume command handling
- [ ] Build temperature adjustment interface
- [ ] Create print cancellation logic
- [ ] Implement user acknowledgment tracking
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Alerts delivered clearly to user
- All commands execute correctly
- Print paused/resumed reliably
- User feedback properly recorded

---

### TICKET-020: Print Completion & Quality Assessment
**Status:** TODO
**Priority:** P2
**Phase:** Monitor Agent
**Depends on:** TICKET-017

**Description:**
Handle print completion and capture quality assessment.

**Tasks:**
- [ ] Implement print completion detection
- [ ] Create quality assessment questionnaire
- [ ] Build print summary generation
- [ ] Implement post-processing recommendations
- [ ] Create print metadata archival
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Completion detected accurately
- Quality assessment captured
- Summary contains all relevant data
- Archives accessible for later analysis

**Quality Assessment Form:**
- Overall quality (excellent/good/acceptable/poor)
- Issues encountered
- User notes
- Photo/inspection option

---

### TICKET-021: Print History & Analytics
**Status:** TODO
**Priority:** P3
**Phase:** Monitor Agent
**Depends on:** TICKET-020

**Description:**
Implement print history storage and analytics system.

**Tasks:**
- [ ] Create print history database/storage
- [ ] Implement history query interface
- [ ] Build analytics and statistics generation
- [ ] Create success rate tracking
- [ ] Implement material cost tracking
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Print history stored and retrievable
- Analytics accurate and useful
- Statistics can be queried by time period
- Cost tracking functional

**Available Analytics:**
- Success rate by model
- Average print times
- Material usage trends
- Cost per project

---

### TICKET-022: Monitor Agent Integration Testing
**Status:** TODO
**Priority:** P2
**Phase:** Monitor Agent
**Depends on:** TICKET-021

**Description:**
Test the complete monitoring workflow with OctoPrint.

**Tasks:**
- [ ] Create mock OctoPrint for testing
- [ ] Test complete print workflow
- [ ] Test issue detection and alerts
- [ ] Test completion and quality assessment
- [ ] Verify history storage
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- All workflows function correctly
- Mock OctoPrint testing works
- Real OctoPrint integration tested
- Test coverage > 80%

---

## PHASE 4: Coordinator Agent & Integration

### TICKET-023: Coordinator Agent Core Framework
**Status:** TODO
**Priority:** P1
**Phase:** Coordinator
**Depends on:** TICKET-003, TICKET-009, TICKET-016

**Description:**
Implement the main coordinator agent that orchestrates all three sub-agents.

**Tasks:**
- [ ] Create `src/agents/coordinator.py`
- [ ] Implement phase management system
- [ ] Build sub-agent routing logic
- [ ] Create cross-phase communication
- [ ] Implement session orchestration
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Routes to correct sub-agent based on phase
- Maintains session state across agents
- Handles phase transitions
- Error handling for inter-agent communication

---

### TICKET-024: Phase Transitions & State Management
**Status:** TODO
**Priority:** P1
**Phase:** Coordinator
**Depends on:** TICKET-023

**Description:**
Implement phase transition logic and state persistence.

**Tasks:**
- [ ] Build design→modeling transition
- [ ] Build modeling→monitor transition
- [ ] Implement backtrack logic (modeling→design, monitor→modeling)
- [ ] Create state validation on transitions
- [ ] Implement state persistence across restarts
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- All transitions work correctly
- State validated on transitions
- Data not lost on restart
- Backtracking preserves data

**Transition Validation:**
- Design approved before modeling
- Model exported before printing
- Prevent invalid state transitions

---

### TICKET-025: File & Project Management
**Status:** TODO
**Priority:** P1
**Phase:** Coordinator
**Depends on:** TICKET-024

**Description:**
Implement file organization and project management across phases.

**Tasks:**
- [ ] Create project directory structure manager
- [ ] Build file organization system
- [ ] Implement version control for designs
- [ ] Create backup and recovery system
- [ ] Build file export/import functionality
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Project files properly organized
- Version history maintained
- Backups created automatically
- Export/import working

**Project Structure:**
```
project_name/
├── design/
├── model/
├── print/
└── session.json
```

---

### TICKET-026: User Interface & Command Processing
**Status:** TODO
**Priority:** P2
**Phase:** Coordinator
**Depends on:** TICKET-025

**Description:**
Implement user-facing interface and command handling.

**Tasks:**
- [ ] Create command parser for user input
- [ ] Build status display formatting
- [ ] Implement help and documentation
- [ ] Create error message formatting
- [ ] Build interactive prompt system
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Commands parsed correctly
- Status displays clearly
- Help is informative
- Error messages useful

**Available Commands:**
- `status` - Show current phase and progress
- `next` - Move to next phase
- `back` - Return to previous phase
- `help` - Show available commands
- `new` - Start new project
- `resume` - Resume previous project

---

### TICKET-027: System Integration Testing
**Status:** TODO
**Priority:** P1
**Phase:** Coordinator
**Depends on:** TICKET-026, TICKET-008, TICKET-015, TICKET-022

**Description:**
Test complete end-to-end system from design through print.

**Tasks:**
- [ ] Create complete test workflow scenario
- [ ] Test full design→model→print pipeline
- [ ] Test data flow between agents
- [ ] Test error recovery and handling
- [ ] Test state persistence and recovery
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Complete workflow functions end-to-end
- Data integrity maintained across phases
- Error handling robust
- All test scenarios pass

**Test Scenario:**
Design phone stand → Generate blueprints → Model in OpenSCAD → Export STL → Simulate print in mock OctoPrint

---

## PHASE 5: Polish & Deployment

### TICKET-028: Documentation & Examples
**Status:** TODO
**Priority:** P2
**Phase:** Polish
**Depends on:** TICKET-027

**Description:**
Create comprehensive documentation and usage examples.

**Tasks:**
- [ ] Write API documentation for each agent
- [ ] Create user guide and tutorials
- [ ] Build example projects (3-5 designs)
- [ ] Document configuration options
- [ ] Create troubleshooting guide
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- All public APIs documented
- User guide covers all workflows
- Examples run successfully
- Configuration documented

---

### TICKET-029: Performance Optimization
**Status:** TODO
**Priority:** P3
**Phase:** Polish
**Depends on:** TICKET-027

**Description:**
Profile and optimize system performance.

**Tasks:**
- [ ] Profile image generation speeds
- [ ] Optimize OpenSCAD compilation times
- [ ] Improve OctoPrint polling efficiency
- [ ] Cache frequently accessed data
- [ ] Optimize memory usage
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Image generation < 2 min per set
- Model compilation < 30 sec
- OctoPrint polling < 5% CPU
- Memory usage stable

---

### TICKET-030: Deployment & Packaging
**Status:** TODO
**Priority:** P2
**Phase:** Polish
**Depends on:** TICKET-029

**Description:**
Package system for deployment and distribution.

**Tasks:**
- [ ] Create Docker container
- [ ] Build Python package distribution
- [ ] Write installation guide
- [ ] Create configuration templates
- [ ] Build release artifacts
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- Docker image builds successfully
- Package installable via pip
- Installation documented
- First-time setup easy

---

### TICKET-031: Quality Assurance & Testing
**Status:** TODO
**Priority:** P2
**Phase:** Polish
**Depends on:** TICKET-030

**Description:**
Comprehensive QA and testing before release.

**Tasks:**
- [ ] Run full test suite
- [ ] Execute stress testing
- [ ] Perform security review
- [ ] Test on multiple platforms
- [ ] Collect feedback and iterate
- [ ] Update relevant documentation in `docs/API_REFERENCE.md`

**Acceptance Criteria:**
- All tests passing
- No critical bugs
- Security review passed
- Works on Mac, Linux, Windows

---

## Notes

- Use `/next-ticket` skill to start work on available tickets
- Update ticket status as you progress
- Create new tickets if additional work is discovered
- Reference ticket numbers in commits: `[TICKET-XXX]`

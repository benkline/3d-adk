# 3D-ADK: Google ADK Implementation Specification

## Overview
This specification details how to structure the 3D-ADK system using Google's Agent Development Kit (ADK) framework.

## Agent Architecture

### Agent Hierarchy

```
CoordinatorAgent (LlmAgent)
├── DesignAgent (LlmAgent)
├── ModelingAgent (LlmAgent)
└── MonitorAgent (LlmAgent)
```

### Coordinator Agent (LlmAgent)

The main coordinator is an `LlmAgent` that:
- Routes between three sub-agents based on current phase
- Manages project state and context
- Coordinates phase transitions
- Handles user input and session management

**Key Properties:**
```python
coordinator = LlmAgent(
    name="3D-ADK Coordinator",
    description="Orchestrates 3D printing workflow from design through print",
    model="claude-opus-4-6",  # Use latest Claude
    instruction="""You are the 3D-ADK Coordinator Agent. You manage the 3D printing workflow.

Current phase: {current_phase}
Project: {project_name}

Your role:
1. Route user input to the appropriate sub-agent based on current phase
2. Present clear options and status to the user
3. Manage transitions between Design → Modeling → Monitor phases
4. Maintain project context across all phases

Available commands:
- 'status': Show current progress
- 'next': Move to next phase
- 'back': Return to previous phase
- 'help': Show available commands
""",
    tools=[
        # Design phase tools
        DesignAgentTool(design_agent),
        # Modeling phase tools
        ModelingAgentTool(modeling_agent),
        # Monitor phase tools
        MonitorAgentTool(monitor_agent),
        # Coordinator tools
        ProjectManagementTool(),
        PhaseTransitionTool(),
    ],
    sub_agents=[design_agent, modeling_agent, monitor_agent]
)
```

### Sub-Agents (LlmAgent)

Each sub-agent is an `LlmAgent` focused on its specific domain:

**Design Agent:**
```python
design_agent = LlmAgent(
    name="Design Phase Agent",
    description="Handles conceptual design through blueprint creation",
    model="claude-opus-4-6",
    instruction="""You are the Design Phase Agent for 3D-ADK.

Your workflow:
1. Interview: Conduct structured conversation about design intent
2. Sketches: Generate conceptual sketches from interview
3. Images: Create detailed rendered images
4. Blueprint: Generate technical specifications and blueprints

Maintain design context and allow iterations/regenerations.""",
    tools=[
        InterviewTool(),
        SketchGenerationTool(),
        ImageGenerationTool(),
        BlueprintGenerationTool(),
    ]
)
```

**Modeling Agent:**
```python
modeling_agent = LlmAgent(
    name="Modeling Phase Agent",
    description="Converts designs to OpenSCAD models and exports STLs",
    model="claude-opus-4-6",
    instruction="""You are the Modeling Phase Agent for 3D-ADK.

Your workflow:
1. Input Processing: Validate design specifications
2. Model Generation: Create parametric OpenSCAD models
3. Refinement: Optimize for printability
4. Export: Generate STL/3MF files

Ensure all generated models are print-ready.""",
    tools=[
        OpenSCADGenerationTool(),
        ModelRenderingTool(),
        PrintabilityAnalysisTool(),
        STLExportTool(),
    ]
)
```

**Monitor Agent:**
```python
monitor_agent = LlmAgent(
    name="Print Monitor Agent",
    description="Monitors 3D printing via OctoPrint integration",
    model="claude-opus-4-6",
    instruction="""You are the Print Monitor Agent for 3D-ADK.

Your role:
1. Connect to OctoPrint and monitor print status
2. Detect issues and alert user
3. Provide real-time print metrics
4. Document completion and quality assessment

Respond quickly to detected issues.""",
    tools=[
        OctoPrintConnectionTool(),
        PrintMonitoringTool(),
        IssueDetectionTool(),
        PrintHistoryTool(),
    ]
)
```

## Tool System

### Tool Development Pattern

All tools inherit from `BaseTool` and implement async execution:

```python
from adk.tools import BaseTool

class InterviewTool(BaseTool):
    """Conduct design interview with user"""

    @property
    def name(self) -> str:
        return "conduct_interview"

    @property
    def description(self) -> str:
        return "Conduct structured interview to gather design requirements"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_input": {
                    "type": "string",
                    "description": "User response to interview question"
                },
                "context": {
                    "type": "object",
                    "description": "Interview history and responses"
                }
            },
            "required": ["user_input"]
        }

    async def run_async(self, **kwargs) -> dict:
        """Execute interview interaction"""
        user_input = kwargs.get("user_input", "")
        context = kwargs.get("context", {})

        # Process interview response
        next_question = self._generate_next_question(context, user_input)

        return {
            "next_question": next_question,
            "updated_context": context,
            "interview_complete": self._check_if_complete(context)
        }

    def _generate_next_question(self, context: dict, response: str) -> str:
        """Generate next interview question"""
        # Implementation
        pass

    def _check_if_complete(self, context: dict) -> bool:
        """Check if interview has gathered all needed info"""
        # Implementation
        pass
```

### Agent Tool (Sub-Agent Delegation)

For calling sub-agents from coordinator:

```python
from adk.tools import AgentTool

class DesignAgentTool(BaseTool):
    """Delegate to Design Phase Agent"""

    def __init__(self, design_agent: LlmAgent):
        self.design_agent = design_agent

    @property
    def name(self) -> str:
        return "run_design_agent"

    @property
    def description(self) -> str:
        return "Run the Design Phase Agent for sketches, images, blueprints"

    async def run_async(self, **kwargs) -> dict:
        """Delegate to sub-agent"""
        user_message = kwargs.get("message", "")
        design_context = kwargs.get("context", {})

        # Run sub-agent
        result = await self.design_agent.run_async(
            user_input=user_message,
            context=design_context
        )

        return result
```

### Long-Running Function Tool

For image generation and model rendering that may take time:

```python
from adk.tools import LongRunningFunctionTool

class ImageGenerationTool(LongRunningFunctionTool):
    """Generate images with progress tracking"""

    @property
    def name(self) -> str:
        return "generate_images"

    async def run_async(self, **kwargs) -> dict:
        """Generate images asynchronously"""
        design_brief = kwargs.get("design_brief")
        variations = kwargs.get("variations", 3)

        # Track progress through callback
        async def generate():
            images = []
            for i in range(variations):
                # Simulate or call actual image generation API
                image_path = await self._call_image_api(design_brief, i)
                images.append(image_path)
                # Progress can be tracked via callbacks
            return {"images": images}

        return await generate()

    async def _call_image_api(self, brief: dict, index: int) -> str:
        """Call image generation API"""
        # Implementation
        pass
```

## Services Architecture

### Memory Service

Store conversation history and design context:

```python
from adk.services import BaseMemoryService

class DesignMemoryService(BaseMemoryService):
    """Store design decisions and conversation history"""

    async def add_events_to_memory(self, events: list) -> None:
        """Add conversation events to memory"""
        # Store interview responses, sketch feedback, etc.
        pass

    async def search_memory(self, query: str) -> list:
        """Search previous design decisions and notes"""
        # Find relevant design history
        pass

    async def add_session_to_memory(self, session_id: str) -> None:
        """Add session to indexed memory"""
        # Index new session
        pass
```

### Artifact Service

Store generated files (sketches, images, models):

```python
from adk.services import BaseArtifactService

class ProjectArtifactService(BaseArtifactService):
    """Store and retrieve project artifacts"""

    async def save_artifact(self, artifact_id: str, data: bytes, metadata: dict) -> None:
        """Save design file or image"""
        # Store design_specs.json, sketches/, images/, models/
        project_id = metadata.get("project_id")
        artifact_type = metadata.get("type")  # "sketch", "image", "model", "stl"

        file_path = f"{project_id}/{artifact_type}/{artifact_id}"
        # Save to file system
        pass

    async def load_artifact(self, artifact_id: str, project_id: str) -> bytes:
        """Load previously generated artifact"""
        # Retrieve sketch, image, model, or STL
        pass

    async def delete_artifact(self, artifact_id: str, project_id: str) -> None:
        """Remove artifact"""
        pass
```

### Session Service

Manage project sessions across restarts:

```python
from adk.services import BaseSessionService

class ProjectSessionService(BaseSessionService):
    """Manage project sessions and state"""

    async def create_session(self, session_id: str, metadata: dict) -> None:
        """Create new project session"""
        session_data = {
            "session_id": session_id,
            "project_name": metadata.get("project_name"),
            "created_at": datetime.now(),
            "current_phase": "design",
            "state": metadata
        }
        # Store session
        pass

    async def get_session(self, session_id: str) -> dict:
        """Load project session"""
        # Retrieve session state
        pass

    async def update_session(self, session_id: str, updates: dict) -> None:
        """Update session with new phase/state"""
        pass

    async def list_sessions(self) -> list:
        """List all projects"""
        pass
```

## Execution Flow

### InvocationContext

Access context during execution:

```python
from adk.runtime import InvocationContext

async def run_coordinator(user_input: str, context: InvocationContext):
    """Execute coordinator with context access"""

    # Access services
    memory = context.memory_service
    artifacts = context.artifact_service
    session = context.session_service

    # Access agent state
    current_phase = context.agent_states.get("current_phase", "design")

    # Run appropriate agent based on phase
    if current_phase == "design":
        result = await design_agent.run_async(user_input=user_input, invocation_context=context)
    elif current_phase == "modeling":
        result = await modeling_agent.run_async(user_input=user_input, invocation_context=context)
    elif current_phase == "monitor":
        result = await monitor_agent.run_async(user_input=user_input, invocation_context=context)

    return result
```

### Runner Configuration

Configure execution parameters:

```python
from adk.runtime import Runner, RunConfig

config = RunConfig(
    max_llm_calls=50,  # Prevent infinite loops
    streaming_mode=True,  # Stream results to user
    timeout_seconds=300,  # 5 minute timeout for long operations
    enable_logging=True
)

runner = Runner(
    agent=coordinator,
    memory_service=ProjectMemoryService(),
    artifact_service=ProjectArtifactService(),
    session_service=ProjectSessionService(),
    config=config
)

result = await runner.run(
    user_input="I want to design a phone stand",
    session_id="project_001"
)
```

## Implementation Patterns

### 1. Phase Management via Agent State

Store phase in `context.agent_states`:

```python
# In coordinator
async def transition_to_modeling(context: InvocationContext):
    context.agent_states["current_phase"] = "modeling"
    context.agent_states["design_approved"] = True
    await context.session_service.update_session(
        session_id=context.session_id,
        updates={"current_phase": "modeling"}
    )
```

### 2. Data Passing Between Agents

Use artifact service for files, memory service for context:

```python
# Design agent saves blueprint
blueprint_data = {"specs": {...}}
await context.artifact_service.save_artifact(
    artifact_id="blueprint_final",
    data=json.dumps(blueprint_data),
    metadata={
        "project_id": project_id,
        "type": "blueprint",
        "phase": "design"
    }
)

# Modeling agent loads blueprint
blueprint = await context.artifact_service.load_artifact(
    artifact_id="blueprint_final",
    project_id=project_id
)
```

### 3. Tool Callbacks

Implement callbacks for pre/post processing:

```python
design_agent.before_model_callback = async def before_call(invocation_context):
    # Load design context before LLM call
    design_context = await invocation_context.memory_service.search_memory(
        query="design brief"
    )
    return {"design_context": design_context}

design_agent.after_tool_callback = async def after_call(tool_result, invocation_context):
    # Save tool results to artifacts
    if tool_result.get("type") == "image":
        await invocation_context.artifact_service.save_artifact(...)
```

## Error Handling & Recovery

### Tool Error Handling

```python
async def run_async(self, **kwargs) -> dict:
    try:
        result = await self._execute_operation(**kwargs)
        return result
    except ToolExecutionError as e:
        # Log error and suggest recovery
        return {
            "error": str(e),
            "recovery_suggestion": self._suggest_recovery(e),
            "retry_possible": True
        }
```

### Agent Recovery

```python
# In RunConfig or agent initialization
config = RunConfig(
    max_llm_calls=50,
    enable_error_recovery=True,
    recovery_strategies=[
        "retry_with_simplified_prompt",
        "fallback_to_basic_implementation",
        "request_user_input"
    ]
)
```

## Configuration Management

Store ADK configuration:

```python
# src/config/adk_config.yaml
agents:
  coordinator:
    name: "3D-ADK Coordinator"
    model: "claude-opus-4-6"
    max_llm_calls: 50
  design:
    name: "Design Phase Agent"
    model: "claude-opus-4-6"
    max_llm_calls: 30
  modeling:
    name: "Modeling Phase Agent"
    model: "claude-opus-4-6"
    max_llm_calls: 20
  monitor:
    name: "Print Monitor Agent"
    model: "claude-opus-4-6"
    max_llm_calls: 15

services:
  memory:
    type: "InMemoryMemoryService"
  artifacts:
    type: "FileSystemArtifactService"
    path: "./projects"
  sessions:
    type: "FileSystemSessionService"
    path: "./sessions"
```

## Key ADK Concepts to Use

1. **LlmAgent as base**: All agents inherit from `LlmAgent`
2. **Tool system**: Each capability is a `BaseTool`
3. **InvocationContext**: Central access to all services during execution
4. **Services**: Extensible storage backends (memory, artifacts, sessions)
5. **RunConfig**: Fine-grained execution control
6. **Callbacks**: `before_model_callback`, `after_tool_callback` for customization

## Next Steps

- Create base agent classes that extend ADK's LlmAgent
- Implement required tools for each agent
- Set up service implementations
- Test inter-agent communication via tools
- Verify context and state management across phases

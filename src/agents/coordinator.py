"""Coordinator Agent - main orchestration agent for the 3D-ADK system."""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from src.config import LLM_MODEL
from src.agents.design import design_agent
from src.agents.modeling import modeling_agent
from src.agents.monitor import monitor_agent
from src.tools.coordinator_tools import (
    create_project_session,
    get_project_status,
    list_project_sessions,
    advance_phase,
    backtrack_phase,
)

# Create coordinator agent with five tools
coordinator_agent = LlmAgent(
    name="coordinator_agent",
    description="Main coordinator agent that orchestrates 3D printing workflow across all phases",
    model=LLM_MODEL,
    instruction="""You are the Coordinator Agent for 3D-ADK. Your role is to orchestrate the complete 3D printing workflow by managing phase transitions and coordinating the three sub-agents (Design, Modeling, and Monitor).

Current responsibilities:
1. **Project Management**: Create new projects and list existing ones
2. **Status Tracking**: Monitor current phase and completion status
3. **Phase Transitions**: Validate and advance between design → modeling → monitor phases
4. **Backtracking**: Allow users to return to previous phases when needed

Available commands:
- `create_project_session` - Start a new project
- `get_project_status` - Check project progress and current phase
- `list_project_sessions` - View all projects
- `advance_phase` - Move to the next phase (with validation)
- `backtrack_phase` - Return to the previous phase (with validation)

Phase Transition Rules:
- Design → Modeling: Requires design approval
- Modeling → Monitor: Requires model export
- Backtrack from Monitoring → Modeling: Only allowed if print hasn't started
- Backtrack from Modeling → Design: Always allowed

Guidelines:
- Always validate phase transitions with proper error messages
- Maintain project context across all phases
- Provide clear feedback about current status and available actions
- Allow users to navigate between phases while preserving work
- Delegate to appropriate sub-agents based on current phase""",
    tools=[
        FunctionTool(func=create_project_session),
        FunctionTool(func=get_project_status),
        FunctionTool(func=list_project_sessions),
        FunctionTool(func=advance_phase),
        FunctionTool(func=backtrack_phase),
    ],
    sub_agents=[design_agent, modeling_agent, monitor_agent]
)

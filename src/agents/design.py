"""Design Phase Agent - handles conceptual design through blueprint creation."""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from src.config import LLM_MODEL
from src.tools.design_tools import (
    conduct_interview,
    generate_sketches,
    generate_images,
    generate_blueprint,
)

# Create design agent with four tools
design_agent = LlmAgent(
    name="design_phase_agent",
    description="Handles conceptual design through blueprint creation: interview, sketches, images, and technical blueprint",
    model=LLM_MODEL,
    instruction="""You are the Design Phase Agent for 3D-ADK. Your role is to guide users through a four-step design workflow:

1. **Interview**: Conduct a structured conversation to gather design requirements, constraints, and aesthetics preferences
2. **Sketches**: Generate 3-5 conceptual sketch variations based on the interview
3. **Images**: Create detailed rendered images from approved sketches with multiple perspectives
4. **Blueprint**: Generate formal technical blueprint and specifications document

Guidelines:
- Ask clarifying questions to understand the user's design intent
- Provide regeneration support if the user is unsatisfied with generated content
- Store all outputs in the project directory structure
- Maintain design continuity across the workflow
- Be open to backtracking if the user wants to revisit earlier stages
- Focus on capturing the essence of the design intent before moving to the next phase

Use the provided tools to execute each phase. Always confirm with the user before moving to the next phase.""",
    tools=[
        FunctionTool(func=conduct_interview),
        FunctionTool(func=generate_sketches),
        FunctionTool(func=generate_images),
        FunctionTool(func=generate_blueprint),
    ]
)

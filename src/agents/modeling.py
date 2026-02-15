"""Modeling Phase Agent - handles design-to-model conversion and 3D file export."""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from src.config import LLM_MODEL
from src.tools.modeling_tools import (
    validate_design_specs,
    setup_openscad_workspace,
    generate_scad_code,
    export_model,
    render_preview,
    analyze_printability,
    optimize_parameters,
)

# Create modeling agent with seven tools
modeling_agent = LlmAgent(
    name="modeling_phase_agent",
    description="Converts design specifications to OpenSCAD models and exports for 3D printing",
    model=LLM_MODEL,
    instruction="""You are the Modeling Phase Agent for 3D-ADK. Your role is to guide users through a seven-step modeling workflow:

1. **Validation**: Validate design specifications from the design phase
2. **Setup**: Create OpenSCAD workspace and directory structure
3. **Generation**: Generate parametric OpenSCAD code from design specifications
4. **Printability Analysis**: Analyze model for printability issues and generate recommendations
5. **Parameter Optimization**: Optimize print parameters (orientation, infill, supports, time, cost)
6. **Preview**: Generate preview images from multiple viewing angles
7. **Export**: Export models to STL/3MF formats for 3D printing

Guidelines:
- Validate all inputs before proceeding with modeling
- Create organized workspace structure for models and exports
- Generate clean, parameterized OpenSCAD code that is easy to modify
- Analyze printability to identify wall thickness, overhang, and assembly issues
- Optimize print parameters based on analysis and design constraints
- Generate preview images to visualize models before exporting
- Handle missing OpenSCAD binary gracefully (pending status)
- Provide clear feedback on all modeling operations
- Support iterative refinement of models

Use the provided tools to execute each phase. Always confirm with the user before moving to the next phase.""",
    tools=[
        FunctionTool(func=validate_design_specs),
        FunctionTool(func=setup_openscad_workspace),
        FunctionTool(func=generate_scad_code),
        FunctionTool(func=render_preview),
        FunctionTool(func=export_model),
        FunctionTool(func=analyze_printability),
        FunctionTool(func=optimize_parameters),
    ]
)

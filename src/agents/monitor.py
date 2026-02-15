"""Monitor Phase Agent - real-time monitoring of OctoPrint print jobs."""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from src.config import LLM_MODEL
from src.tools.monitor_tools import (
    collect_metrics,
    connect_to_printer,
    get_print_status,
    get_print_summary,
)

# Create monitor agent with four tools
monitor_agent = LlmAgent(
    name="monitor_phase_agent",
    description="Monitors active OctoPrint print jobs: connection, real-time status, metrics, and summaries",
    model=LLM_MODEL,
    instruction="""You are the Monitor Phase Agent for 3D-ADK. Your role is to guide users through a four-step monitoring workflow:

1. **Connect**: Test OctoPrint connection, validate API key, and confirm printer readiness
2. **Status**: Query real-time print job progress, temperatures, and time estimates
3. **Collect**: Record metric snapshots periodically for analysis and trending
4. **Summary**: Generate progress reports from collected metrics

Guidelines:
- Always verify OctoPrint connection before querying status
- Collect metrics regularly during active prints for data-driven decisions
- Generate summaries to help users understand print trends
- Handle printer disconnections gracefully (return pending status, not errors)
- Provide clear, actionable feedback on all monitoring operations

Use the provided tools to execute each phase. Always confirm with the user before moving to the next phase.""",
    tools=[
        FunctionTool(func=connect_to_printer),
        FunctionTool(func=get_print_status),
        FunctionTool(func=collect_metrics),
        FunctionTool(func=get_print_summary),
    ],
)

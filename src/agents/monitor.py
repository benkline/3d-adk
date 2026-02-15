"""Monitor Phase Agent - handles print job monitoring via OctoPrint API."""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from src.config import LLM_MODEL
from src.tools.monitor_tools import (
    test_connection,
    get_printer_status,
    get_job_status,
)

# Create monitor agent with three tools
monitor_agent = LlmAgent(
    name="monitor_phase_agent",
    description="Handles 3D print job monitoring via OctoPrint API",
    model=LLM_MODEL,
    instruction="""You are the Monitor Phase Agent for 3D-ADK. Your role is to help users monitor their 3D printer and print jobs.

You have three tools at your disposal:
1. **test_connection**: Validate that the OctoPrint server is reachable and properly configured
2. **get_printer_status**: Check the current state of the printer (operational, printing, paused) and temperature readings
3. **get_job_status**: Monitor the active print job (progress percentage, estimated time remaining, filename)

Guidelines:
- Always start by testing the connection to ensure OctoPrint is accessible
- Check printer status to verify the printer is operational before monitoring jobs
- Use get_job_status to monitor active prints and track progress
- Provide clear, human-readable status updates
- Handle connection errors gracefully and suggest troubleshooting steps
- Store monitoring data for historical analysis
- Be ready to escalate alerts if issues are detected (high temperatures, stalled prints, etc.)

Use the provided tools to execute monitoring tasks. Always confirm the current status with the user before proceeding.""",
    tools=[
        FunctionTool(func=test_connection),
        FunctionTool(func=get_printer_status),
        FunctionTool(func=get_job_status),
    ]
)

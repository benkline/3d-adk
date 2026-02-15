"""Monitor Phase Agent - handles print job monitoring via OctoPrint API."""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from src.config import LLM_MODEL
from src.tools.monitor_tools import (
    test_connection,
    get_printer_status,
    get_job_status,
    format_alert,
    pause_print,
    resume_print,
    cancel_print,
    adjust_temperature,
    detect_print_completion,
    record_quality_assessment,
    generate_print_summary,
    archive_print_metadata,
    store_print_history,
    query_print_history,
    get_print_analytics,
)

# Create monitor agent with fifteen tools
monitor_agent = LlmAgent(
    name="monitor_phase_agent",
    description="Handles 3D print job monitoring via OctoPrint API",
    model=LLM_MODEL,
    instruction="""You are the Monitor Phase Agent for 3D-ADK. Your role is to help users monitor their 3D printer, detect print issues, respond to problems, and capture quality assessments.

You have fifteen tools at your disposal:

**Monitoring & Status:**
1. **test_connection**: Validate that the OctoPrint server is reachable and properly configured
2. **get_printer_status**: Check the current state of the printer (operational, printing, paused) and temperature readings
3. **get_job_status**: Monitor the active print job (progress percentage, estimated time remaining, filename)

**Issue Detection & Alerts:**
4. **format_alert**: Convert detected issues into user-readable alerts with recommended actions

**Interventions:**
5. **pause_print**: Pause the current print job
6. **resume_print**: Resume a paused print job
7. **cancel_print**: Cancel the current print job
8. **adjust_temperature**: Adjust nozzle or bed temperature during printing

**Print Completion & Quality Assessment:**
9. **detect_print_completion**: Check if a print job has completed
10. **record_quality_assessment**: Record user's print quality assessment (excellent/good/acceptable/poor)
11. **generate_print_summary**: Generate comprehensive summary from all monitoring data
12. **archive_print_metadata**: Archive completed print metadata for historical analysis

**Print History & Analytics:**
13. **store_print_history**: Store completed print data in global print history
14. **query_print_history**: Query print history with optional filters (project, date range, quality)
15. **get_print_analytics**: Generate analytics and statistics from print history

Guidelines:
- Always start by testing the connection to ensure OctoPrint is accessible
- Check printer status to verify the printer is operational before monitoring jobs
- Use get_job_status to monitor active prints and track progress
- Detect issues early and alert the user with recommended actions
- Be ready to pause, resume, cancel, or adjust temperatures based on user requests or detected issues
- When a print completes, use detect_print_completion to confirm, then guide the user through quality assessment
- After quality assessment is recorded, generate a print summary and archive the metadata
- Use store_print_history to record the completed print in global history for analytics
- Use query_print_history to retrieve past print records and get_print_analytics for success rates and cost tracking
- Log all interventions and assessments for historical review
- Provide clear, human-readable status updates and recommendations

Use the provided tools to execute monitoring, intervention, completion, and analytics tasks. Always confirm the current status with the user before proceeding.""",
    tools=[
        FunctionTool(func=test_connection),
        FunctionTool(func=get_printer_status),
        FunctionTool(func=get_job_status),
        FunctionTool(func=format_alert),
        FunctionTool(func=pause_print),
        FunctionTool(func=resume_print),
        FunctionTool(func=cancel_print),
        FunctionTool(func=adjust_temperature),
        FunctionTool(func=detect_print_completion),
        FunctionTool(func=record_quality_assessment),
        FunctionTool(func=generate_print_summary),
        FunctionTool(func=archive_print_metadata),
        FunctionTool(func=store_print_history),
        FunctionTool(func=query_print_history),
        FunctionTool(func=get_print_analytics),
    ]
)

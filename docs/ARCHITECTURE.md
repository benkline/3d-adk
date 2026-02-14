# System Architecture

3D-ADK uses a multi-agent system where a **Coordinator Agent** orchestrates three specialized sub-agents:

- **Design Agent** - Interview → Sketches → Images → Blueprint
- **Modeling Agent** - OpenSCAD generation → Validation → STL export
- **Monitor Agent** - OctoPrint connection → Real-time monitoring → Quality assessment

Each agent is an `LlmAgent` with specialized tools. Data flows through:
- **Memory Service** - Conversation history and design decisions
- **Artifact Service** - Generated files (sketches, models, STLs)
- **Session Service** - Project state and phase tracking

The system uses Google ADK's tool system, with agents communicating via `AgentTool` delegation and `InvocationContext` for service access.

**For detailed architecture:** See [../specs/ADK_IMPLEMENTATION_SPEC.md](../specs/ADK_IMPLEMENTATION_SPEC.md)

**For agent-specific details:**
- [../specs/COORDINATOR_AGENT_SPEC.md](../specs/COORDINATOR_AGENT_SPEC.md)
- [../specs/DESIGN_AGENT_SPEC.md](../specs/DESIGN_AGENT_SPEC.md)
- [../specs/MODELING_AGENT_SPEC.md](../specs/MODELING_AGENT_SPEC.md)
- [../specs/MONITOR_AGENT_SPEC.md](../specs/MONITOR_AGENT_SPEC.md)

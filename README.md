# 3D-ADK: AI-Powered 3D Printing Workflow Agent

A sophisticated multi-agent system that guides users through the complete 3D printing workflow: from initial design conception through final print execution and monitoring.

## 🎯 Overview

3D-ADK combines Google's Agent Development Kit with specialized AI agents to create a seamless 3D printing experience:

1. **Design Phase Agent** - Transform ideas into technical blueprints
2. **Modeling Phase Agent** - Convert blueprints to OpenSCAD models and STL files
3. **Print Monitor Agent** - Real-time monitoring via OctoPrint integration
4. **Coordinator Agent** - Orchestrates workflow across all phases

## ✨ Features

### Design Phase
- 🎤 Interactive interview-based design gathering
- 🎨 AI-generated conceptual sketches
- 🖼️ High-quality rendered images with iterations
- 📋 Automated technical blueprint generation
- 🔄 Iterative regeneration on feedback

### Modeling Phase
- 📐 Parametric OpenSCAD model generation
- ✅ Printability analysis and validation
- 🎯 Print orientation optimization
- 📦 Multi-format export (STL, 3MF)
- 🧮 Time & weight estimation

### Print Monitor Phase
- 📡 Real-time OctoPrint integration
- ⚠️ Automated issue detection and alerts
- 📊 Live print metrics and progress tracking
- 📝 Print history and quality assessment
- 🔍 Failure analysis and recommendations

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Mac/Linux/Windows with zsh or bash
- Google ADK SDK
- OctoPrint instance (for monitor phase)

### Installation

1. **Clone and setup virtual environment:**
```bash
cd ~/.venvs
python3 -m venv 3d-adk
source 3d-adk/bin/activate
```

2. **Install dependencies:**
```bash
cd ~/Projects/3d-adk
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your API keys and OctoPrint settings
```

4. **Run the system:**
```bash
python src/main.py
```

## 📁 Project Structure

```
3d-adk/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── .env.example                       # Configuration template
├── 3D_ADK_AGENT_PLAN.md              # Overall system plan
├── tickets.md                         # Implementation tickets
├── src/
│   ├── main.py                       # Coordinator agent entry point
│   ├── agents/
│   │   ├── coordinator.py            # Coordinator agent implementation
│   │   ├── design.py                 # Design phase agent
│   │   ├── modeling.py               # Modeling phase agent
│   │   └── monitor.py                # Print monitor agent
│   ├── tools/
│   │   ├── design_tools.py           # Design phase tools
│   │   ├── modeling_tools.py         # Modeling phase tools
│   │   └── monitor_tools.py          # Monitor phase tools
│   ├── services/
│   │   ├── memory.py                 # Memory service implementation
│   │   ├── artifacts.py              # Artifact storage service
│   │   └── sessions.py               # Session management service
│   ├── config.py                     # Configuration management
│   └── utils.py                      # Utility functions
├── specs/
│   ├── COORDINATOR_AGENT_SPEC.md     # Coordinator specification
│   ├── DESIGN_AGENT_SPEC.md          # Design agent specification
│   ├── MODELING_AGENT_SPEC.md        # Modeling agent specification
│   ├── MONITOR_AGENT_SPEC.md         # Monitor agent specification
│   └── ADK_IMPLEMENTATION_SPEC.md    # ADK framework patterns
├── docs/
│   ├── ARCHITECTURE.md               # System architecture overview
│   ├── DEVELOPER_GUIDE.md            # Development setup and guidelines
│   ├── API_REFERENCE.md              # Agent and tool APIs
│   ├── SETUP_GUIDE.md                # Detailed setup instructions
│   ├── WORKFLOW.md                   # User workflow documentation
│   └── TROUBLESHOOTING.md            # Common issues and solutions
└── tests/
    ├── test_agents.py                # Agent tests
    ├── test_tools.py                 # Tool tests
    ├── test_services.py              # Service tests
    └── test_integration.py           # End-to-end tests
```

## 📚 Documentation

- **[System Architecture](docs/ARCHITECTURE.md)** - High-level system design
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Setup and development workflow
- **[API Reference](docs/API_REFERENCE.md)** - Agent and tool APIs
- **[Setup Guide](docs/SETUP_GUIDE.md)** - Detailed installation steps
- **[User Workflow](docs/WORKFLOW.md)** - How to use the system
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and fixes
- **[Specification Docs](specs/)** - Detailed technical specifications

## 🔄 Workflow

### 1. Design Phase
```
User Interview → Generate Sketches → Refine Images → Create Blueprint
```
Users describe their 3D design idea through a natural conversation. The system generates sketches, detailed renders, and technical specifications.

### 2. Modeling Phase
```
Blueprint → OpenSCAD Generation → Validation → STL Export
```
Design specifications are converted into parametric OpenSCAD models, validated for printability, and exported as print-ready files.

### 3. Monitor Phase
```
Start Print → Real-time Monitoring → Issue Detection → Completion
```
Monitors active prints on OctoPrint, detects issues, and provides real-time feedback.

## 🛠️ Development

### Setting Up Development Environment

```bash
# Activate virtual environment
source ~/.venvs/3d-adk/bin/activate

# Install with dev dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run linter
black src/ tests/
flake8 src/ tests/
```

### Running Tickets

Use the `/next-ticket` skill to work through implementation tickets:

```
/next-ticket
```

This will:
1. Show next available ticket
2. Guide you through implementation
3. Run tests
4. Request code review
5. Update documentation

### Project Phases

1. **Phase 0** - Infrastructure & Foundation (2 tickets)
2. **Phase 1** - Design Agent Implementation (6 tickets)
3. **Phase 2** - Modeling Agent Implementation (6 tickets)
4. **Phase 3** - Print Monitor Agent Implementation (7 tickets)
5. **Phase 4** - Coordinator Agent & Integration (5 tickets)
6. **Phase 5** - Polish & Deployment (4 tickets)

See [tickets.md](tickets.md) for complete list.

## 🔐 Configuration

Create `.env` file based on `.env.example`:

```env
# API Keys
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...  # Optional, if using other image APIs

# OctoPrint Configuration
OCTOPRINT_HOST=localhost
OCTOPRINT_PORT=5000
OCTOPRINT_API_KEY=your_api_key

# Image Generation
IMAGE_API_PROVIDER=anthropic  # or openai, stability, etc.

# Model Selection
LLM_MODEL=claude-opus-4-6
```

## 📊 Project Status

Currently in **Phase 0: Infrastructure** setup.

### Completed
- ✅ Project plan and system architecture
- ✅ Comprehensive specifications
- ✅ Implementation tickets
- ✅ Virtual environment

### In Progress
- 🔄 Infrastructure setup (TICKET-001, TICKET-002)

### Coming Soon
- Design Agent (Phase 1)
- Modeling Agent (Phase 2)
- Monitor Agent (Phase 3)
- System Integration (Phase 4)
- Polish & Deployment (Phase 5)

## 🤝 Architecture Highlights

### Multi-Agent System
- **Coordinator Agent** routes user input to specialized sub-agents
- **Sub-agents** handle specific domains (design, modeling, monitoring)
- **Async execution** for responsive user experience
- **Context preservation** across phase transitions

### Service Architecture
- **Memory Service** - Stores conversation history and design decisions
- **Artifact Service** - Persists generated files and models
- **Session Service** - Manages project state across restarts

### Tool System
- **Design Tools** - Interview, sketch, image, and blueprint generation
- **Modeling Tools** - OpenSCAD generation, rendering, export
- **Monitor Tools** - OctoPrint integration, issue detection, quality assessment

## 🔗 Key Technologies

- **Framework**: Google Agent Development Kit (ADK)
- **LLM**: Claude (Anthropic)
- **CAD**: OpenSCAD
- **3D Printer Interface**: OctoPrint API
- **Image Generation**: Claude Vision/DALL-E/Stable Diffusion
- **Storage**: File system (with extensibility for cloud)
- **Testing**: pytest

## 📖 Learning Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [OpenSCAD Documentation](https://openscad.org/documentation.html)
- [OctoPrint API](https://docs.octoprint.org/en/master/api/)
- [Claude API Documentation](https://anthropic.com/docs)

## 🚨 Support

### Common Issues

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues and solutions.

### Getting Help

1. Check the [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
2. Review [API Reference](docs/API_REFERENCE.md)
3. Check test files for usage examples
4. Open an issue with detailed description

## 📝 License

[Add your license here]

## 🙏 Acknowledgments

- Google Agent Development Kit team
- Anthropic for Claude API
- OpenSCAD community
- OctoPrint contributors

---

**Last Updated**: February 14, 2026

For the latest information, see [ARCHITECTURE.md](docs/ARCHITECTURE.md) and [tickets.md](tickets.md).

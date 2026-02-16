# 3D-ADK - AI-Driven Mechanical Design Kit for 3D Printing
# Docker image for containerized deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# - openscad: required for 3D model rendering
# - xvfb: virtual display for headless OpenSCAD rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    openscad \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml requirements.txt .env.example ./
COPY src ./src
COPY docs ./docs
COPY examples ./examples

# Install Python dependencies using the package definition
RUN pip install --no-cache-dir -e .

# Create directories for runtime data
RUN mkdir -p /app/projects /app/sessions

# Set environment variables
ENV OPENSCAD_PATH=/usr/bin/openscad
ENV PROJECTS_DIR=/app/projects
ENV SESSIONS_DIR=/app/sessions
ENV LOG_LEVEL=INFO

# Health check: verify the CLI is available
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD 3d-adk --help > /dev/null 2>&1 || exit 1

# Default entrypoint for interactive CLI
ENTRYPOINT ["3d-adk"]
CMD ["-i"]

# Multi-stage build for A/B Test Validation Agent
# Stage 1: Base image with Python dependencies
FROM python:3.13-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies installation
FROM base as builder

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 3: Production image
FROM base as production

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Make run.sh executable
RUN chmod +x run.sh

# Update PATH to include local binaries
ENV PATH=/root/.local/bin:$PATH

# Set default environment variables (can be overridden at runtime)
# AgentBeats controller will set AGENT_PORT dynamically when it starts the agent
# Default to 10000 for local/AgentBeats use, but controller manages this in production
# CLOUDRUN_HOST and HTTPS_ENABLED are required for AgentBeats on Cloud Run
ENV HOST=0.0.0.0 \
    AGENT_PORT=10000 \
    LOG_LEVEL=INFO \
    API_WORKERS=1 \
    CLOUDRUN_HOST=ab-green-728049235050.us-central1.run.app \
    HTTPS_ENABLED=true

# Expose port 8080 (Cloud Run default) and 10000 (AgentBeats default)
EXPOSE 8080 10000

# Health check (try AGENT_PORT first, fallback to PORT, then default 8080)
# This matches the priority in run.sh: AGENT_PORT > PORT > 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${AGENT_PORT:-${PORT:-8080}}/a2a/health || exit 1

# Run AgentBeats controller (which manages the agent lifecycle)
# The controller will execute run.sh to start the agent
# Use the CLI command (not python -m) provided by earthshaker package
CMD ["agentbeats", "run_ctrl"]

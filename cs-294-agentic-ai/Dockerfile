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
# AgentBeats controller will set HOST and AGENT_PORT
# Cloud platforms (Render, Cloud Run, etc.) will set PORT
# Don't set AGENT_PORT here - let it be set at runtime or fall back to PORT
ENV HOST=0.0.0.0 \
    LOG_LEVEL=INFO \
    API_WORKERS=1

# Expose port 8080 (Cloud Run default) and 10000 (AgentBeats default)
EXPOSE 8080 10000

# Health check (try AGENT_PORT first, fallback to PORT, then default 8080)
# This matches the priority in run.sh: AGENT_PORT > PORT > 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${AGENT_PORT:-${PORT:-8080}}/a2a/health || exit 1

# Run the agent server directly via run.sh
# Cloud Run will set PORT=8080, which run.sh will use
CMD ["./run.sh"]

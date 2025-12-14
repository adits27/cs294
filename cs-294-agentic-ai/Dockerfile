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
ENV HOST=0.0.0.0 \
    AGENT_PORT=10000 \
    LOG_LEVEL=INFO \
    API_WORKERS=1

# Expose port (defaults to 10000, but configurable via AGENT_PORT or PORT)
EXPOSE 10000

# Health check (try AGENT_PORT first, fallback to PORT, then default)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${AGENT_PORT:-${PORT:-10000}}/a2a/health || exit 1

# Run the application using the run.sh script
# Note: AgentBeats controller will use the Procfile
CMD ["./run.sh"]

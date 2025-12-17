#!/bin/bash
set -e  # Exit on error
set -x  # Print commands as they execute

# AgentBeats controller automatically sets $HOST and $AGENT_PORT
# The agent MUST listen on these variables as per AgentBeats requirements
# The controller manages the port mapping and proxying

# Use the HOST and AGENT_PORT environment variables set by the controller
# These are required by AgentBeats - do not override them
LISTEN_HOST=${HOST:-0.0.0.0}
LISTEN_PORT=${AGENT_PORT:-10000}

echo "======================================"
echo "AGENT STARTUP - $(date)"
echo "======================================"
echo "Starting agent on ${LISTEN_HOST}:${LISTEN_PORT}"
echo "Environment variables:"
echo "  HOST=$HOST"
echo "  AGENT_PORT=$AGENT_PORT"
echo "  PORT=$PORT"
echo "  AGENT_URL=$AGENT_URL"
echo "  CLOUDRUN_HOST=$CLOUDRUN_HOST"
echo "  HTTPS_ENABLED=$HTTPS_ENABLED"
echo "Working directory: $(pwd)"
echo "Files in current directory:"
ls -la
echo "======================================"

# Activate virtual environment if it exists (for local development)
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment"
    source venv/bin/activate
fi

# Check if uvicorn is available
echo "Checking for uvicorn..."
if ! command -v uvicorn &> /dev/null; then
    echo "ERROR: uvicorn not found in PATH"
    echo "PATH=$PATH"
    which python || echo "python not found"
    exit 1
fi
echo "uvicorn found at: $(which uvicorn)"

# Check Python version
echo "Python version: $(python --version)"

# Check if api directory exists
echo "Checking api directory..."
if [ ! -d "api" ]; then
    echo "ERROR: api directory not found"
    exit 1
fi
ls -la api/
echo "api directory found"

echo "======================================"
echo "All checks passed, starting uvicorn..."
echo "======================================"

# Start the agent server
# The agent listens on HOST:AGENT_PORT as required by AgentBeats
exec uvicorn api.server:app --host $LISTEN_HOST --port $LISTEN_PORT --log-level info

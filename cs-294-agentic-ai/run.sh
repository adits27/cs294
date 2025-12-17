#!/bin/bash
set -e  # Exit on error

# AgentBeats controller automatically sets $HOST and $AGENT_PORT
# The agent MUST listen on these variables as per AgentBeats requirements
# The controller manages the port mapping and proxying

# Use the HOST and AGENT_PORT environment variables set by the controller
# These are required by AgentBeats - do not override them
LISTEN_HOST=${HOST:-0.0.0.0}
LISTEN_PORT=${AGENT_PORT:-10000}

echo "Starting agent on ${LISTEN_HOST}:${LISTEN_PORT}"
echo "Environment: HOST=$HOST, AGENT_PORT=$AGENT_PORT, PORT=$PORT"
echo "Working directory: $(pwd)"

# Activate virtual environment if it exists (for local development)
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment"
    source venv/bin/activate
fi

# Check if uvicorn is available
if ! command -v uvicorn &> /dev/null; then
    echo "ERROR: uvicorn not found in PATH"
    exit 1
fi

# Check if the api.server module can be imported
python3 -c "import api.server" 2>&1 || {
    echo "ERROR: Failed to import api.server module"
    exit 1
}

echo "Starting uvicorn server..."
# Start the agent server
# The agent listens on HOST:AGENT_PORT as required by AgentBeats
exec uvicorn api.server:app --host $LISTEN_HOST --port $LISTEN_PORT --log-level info

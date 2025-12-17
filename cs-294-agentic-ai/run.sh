#!/bin/bash
# AgentBeats controller automatically sets $HOST and $AGENT_PORT
# The agent MUST listen on these variables as per AgentBeats requirements
# The controller manages the port mapping and proxying

# Use the HOST and AGENT_PORT environment variables set by the controller
# These are required by AgentBeats - do not override them
LISTEN_HOST=${HOST:-0.0.0.0}
LISTEN_PORT=${AGENT_PORT:-10000}

# Activate virtual environment if it exists (for local development)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Start the agent server
# The agent listens on HOST:AGENT_PORT as required by AgentBeats
uvicorn api.server:app --host $LISTEN_HOST --port $LISTEN_PORT

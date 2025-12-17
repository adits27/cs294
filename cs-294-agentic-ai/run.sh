#!/bin/bash
# AgentBeats controller automatically sets $HOST and $AGENT_PORT
# The controller manages the agent lifecycle and proxies requests

# Use environment variables set by AgentBeats controller
# Fallback to defaults only for local development
LISTEN_HOST=${HOST:-0.0.0.0}
LISTEN_PORT=${AGENT_PORT:-8000}

# Activate virtual environment if it exists (for local development)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Start the agent server
# The agent listens on HOST:AGENT_PORT as required by AgentBeats
uvicorn api.server:app --host $LISTEN_HOST --port $LISTEN_PORT

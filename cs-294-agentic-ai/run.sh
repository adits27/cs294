#!/bin/bash
# AgentBeats controller uses $HOST and $AGENT_PORT
# Render and other platforms use $PORT
# Priority: AGENT_PORT (AgentBeats) > PORT (Render/Cloud) > default 8000
LISTEN_PORT=${AGENT_PORT:-${PORT:-8000}}
LISTEN_HOST=${HOST:-0.0.0.0}

# Activate virtual environment if it exists and we're running locally
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

uvicorn api.server:app --host $LISTEN_HOST --port $LISTEN_PORT

"""
FastAPI Application Server for A2A Compliant HTTP API Layer

This server provides REST endpoints for:
- Individual agent invocation
- Full validation workflow execution
- Workflow status and result retrieval
- Agent metadata and capabilities

Usage:
    uvicorn api.server:app --reload --host 0.0.0.0 --port 8000

Environment Variables:
    - API_HOST: Host to bind to (default: 0.0.0.0)
    - API_PORT: Port to bind to (default: 8000)
    - API_WORKERS: Number of worker processes (default: 1)
    - LOG_LEVEL: Logging level (default: INFO)
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime

from api.routes import router
from api.schemas import ErrorResponse

# ============================================================================
# Configuration
# ============================================================================

API_VERSION = "1.0.0"
API_TITLE = "A2A Agent Validation API"
API_DESCRIPTION = """
# A2A Compliant HTTP API for A/B Test Validation

This API provides REST endpoints for validating A/B test experiments using multiple specialized agents.

## Features

- **Agent Invocation**: Invoke individual validation agents
- **Workflow Execution**: Run complete validation workflows
- **Async Processing**: Support for both synchronous and asynchronous execution
- **A2A Compliance**: Full Agent-to-Agent (A2A) message protocol support
- **Comprehensive Results**: Detailed validation scores and breakdowns

## Agent Types

1. **Statistical Validation Agent** (40% weight)
   - Power analysis
   - Significance testing
   - Effect size calculations
   - Multiple testing corrections

2. **Report Validation Agent** (30% weight)
   - Report structure and clarity
   - Completeness checks
   - Visualization quality

3. **Data Validation Agent** (20% weight)
   - Data quality and completeness
   - Missing value analysis
   - Distribution checks
   - Sample adequacy

4. **Code Validation Agent** (10% weight)
   - Code structure and organization
   - Best practices compliance
   - Error handling
   - Documentation quality

## Validation Scoring

- Final score: 0-100 (weighted average)
- Decision threshold: >= 70.0 = "GOOD A/B TEST", < 70.0 = "BAD A/B TEST"
- Weights are automatically normalized if agents are unavailable
"""

# ============================================================================
# Logging Configuration
# ============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Application Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {API_TITLE} v{API_VERSION}")
    logger.info("Loading agent configurations...")

    # Log available agents
    from api.routes import AGENT_REGISTRY
    logger.info(f"Loaded {len(AGENT_REGISTRY)} agents:")
    for agent_id, info in AGENT_REGISTRY.items():
        logger.info(f"  - {agent_id}: {info['name']} (weight: {info['weight']})")

    logger.info("API server ready")

    yield

    # Shutdown
    logger.info("Shutting down API server...")
    logger.info("Cleanup complete")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ============================================================================
# Middleware
# ============================================================================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = datetime.utcnow()

    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds()

    # Log response
    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"Status={response.status_code} Duration={duration:.3f}s"
    )

    return response


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.error(f"Validation error: {exc.errors()}")

    error_details = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append(f"{field}: {error['msg']}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="ValidationError",
            message="Request validation failed",
            detail="; ".join(error_details),
            timestamp=datetime.utcnow().isoformat()
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred",
            detail=str(exc),
            timestamp=datetime.utcnow().isoformat()
        ).model_dump()
    )


# ============================================================================
# Routes
# ============================================================================

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["A2A Validation API"])

# Include A2A protocol routes
from api.a2a_routes import a2a_router
app.include_router(a2a_router, prefix="/a2a", tags=["A2A Protocol"])


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs"""
    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
        "a2a_manifest": "/a2a/manifest",
        "a2a_health": "/a2a/health"
    }


# Info endpoint (AgentBeats compatible)
@app.get("/info", include_in_schema=False)
async def info():
    """Agent info endpoint for AgentBeats controller"""
    return {
        "agent_id": "ab-test-validation-agent",
        "agent_name": "A/B Test Validation Agent",
        "version": API_VERSION,
        "description": "Multi-agent A/B test validation system using A2A protocol",
        "capabilities": ["ab_test_validation"],
        "endpoints": {
            "manifest": "/a2a/manifest",
            "capabilities": "/a2a/capabilities",
            "invoke": "/a2a/invoke",
            "health": "/a2a/health",
            "info": "/a2a/info"
        }
    }


# Agent card endpoint (AgentBeats verification)
@app.get("/.well-known/agent-card.json", include_in_schema=False)
async def agent_card():
    """Agent card for AgentBeats verification"""
    from pathlib import Path
    import json

    card_path = Path(__file__).parent.parent / ".well-known" / "agent-card.json"
    if card_path.exists():
        with open(card_path, 'r') as f:
            return json.load(f)

    # Fallback if file doesn't exist
    return {
        "name": "A/B Test Validation Agent",
        "description": "Multi-agent A/B test validation system using A2A protocol",
        "version": API_VERSION,
        "agent_id": "ab-test-validation-agent",
        "capabilities": [
            {
                "id": "ab_test_validation",
                "name": "A/B Test Validation",
                "description": "Complete validation of A/B test experiments including data, code, reports, and statistical analysis"
            }
        ],
        "endpoints": {
            "info": "/info",
            "manifest": "/a2a/manifest",
            "capabilities": "/a2a/capabilities",
            "invoke": "/a2a/invoke",
            "health": "/a2a/health"
        }
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    workers = int(os.getenv("API_WORKERS", "1"))

    logger.info(f"Starting server on {host}:{port} with {workers} workers")

    uvicorn.run(
        "api.server:app",
        host=host,
        port=port,
        workers=workers,
        reload=True,  # Enable auto-reload for development
        log_level=LOG_LEVEL.lower()
    )

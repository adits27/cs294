"""
A2A Protocol Compliant REST API Routes

These endpoints follow the Agent-to-Agent (A2A) protocol specification
for standardized agent communication and invocation.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import asyncio
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import logging

from api.schemas import (
    WorkflowValidateRequest,
    ValidationDecision,
    WorkflowStatus,
    ValidationBreakdown,
)

from agents import (
    ABTestContext,
    create_initial_state,
    run_validation_workflow,
    A2AMessage,
    MessageType,
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
a2a_router = APIRouter()

# Session storage for A2A protocol (in production, use Redis/DB)
session_storage: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# A2A Protocol Schemas
# ============================================================================

class A2AInvokeRequest(BaseModel):
    """A2A standard invoke request"""
    session_id: Optional[str] = Field(None, description="Session ID for tracking (auto-generated if not provided)")
    capability: str = Field(..., description="Capability to invoke (e.g., 'ab_test_validation')")
    input: Dict[str, Any] = Field(..., description="Input data for the capability")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    async_execution: bool = Field(default=False, description="Whether to execute asynchronously")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "capability": "ab_test_validation",
                "input": {
                    "hypothesis": "New feature increases conversion by 5%",
                    "success_metrics": ["conversion_rate"],
                    "dataset_path": "/data/experiment.csv",
                    "expected_effect_size": 0.05,
                    "significance_level": 0.05,
                    "power": 0.80
                },
                "async_execution": False
            }
        }


class A2AInvokeResponse(BaseModel):
    """A2A standard invoke response"""
    session_id: str = Field(..., description="Session ID for this invocation")
    status: str = Field(..., description="Execution status")
    result: Optional[Dict[str, Any]] = Field(None, description="Result data (if completed)")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    timestamp: str = Field(..., description="Response timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class A2ACapability(BaseModel):
    """A2A capability definition"""
    id: str
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class A2ACapabilitiesResponse(BaseModel):
    """A2A capabilities list response"""
    agent_id: str
    agent_name: str
    version: str
    capabilities: list[A2ACapability]


class A2AHealthResponse(BaseModel):
    """A2A health check response"""
    status: str
    agent_id: str
    version: str
    uptime_seconds: Optional[float] = None
    timestamp: str


# ============================================================================
# Helper Functions
# ============================================================================

def extract_validation_breakdown(validation_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract score breakdown from validation results"""
    synthesis = validation_results.get("synthesis", {})
    breakdown_data = synthesis.get("breakdown", {})

    if not breakdown_data:
        return None

    return {
        "statistical_validation": breakdown_data.get("statistical_validation"),
        "report_quality": breakdown_data.get("report_quality"),
        "data_quality": breakdown_data.get("data_quality"),
        "code_quality": breakdown_data.get("code_quality"),
    }


def determine_decision(final_score: float) -> str:
    """Determine validation decision based on score"""
    if final_score >= 70.0:
        return "GOOD A/B TEST"
    elif final_score < 70.0:
        return "BAD A/B TEST"
    else:
        return "UNKNOWN"


async def run_validation_async(session_id: str, ab_test_context: ABTestContext, task_description: str):
    """Run validation workflow asynchronously"""
    try:
        # Update session status
        session_storage[session_id]["status"] = "running"
        session_storage[session_id]["progress"] = "Executing validation workflow"

        # Create initial state
        initial_state = create_initial_state(
            task=task_description,
            ab_test_context=ab_test_context
        )

        # Run workflow in thread pool (LangGraph is synchronous)
        loop = asyncio.get_event_loop()
        final_state = await loop.run_in_executor(None, run_validation_workflow, initial_state)

        # Extract results
        final_score = final_state["final_score"]
        validation_summary = final_state["validation_summary"]
        validation_results = final_state["validation_results"]

        # Build result
        result = {
            "final_score": final_score,
            "decision": determine_decision(final_score),
            "validation_summary": validation_summary,
            "breakdown": extract_validation_breakdown(validation_results),
            "validation_results": validation_results,
        }

        # Update session
        session_storage[session_id]["status"] = "completed"
        session_storage[session_id]["result"] = result
        session_storage[session_id]["completed_at"] = datetime.utcnow().isoformat()
        session_storage[session_id]["progress"] = "Workflow completed successfully"

    except Exception as e:
        logger.error(f"Session {session_id} failed: {str(e)}")
        session_storage[session_id]["status"] = "failed"
        session_storage[session_id]["error"] = str(e)
        session_storage[session_id]["completed_at"] = datetime.utcnow().isoformat()


# ============================================================================
# A2A Protocol Endpoints
# ============================================================================

@a2a_router.get(
    "/manifest",
    summary="Get A2A Manifest",
    description="Returns the A2A manifest describing agent capabilities and endpoints"
)
async def get_manifest():
    """Return A2A manifest"""
    manifest_path = Path(__file__).parent.parent / "a2a-manifest.json"

    if not manifest_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A2A manifest file not found"
        )

    return FileResponse(
        path=str(manifest_path),
        media_type="application/json",
        filename="a2a-manifest.json"
    )


@a2a_router.get(
    "/capabilities",
    response_model=A2ACapabilitiesResponse,
    summary="List Agent Capabilities",
    description="Returns list of all capabilities this agent supports"
)
async def get_capabilities():
    """List all A2A capabilities"""

    capabilities = [
        A2ACapability(
            id="ab_test_validation",
            name="A/B Test Validation",
            description="Complete validation of A/B test experiments including data, code, reports, and statistical analysis",
            input_schema={
                "type": "object",
                "required": ["hypothesis", "success_metrics", "dataset_path", "expected_effect_size"],
                "properties": {
                    "hypothesis": {"type": "string"},
                    "success_metrics": {"type": "array", "items": {"type": "string"}},
                    "dataset_path": {"type": "string"},
                    "code_path": {"type": "string"},
                    "report_path": {"type": "string"},
                    "expected_effect_size": {"type": "number"},
                    "significance_level": {"type": "number", "default": 0.05},
                    "power": {"type": "number", "default": 0.80}
                }
            },
            output_schema={
                "type": "object",
                "required": ["final_score", "decision", "validation_summary"],
                "properties": {
                    "final_score": {"type": "number"},
                    "decision": {"type": "string", "enum": ["GOOD A/B TEST", "BAD A/B TEST", "UNKNOWN"]},
                    "validation_summary": {"type": "string"},
                    "breakdown": {"type": "object"},
                    "validation_results": {"type": "object"}
                }
            },
            metadata={
                "weights": {
                    "statistical_validation": 0.40,
                    "report_quality": 0.30,
                    "data_quality": 0.20,
                    "code_quality": 0.10
                }
            }
        )
    ]

    return A2ACapabilitiesResponse(
        agent_id="ab-test-validation-agent",
        agent_name="A/B Test Validation Agent",
        version="1.0.0",
        capabilities=capabilities
    )


@a2a_router.post(
    "/invoke",
    response_model=A2AInvokeResponse,
    summary="Invoke Agent Capability",
    description="Invoke a specific agent capability via A2A protocol",
    responses={400: {"description": "Invalid capability or input"}, 500: {"description": "Execution failed"}}
)
async def invoke_capability(request: A2AInvokeRequest, background_tasks: BackgroundTasks):
    """
    Invoke agent capability following A2A protocol.
    Supports both synchronous and asynchronous execution.
    """
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())

    # Validate capability
    if request.capability != "ab_test_validation":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported capability: {request.capability}. Supported: ['ab_test_validation']"
        )

    try:
        # Validate input schema
        required_fields = ["hypothesis", "success_metrics", "dataset_path", "expected_effect_size"]
        missing_fields = [field for field in required_fields if field not in request.input]

        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required input fields: {missing_fields}"
            )

        # Create ABTestContext from input
        ab_test_context = ABTestContext(
            hypothesis=request.input["hypothesis"],
            success_metrics=request.input["success_metrics"],
            dataset_path=request.input["dataset_path"],
            code_path=request.input.get("code_path", ""),
            report_path=request.input.get("report_path", ""),
            expected_effect_size=request.input["expected_effect_size"],
            significance_level=request.input.get("significance_level", 0.05),
            power=request.input.get("power", 0.80),
        )

        task_description = request.context.get("task_description", "Validate A/B test experiment")

        # Handle async execution
        if request.async_execution:
            # Store session metadata
            session_storage[session_id] = {
                "session_id": session_id,
                "capability": request.capability,
                "status": "pending",
                "started_at": datetime.utcnow().isoformat(),
                "completed_at": None,
                "progress": "Session queued",
                "result": None,
                "error": None,
            }

            # Add to background tasks
            background_tasks.add_task(
                run_validation_async,
                session_id,
                ab_test_context,
                task_description
            )

            return A2AInvokeResponse(
                session_id=session_id,
                status="pending",
                result=None,
                error=None,
                timestamp=datetime.utcnow().isoformat(),
                metadata={
                    "message": "Execution started asynchronously",
                    "status_url": f"/a2a/status/{session_id}",
                    "result_url": f"/a2a/result/{session_id}"
                }
            )

        # Handle synchronous execution
        else:
            start_time = datetime.utcnow()

            # Create initial state
            initial_state = create_initial_state(
                task=task_description,
                ab_test_context=ab_test_context
            )

            # Run workflow
            loop = asyncio.get_event_loop()
            final_state = await loop.run_in_executor(None, run_validation_workflow, initial_state)

            # Extract results
            final_score = final_state["final_score"]
            validation_summary = final_state["validation_summary"]
            validation_results = final_state["validation_results"]

            # Build result
            result = {
                "final_score": final_score,
                "decision": determine_decision(final_score),
                "validation_summary": validation_summary,
                "breakdown": extract_validation_breakdown(validation_results),
                "validation_results": validation_results,
            }

            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return A2AInvokeResponse(
                session_id=session_id,
                status="completed",
                result=result,
                error=None,
                timestamp=datetime.utcnow().isoformat(),
                metadata={
                    "execution_time_seconds": execution_time
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invoke failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {str(e)}"
        )


@a2a_router.get(
    "/status/{session_id}",
    response_model=A2AInvokeResponse,
    summary="Check Session Status",
    description="Check the execution status of an async session",
    responses={404: {"description": "Session not found"}}
)
async def get_session_status(session_id: str):
    """Get status of async session execution"""
    if session_id not in session_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found"
        )

    session = session_storage[session_id]

    return A2AInvokeResponse(
        session_id=session_id,
        status=session["status"],
        result=session.get("result"),
        error=session.get("error"),
        timestamp=session.get("completed_at") or datetime.utcnow().isoformat(),
        metadata={
            "started_at": session["started_at"],
            "progress": session.get("progress")
        }
    )


@a2a_router.get(
    "/result/{session_id}",
    response_model=A2AInvokeResponse,
    summary="Get Session Result",
    description="Retrieve the result of a completed session",
    responses={404: {"description": "Session not found"}, 425: {"description": "Session not completed"}}
)
async def get_session_result(session_id: str):
    """Get result of completed session"""
    if session_id not in session_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found"
        )

    session = session_storage[session_id]

    # Check if session is completed
    if session["status"] in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail=f"Session is still {session['status']}. Check /a2a/status/{session_id} for progress."
        )

    return A2AInvokeResponse(
        session_id=session_id,
        status=session["status"],
        result=session.get("result"),
        error=session.get("error"),
        timestamp=session.get("completed_at") or datetime.utcnow().isoformat(),
        metadata={
            "started_at": session["started_at"]
        }
    )


@a2a_router.get(
    "/info",
    summary="Get Agent Info",
    description="Get basic agent information (AgentBeats compatible endpoint)"
)
async def get_agent_info():
    """Return basic agent information for AgentBeats controller"""
    return {
        "agent_id": "ab-test-validation-agent",
        "agent_name": "A/B Test Validation Agent",
        "version": "1.0.0",
        "description": "Multi-agent A/B test validation system using A2A protocol",
        "capabilities": ["ab_test_validation"],
        "endpoints": {
            "manifest": "/a2a/manifest",
            "capabilities": "/a2a/capabilities",
            "invoke": "/a2a/invoke",
            "health": "/a2a/health"
        }
    }


@a2a_router.get(
    "/health",
    response_model=A2AHealthResponse,
    summary="A2A Health Check",
    description="Check agent health and availability"
)
async def a2a_health_check():
    """A2A protocol health check"""
    return A2AHealthResponse(
        status="healthy",
        agent_id="ab-test-validation-agent",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )

"""
REST API Routes for A2A Compliant HTTP API Layer
"""
from typing import Dict, Any
from datetime import datetime
import uuid
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
import logging

from api.schemas import (
    # Agent schemas
    AgentMetadata,
    AgentListResponse,
    AgentInvokeRequest,
    AgentInvokeResponse,
    # Workflow schemas
    WorkflowValidateRequest,
    WorkflowValidateResponse,
    WorkflowStatusResponse,
    WorkflowResultsResponse,
    ValidationBreakdown,
    ValidationDecision,
    WorkflowStatus,
    A2AMessageLog,
    # Error schema
    ErrorResponse,
    # Health check
    HealthCheckResponse,
)

# Import agents and workflow
from agents import (
    ABTestContext,
    create_initial_state,
    run_validation_workflow,
    DataValidationAgent,
    CodeValidationAgent,
    ReportValidationAgent,
    StatisticalValidationAgent,
    OrchestratingAgent,
    A2AMessage,
    MessageType,
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# ============================================================================
# Agent Registry
# ============================================================================

# Define available agents with metadata
AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "data_val_agent": {
        "name": "Data Validation Agent",
        "description": "Validates data quality, completeness, missing values, distributions, and sample adequacy",
        "weight": 0.20,
        "validation_type": "data_quality",
        "class": DataValidationAgent,
    },
    "code_val_agent": {
        "name": "Code Validation Agent",
        "description": "Validates code structure, best practices, error handling, and documentation",
        "weight": 0.10,
        "validation_type": "code_quality",
        "class": CodeValidationAgent,
    },
    "report_val_agent": {
        "name": "Report Validation Agent",
        "description": "Validates report structure, clarity, completeness, and visualizations",
        "weight": 0.30,
        "validation_type": "report_quality",
        "class": ReportValidationAgent,
    },
    "stats_val_agent": {
        "name": "Statistical Validation Agent",
        "description": "Validates power analysis, significance tests, effect sizes, and multiple testing corrections",
        "weight": 0.40,
        "validation_type": "statistical_validation",
        "class": StatisticalValidationAgent,
    },
}

# Scoring weights (from OrchestratingAgent)
SCORING_WEIGHTS = {
    "statistical_validation": 0.40,
    "report_quality": 0.30,
    "data_quality": 0.20,
    "code_quality": 0.10,
}

# In-memory storage for async workflow execution
# In production, use Redis, database, or message queue
workflow_storage: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Helper Functions
# ============================================================================

def a2a_message_to_dict(message: A2AMessage) -> Dict[str, Any]:
    """Convert A2AMessage to dictionary"""
    return message.to_dict()


def extract_validation_breakdown(validation_results: Dict[str, Any]) -> ValidationBreakdown:
    """Extract score breakdown from validation results"""
    synthesis = validation_results.get("synthesis", {})
    breakdown_data = synthesis.get("breakdown", {})

    return ValidationBreakdown(
        statistical_validation=breakdown_data.get("statistical_validation"),
        report_quality=breakdown_data.get("report_quality"),
        data_quality=breakdown_data.get("data_quality"),
        code_quality=breakdown_data.get("code_quality"),
    )


def determine_decision(final_score: float) -> ValidationDecision:
    """Determine validation decision based on score"""
    if final_score >= 70.0:
        return ValidationDecision.GOOD_AB_TEST
    elif final_score < 70.0:
        return ValidationDecision.BAD_AB_TEST
    else:
        return ValidationDecision.UNKNOWN


async def run_workflow_async(workflow_id: str, initial_state: Dict[str, Any]):
    """Run validation workflow in background"""
    try:
        # Update status to running
        workflow_storage[workflow_id]["status"] = WorkflowStatus.RUNNING
        workflow_storage[workflow_id]["progress"] = "Executing validation workflow"

        # Run workflow in thread pool (LangGraph is synchronous)
        loop = asyncio.get_event_loop()
        final_state = await loop.run_in_executor(None, run_validation_workflow, initial_state)

        # Store results
        workflow_storage[workflow_id]["status"] = WorkflowStatus.COMPLETED
        workflow_storage[workflow_id]["final_state"] = final_state
        workflow_storage[workflow_id]["completed_at"] = datetime.utcnow().isoformat()
        workflow_storage[workflow_id]["progress"] = "Workflow completed successfully"

    except Exception as e:
        logger.error(f"Workflow {workflow_id} failed: {str(e)}")
        workflow_storage[workflow_id]["status"] = WorkflowStatus.FAILED
        workflow_storage[workflow_id]["error"] = str(e)
        workflow_storage[workflow_id]["completed_at"] = datetime.utcnow().isoformat()


# ============================================================================
# Health Check Endpoint
# ============================================================================

@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Check API service health and availability"
)
async def health_check():
    """Health check endpoint"""
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        agents_available=len(AGENT_REGISTRY),
        timestamp=datetime.utcnow().isoformat()
    )


# ============================================================================
# Agent Endpoints
# ============================================================================

@router.get(
    "/agents",
    response_model=AgentListResponse,
    summary="List Available Agents",
    description="Get list of all available agents and their capabilities"
)
async def list_agents():
    """List all available agents"""
    agents = [
        AgentMetadata(
            agent_id=agent_id,
            name=info["name"],
            description=info["description"],
            weight=info["weight"],
            validation_type=info["validation_type"]
        )
        for agent_id, info in AGENT_REGISTRY.items()
    ]

    return AgentListResponse(
        agents=agents,
        total_count=len(agents),
        scoring_weights=SCORING_WEIGHTS
    )


@router.get(
    "/agents/{agent_id}",
    response_model=AgentMetadata,
    summary="Get Agent Metadata",
    description="Get detailed metadata for a specific agent",
    responses={404: {"model": ErrorResponse}}
)
async def get_agent_metadata(agent_id: str):
    """Get metadata for a specific agent"""
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )

    info = AGENT_REGISTRY[agent_id]
    return AgentMetadata(
        agent_id=agent_id,
        name=info["name"],
        description=info["description"],
        weight=info["weight"],
        validation_type=info["validation_type"]
    )


@router.post(
    "/agents/{agent_id}/invoke",
    response_model=AgentInvokeResponse,
    summary="Invoke Individual Agent",
    description="Invoke a specific agent with custom request data",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def invoke_agent(agent_id: str, request: AgentInvokeRequest):
    """Invoke a specific agent directly"""
    # Check if agent exists
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )

    try:
        # Get agent class and instantiate
        agent_class = AGENT_REGISTRY[agent_id]["class"]
        agent = agent_class(agent_id=agent_id)

        # Create A2A request message
        request_message = A2AMessage(
            sender="api_client",
            receiver=agent_id,
            message_type=MessageType.REQUEST,
            task=request.task,
            data=request.data
        )

        # Process request
        response_message = agent.process_request(request_message)

        # Return response
        return AgentInvokeResponse(
            agent_id=agent_id,
            message_id=response_message.message_id,
            status=response_message.status.value,
            result=response_message.result,
            timestamp=response_message.timestamp,
            error=response_message.result.get("error") if response_message.status.value == "FAILED" else None
        )

    except Exception as e:
        logger.error(f"Agent invocation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent invocation failed: {str(e)}"
        )


# ============================================================================
# Workflow Validation Endpoints
# ============================================================================

@router.post(
    "/workflows/validate",
    response_model=WorkflowValidateResponse,
    summary="Run Full Validation Workflow",
    description="Execute the complete A/B test validation workflow synchronously",
    responses={500: {"model": ErrorResponse}}
)
async def validate_workflow(request: WorkflowValidateRequest):
    """
    Run full validation workflow synchronously.
    This executes all validation agents in parallel and returns the aggregated results.
    """
    workflow_id = str(uuid.uuid4())
    start_time = datetime.utcnow()

    try:
        # Convert request to ABTestContext
        ab_test_context = ABTestContext(
            # New field names
            data_source=request.ab_test_context.data_source,
            code_source=request.ab_test_context.code_source,
            report_source=request.ab_test_context.report_source,
            # Legacy field names (backward compatibility)
            dataset_path=request.ab_test_context.dataset_path,
            code_path=request.ab_test_context.code_path,
            report_path=request.ab_test_context.report_path,
            # Optional parameters
            hypothesis=request.ab_test_context.hypothesis,
            success_metrics=request.ab_test_context.success_metrics,
            expected_effect_size=request.ab_test_context.expected_effect_size,
            significance_level=request.ab_test_context.significance_level,
            power=request.ab_test_context.power,
        )

        # Create initial state
        initial_state = create_initial_state(
            task=request.task_description,
            ab_test_context=ab_test_context
        )

        # Run workflow in thread pool (since it's synchronous)
        loop = asyncio.get_event_loop()
        final_state = await loop.run_in_executor(None, run_validation_workflow, initial_state)

        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()

        # Extract results
        final_score = final_state["final_score"]
        validation_summary = final_state["validation_summary"]
        validation_results = final_state["validation_results"]
        a2a_message_log = final_state["a2a_message_log"]

        # Convert A2A messages to dict
        message_log = [
            A2AMessageLog(**a2a_message_to_dict(msg))
            for msg in a2a_message_log
        ]

        # Extract breakdown
        breakdown = extract_validation_breakdown(validation_results)

        # Determine decision
        decision = determine_decision(final_score)

        return WorkflowValidateResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus.COMPLETED,
            final_score=final_score,
            decision=decision,
            validation_summary=validation_summary,
            breakdown=breakdown,
            validation_results=validation_results,
            a2a_message_log=message_log,
            timestamp=end_time.isoformat(),
            execution_time_seconds=execution_time
        )

    except Exception as e:
        logger.error(f"Workflow validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow validation failed: {str(e)}"
        )


@router.post(
    "/workflows/validate-async",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start Async Validation Workflow",
    description="Start validation workflow asynchronously and return workflow ID for status tracking"
)
async def validate_workflow_async(request: WorkflowValidateRequest, background_tasks: BackgroundTasks):
    """
    Start validation workflow asynchronously.
    Returns workflow_id immediately for status polling.
    """
    workflow_id = str(uuid.uuid4())

    try:
        # Convert request to ABTestContext
        ab_test_context = ABTestContext(
            # New field names
            data_source=request.ab_test_context.data_source,
            code_source=request.ab_test_context.code_source,
            report_source=request.ab_test_context.report_source,
            # Legacy field names (backward compatibility)
            dataset_path=request.ab_test_context.dataset_path,
            code_path=request.ab_test_context.code_path,
            report_path=request.ab_test_context.report_path,
            # Optional parameters
            hypothesis=request.ab_test_context.hypothesis,
            success_metrics=request.ab_test_context.success_metrics,
            expected_effect_size=request.ab_test_context.expected_effect_size,
            significance_level=request.ab_test_context.significance_level,
            power=request.ab_test_context.power,
        )

        # Create initial state
        initial_state = create_initial_state(
            task=request.task_description,
            ab_test_context=ab_test_context
        )

        # Store workflow metadata
        workflow_storage[workflow_id] = {
            "workflow_id": workflow_id,
            "status": WorkflowStatus.PENDING,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "progress": "Workflow queued",
            "initial_state": initial_state,
            "final_state": None,
            "error": None,
        }

        # Add workflow to background tasks
        background_tasks.add_task(run_workflow_async, workflow_id, initial_state)

        return {
            "workflow_id": workflow_id,
            "status": WorkflowStatus.PENDING,
            "message": "Workflow started successfully",
            "status_url": f"/workflows/{workflow_id}/status",
            "results_url": f"/workflows/{workflow_id}/results"
        }

    except Exception as e:
        logger.error(f"Failed to start async workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(e)}"
        )


@router.get(
    "/workflows/{workflow_id}/status",
    response_model=WorkflowStatusResponse,
    summary="Check Workflow Execution Status",
    description="Get the current status of an async workflow execution",
    responses={404: {"model": ErrorResponse}}
)
async def get_workflow_status(workflow_id: str):
    """Get status of async workflow execution"""
    if workflow_id not in workflow_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found"
        )

    workflow = workflow_storage[workflow_id]

    return WorkflowStatusResponse(
        workflow_id=workflow_id,
        status=workflow["status"],
        started_at=workflow["started_at"],
        completed_at=workflow.get("completed_at"),
        progress=workflow.get("progress"),
        error=workflow.get("error")
    )


@router.get(
    "/workflows/{workflow_id}/results",
    response_model=WorkflowResultsResponse,
    summary="Retrieve Workflow Results",
    description="Get the complete results of a workflow execution",
    responses={404: {"model": ErrorResponse}, 425: {"model": ErrorResponse}}
)
async def get_workflow_results(workflow_id: str):
    """Get results of workflow execution"""
    if workflow_id not in workflow_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found"
        )

    workflow = workflow_storage[workflow_id]

    # Check if workflow is still running
    if workflow["status"] in [WorkflowStatus.PENDING, WorkflowStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail=f"Workflow is still {workflow['status'].value}. Check /workflows/{workflow_id}/status for progress."
        )

    # Check if workflow failed
    if workflow["status"] == WorkflowStatus.FAILED:
        return WorkflowResultsResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus.FAILED,
            timestamp=workflow.get("completed_at", datetime.utcnow().isoformat())
        )

    # Extract results from final state
    final_state = workflow.get("final_state")
    if not final_state:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow completed but no results available"
        )

    # Convert A2A messages
    message_log = [
        A2AMessageLog(**a2a_message_to_dict(msg))
        for msg in final_state["a2a_message_log"]
    ]

    # Extract breakdown
    breakdown = extract_validation_breakdown(final_state["validation_results"])

    # Determine decision
    decision = determine_decision(final_state["final_score"])

    return WorkflowResultsResponse(
        workflow_id=workflow_id,
        status=WorkflowStatus.COMPLETED,
        final_score=final_state["final_score"],
        decision=decision,
        validation_summary=final_state["validation_summary"],
        breakdown=breakdown,
        validation_results=final_state["validation_results"],
        a2a_message_log=message_log,
        timestamp=workflow.get("completed_at", datetime.utcnow().isoformat())
    )

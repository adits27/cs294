"""
API Request/Response Schemas for A2A Compliant HTTP API Layer
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class WorkflowStatus(str, Enum):
    """Status of workflow execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ValidationDecision(str, Enum):
    """Final validation decision"""
    GOOD_AB_TEST = "GOOD A/B TEST"
    BAD_AB_TEST = "BAD A/B TEST"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# Agent Schemas
# ============================================================================

class AgentMetadata(BaseModel):
    """Metadata for an individual agent"""
    agent_id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Human-readable agent name")
    description: str = Field(..., description="Agent purpose and capabilities")
    weight: float = Field(..., description="Scoring weight in validation (0-1)")
    validation_type: str = Field(..., description="Type of validation performed")


class AgentListResponse(BaseModel):
    """Response for listing all available agents"""
    agents: List[AgentMetadata] = Field(..., description="List of available agents")
    total_count: int = Field(..., description="Total number of agents")
    scoring_weights: Dict[str, float] = Field(..., description="Normalized scoring weights")


# ============================================================================
# Invocation Schemas
# ============================================================================

class AgentInvokeRequest(BaseModel):
    """Request to invoke a single agent"""
    task: str = Field(..., description="Task description for the agent")
    data: Dict[str, Any] = Field(..., description="Input data for the agent")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class AgentInvokeResponse(BaseModel):
    """Response from agent invocation"""
    agent_id: str = Field(..., description="Agent that processed the request")
    message_id: str = Field(..., description="Unique message identifier")
    status: str = Field(..., description="Message status (COMPLETED/FAILED)")
    result: Dict[str, Any] = Field(..., description="Agent result data")
    timestamp: str = Field(..., description="Response timestamp (ISO format)")
    error: Optional[str] = Field(None, description="Error message if failed")


# ============================================================================
# Workflow Validation Schemas
# ============================================================================

class ABTestContextRequest(BaseModel):
    """
    Request schema for A/B test validation (matches ABTestContext from agents)

    Supports folder patterns for easy batch processing:
    - Single file: "path/to/file.csv"
    - Folder pattern: "results/result_1_1/*" (auto-discovers data_source/, code/, report/ subdirs)
    - Specific folder: "results/result_1_1/data_source/*" (all files in folder)

    All parameters except data_source are optional and will be inferred from files.
    """
    # New field names (recommended)
    data_source: str = Field(..., description="Path/pattern to data files (REQUIRED). Supports folder/* patterns")
    code_source: str = Field("", description="Path/pattern to code files (optional). Supports folder/* patterns")
    report_source: str = Field("", description="Path/pattern to report files (optional). Supports folder/* patterns")

    # Legacy field names for backward compatibility (deprecated)
    dataset_path: str = Field("", description="[DEPRECATED] Use data_source instead")
    code_path: str = Field("", description="[DEPRECATED] Use code_source instead")
    report_path: str = Field("", description="[DEPRECATED] Use report_source instead")

    # Optional parameters (inferred if not provided)
    hypothesis: str = Field("", description="A/B test hypothesis (inferred from files if not provided)")
    success_metrics: List[str] = Field(default_factory=list, description="List of success metrics (inferred if not provided)")
    expected_effect_size: float = Field(0.05, description="Minimum detectable effect (inferred if not provided, default: 0.05)")
    significance_level: float = Field(0.05, description="Alpha level for statistical tests (default: 0.05)")
    power: float = Field(0.80, description="Statistical power (default: 0.80)")

    class Config:
        json_schema_extra = {
            "example": {
                "data_source": "results/result_1_1/*"
            }
        }


class ValidationBreakdown(BaseModel):
    """Breakdown of validation scores by category"""
    statistical_validation: Optional[float] = Field(None, description="Statistical analysis score (0-100)")
    report_quality: Optional[float] = Field(None, description="Report quality score (0-100)")
    data_quality: Optional[float] = Field(None, description="Data quality score (0-100)")
    code_quality: Optional[float] = Field(None, description="Code quality score (0-100)")


class A2AMessageLog(BaseModel):
    """A2A message log entry"""
    message_id: str
    session_id: Optional[str] = None
    sender: str
    receiver: str
    message_type: str
    timestamp: str
    task: Optional[str] = None
    status: str
    data: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)


class WorkflowValidateRequest(BaseModel):
    """Request to run full validation workflow"""
    ab_test_context: ABTestContextRequest = Field(..., description="A/B test context")
    task_description: Optional[str] = Field(
        "Validate A/B test experiment",
        description="Custom task description"
    )


class WorkflowValidateResponse(BaseModel):
    """Response from validation workflow"""
    workflow_id: str = Field(..., description="Unique workflow execution identifier")
    status: WorkflowStatus = Field(..., description="Workflow execution status")
    final_score: float = Field(..., description="Overall validation score (0-100)")
    decision: ValidationDecision = Field(..., description="Final validation decision")
    validation_summary: str = Field(..., description="Human-readable validation summary")
    breakdown: Optional[ValidationBreakdown] = Field(None, description="Score breakdown by category")
    validation_results: Dict[str, Any] = Field(..., description="Detailed validation results")
    a2a_message_log: List[A2AMessageLog] = Field(..., description="Complete A2A message log")
    timestamp: str = Field(..., description="Completion timestamp (ISO format)")
    execution_time_seconds: Optional[float] = Field(None, description="Total execution time")


# ============================================================================
# Workflow Status/Results Schemas (for async endpoints)
# ============================================================================

class WorkflowStatusResponse(BaseModel):
    """Response for workflow status check"""
    workflow_id: str = Field(..., description="Workflow execution identifier")
    status: WorkflowStatus = Field(..., description="Current execution status")
    started_at: str = Field(..., description="Start timestamp (ISO format)")
    completed_at: Optional[str] = Field(None, description="Completion timestamp (ISO format)")
    progress: Optional[str] = Field(None, description="Current progress description")
    error: Optional[str] = Field(None, description="Error message if failed")


class WorkflowResultsResponse(BaseModel):
    """Response for retrieving workflow results"""
    workflow_id: str = Field(..., description="Workflow execution identifier")
    status: WorkflowStatus = Field(..., description="Workflow execution status")
    final_score: Optional[float] = Field(None, description="Overall validation score (0-100)")
    decision: Optional[ValidationDecision] = Field(None, description="Final validation decision")
    validation_summary: Optional[str] = Field(None, description="Human-readable validation summary")
    breakdown: Optional[ValidationBreakdown] = Field(None, description="Score breakdown by category")
    validation_results: Optional[Dict[str, Any]] = Field(None, description="Detailed validation results")
    a2a_message_log: Optional[List[A2AMessageLog]] = Field(None, description="Complete A2A message log")
    timestamp: str = Field(..., description="Result timestamp (ISO format)")


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: str = Field(..., description="Error timestamp (ISO format)")


# ============================================================================
# Health Check Schema
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    agents_available: int = Field(..., description="Number of available agents")
    timestamp: str = Field(..., description="Health check timestamp (ISO format)")

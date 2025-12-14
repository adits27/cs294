"""
A2A Compliant HTTP API Layer

This module provides REST API endpoints for the A/B test validation system.
"""
from api.server import app
from api.schemas import (
    AgentMetadata,
    AgentListResponse,
    AgentInvokeRequest,
    AgentInvokeResponse,
    ABTestContextRequest,
    WorkflowValidateRequest,
    WorkflowValidateResponse,
    WorkflowStatusResponse,
    WorkflowResultsResponse,
    ValidationBreakdown,
    ValidationDecision,
    WorkflowStatus,
    ErrorResponse,
    HealthCheckResponse,
)

__all__ = [
    "app",
    # Schemas
    "AgentMetadata",
    "AgentListResponse",
    "AgentInvokeRequest",
    "AgentInvokeResponse",
    "ABTestContextRequest",
    "WorkflowValidateRequest",
    "WorkflowValidateResponse",
    "WorkflowStatusResponse",
    "WorkflowResultsResponse",
    "ValidationBreakdown",
    "ValidationDecision",
    "WorkflowStatus",
    "ErrorResponse",
    "HealthCheckResponse",
]

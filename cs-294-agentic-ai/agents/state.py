"""
State Management for Multi-Agent A/B Testing System

This module defines the shared state and context schemas used across
all agents in the validation and assessment pipeline.
"""

from typing import Annotated, Any, Dict, List, TypedDict
from operator import add

from pydantic import BaseModel, Field

from .protocol import A2AMessage


def merge_dicts(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with right values taking precedence.

    Used as a reducer for ValidationState.validation_results to handle
    concurrent updates from parallel agent nodes.

    For nested dictionaries (like agent_responses), this merges them
    instead of overwriting.
    """
    result = left.copy()

    for key, value in right.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Deep merge nested dictionaries
            result[key] = {**result[key], **value}
        else:
            # Override with right value
            result[key] = value

    return result


class ABTestContext(BaseModel):
    """
    Context information for an A/B test validation task.

    This schema captures all the essential parameters and metadata
    needed to validate an A/B test experiment.
    """
    hypothesis: str = Field(
        ...,
        description="The hypothesis being tested in the A/B experiment"
    )
    success_metrics: List[str] = Field(
        ...,
        description="List of metrics used to measure success (e.g., conversion_rate, revenue)"
    )
    dataset_path: str = Field(
        ...,
        description="Path to the A/B test dataset"
    )
    code_path: str = Field(
        default="",
        description="Path to the analysis code file (optional, defaults to dataset_path with .py extension)"
    )
    report_path: str = Field(
        default="",
        description="Path to the analysis report file (optional, defaults to dataset_path with _report.md)"
    )
    expected_effect_size: float = Field(
        ...,
        description="Expected effect size for the test (e.g., minimum detectable effect)"
    )
    significance_level: float = Field(
        default=0.05,
        description="Statistical significance level (alpha) for hypothesis testing"
    )
    power: float = Field(
        default=0.80,
        description="Statistical power (1 - beta) for the test"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "hypothesis": "New checkout flow increases conversion rate",
                "success_metrics": ["conversion_rate", "average_order_value"],
                "dataset_path": "/data/ab_test_results.csv",
                "expected_effect_size": 0.05,
                "significance_level": 0.05,
                "power": 0.80
            }
        }


class ValidationState(TypedDict):
    """
    Validation state for LangGraph compatibility with parallel execution support.

    This TypedDict tracks the complete state of the validation workflow,
    including task information, context, message logs, and results.

    Uses Annotated types with reducers to handle concurrent updates from
    parallel agent nodes:
    - a2a_message_log: Uses 'add' operator to append messages
    - validation_results: Uses 'merge_dicts' to merge result dictionaries
    """
    task: str
    ab_test_context: ABTestContext
    a2a_message_log: Annotated[List[A2AMessage], add]
    validation_results: Annotated[Dict[str, Any], merge_dicts]
    final_score: float
    validation_summary: str


def create_initial_state(
    task: str,
    ab_test_context: ABTestContext
) -> ValidationState:
    """
    Create an initial validation state with default values.

    Args:
        task: Description of the validation task
        ab_test_context: A/B test context information

    Returns:
        ValidationState: Initialized state dictionary
    """
    return ValidationState(
        task=task,
        ab_test_context=ab_test_context,
        a2a_message_log=[],
        validation_results={},
        final_score=0.0,
        validation_summary=""
    )


def update_validation_state(
    state: ValidationState,
    message: A2AMessage = None,
    validation_results: Dict[str, Any] = None,
    final_score: float = None,
    validation_summary: str = None
) -> ValidationState:
    """
    Update validation state with new information.

    Args:
        state: Current validation state
        message: Optional A2A message to add to log
        validation_results: Optional validation results to merge
        final_score: Optional final score to set
        validation_summary: Optional summary to set

    Returns:
        ValidationState: Updated state dictionary
    """
    updated_state = state.copy()

    if message is not None:
        updated_state["a2a_message_log"] = state["a2a_message_log"] + [message]

    if validation_results is not None:
        updated_state["validation_results"] = {
            **state["validation_results"],
            **validation_results
        }

    if final_score is not None:
        updated_state["final_score"] = final_score

    if validation_summary is not None:
        updated_state["validation_summary"] = validation_summary

    return updated_state

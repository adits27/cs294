"""
Multi-Agent A/B Testing Validation and Assessor System

This package contains all agent definitions, protocols, and state management
for the A2A-based A/B testing validation system.
"""

from .base_agent import BaseAgent
from .protocol import A2AMessage, MessageStatus, MessageType
from .state import ABTestContext, ValidationState, create_initial_state, update_validation_state, merge_dicts
from .orchestrator import OrchestratingAgent
from .workflow import create_validation_workflow, run_validation_workflow
from .parameter_inference_agent import ParameterInferenceAgent
from .data_validation_agent import DataValidationAgent
from .code_validation_agent import CodeValidationAgent
from .report_validation_agent import ReportValidationAgent
from .statistical_validation_agent import StatisticalValidationAgent
from .storage import resolve_path, resolve_directory, get_r2_storage, is_r2_path

__all__ = [
    "BaseAgent",
    "A2AMessage",
    "MessageType",
    "MessageStatus",
    "ABTestContext",
    "ValidationState",
    "create_initial_state",
    "update_validation_state",
    "merge_dicts",
    "OrchestratingAgent",
    "create_validation_workflow",
    "run_validation_workflow",
    "ParameterInferenceAgent",
    "DataValidationAgent",
    "CodeValidationAgent",
    "ReportValidationAgent",
    "StatisticalValidationAgent",
    "resolve_path",
    "resolve_directory",
    "get_r2_storage",
    "is_r2_path",
]

__version__ = "0.1.0"

"""
Multi-Agent A/B Testing Validation and Assessor System

This package contains all agent definitions, protocols, and state management
for the A2A-based A/B testing validation system.
"""

from .base_agent import BaseAgent
from .protocol import A2AMessage, MessageStatus, MessageType
from .state import ABTestContext, ValidationState, create_initial_state, update_validation_state

__all__ = [
    "BaseAgent",
    "A2AMessage",
    "MessageType",
    "MessageStatus",
    "ABTestContext",
    "ValidationState",
    "create_initial_state",
    "update_validation_state",
]

__version__ = "0.1.0"

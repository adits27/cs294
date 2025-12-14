"""
A2A (Agent-to-Agent) Protocol Message Definitions

This module defines the standard message format for all agent-to-agent communications
in the Multi-Agent A/B Testing Validation and Assessor system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Enumeration of possible message types in the A2A protocol."""
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"
    ERROR = "ERROR"


class MessageStatus(str, Enum):
    """Enumeration of possible message statuses."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class A2AMessage(BaseModel):
    """
    Standard A2A Message format for agent-to-agent communication.

    All agents must use this message format to ensure interoperability
    and maintain a consistent communication protocol.
    """
    message_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this message"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier for tracking conversation context across multiple messages"
    )
    sender: str = Field(
        ...,
        description="Identifier of the agent sending this message"
    )
    receiver: str = Field(
        ...,
        description="Identifier of the agent receiving this message"
    )
    message_type: MessageType = Field(
        ...,
        description="Type of message: REQUEST, RESPONSE, or ERROR"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO format timestamp of message creation"
    )
    task: Optional[str] = Field(
        default=None,
        description="Optional task identifier or description"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible payload containing message-specific data"
    )
    status: MessageStatus = Field(
        default=MessageStatus.PENDING,
        description="Current status of the message/task"
    )
    result: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible payload containing result data"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "message_id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": "abc123-session-xyz789",
                "sender": "orchestrator",
                "receiver": "data_validator",
                "message_type": "REQUEST",
                "timestamp": "2025-12-12T10:30:00.000000",
                "task": "validate_dataset",
                "data": {
                    "dataset_path": "/path/to/data.csv",
                    "validation_rules": ["check_nulls", "check_distribution"]
                },
                "status": "PENDING",
                "result": {}
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        return self.model_dump()

    def to_json(self) -> str:
        """Convert message to JSON string."""
        return self.model_dump_json(indent=2)

"""
Base Agent Abstract Class

This module defines the abstract base class that all agents in the
Multi-Agent A/B Testing system must inherit from. It enforces the
A2A protocol and provides common functionality.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from .protocol import A2AMessage, MessageStatus, MessageType


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.

    All agents must implement the process_request method and communicate
    using the standardized A2AMessage format.
    """

    def __init__(self, agent_id: str):
        """
        Initialize the base agent.

        Args:
            agent_id: Unique identifier for this agent
        """
        self.agent_id = agent_id

    @abstractmethod
    def process_request(self, message: A2AMessage) -> A2AMessage:
        """
        Process an incoming A2A message request.

        This method must be implemented by all concrete agent classes.
        It should process the request and return an appropriate A2A response.

        Args:
            message: Incoming A2A message to process

        Returns:
            A2AMessage: Response message with results or error information

        Raises:
            NotImplementedError: If not implemented by concrete class
        """
        raise NotImplementedError("Agents must implement process_request method")

    def create_response(
        self,
        original_message: A2AMessage,
        result_data: Dict[str, Any],
        status: MessageStatus = MessageStatus.COMPLETED
    ) -> A2AMessage:
        """
        Create a standardized A2A response message.

        Helper method to generate a properly formatted response to an incoming request.
        Automatically sets message_type to RESPONSE or ERROR based on status.

        Args:
            original_message: The original request message being responded to
            result_data: Dictionary containing the result data to return
            status: Status of the response (COMPLETED, FAILED, or PENDING)

        Returns:
            A2AMessage: Properly formatted response message
        """
        message_type = MessageType.ERROR if status == MessageStatus.FAILED else MessageType.RESPONSE

        return A2AMessage(
            sender=self.agent_id,
            receiver=original_message.sender,
            message_type=message_type,
            task=original_message.task,
            data=original_message.data,
            status=status,
            result=result_data
        )

    def create_request(
        self,
        receiver: str,
        task: str,
        data: Dict[str, Any]
    ) -> A2AMessage:
        """
        Create a standardized A2A request message.

        Helper method to generate a properly formatted request to send to another agent.

        Args:
            receiver: Agent ID of the receiving agent
            task: Task identifier or description
            data: Dictionary containing the request data

        Returns:
            A2AMessage: Properly formatted request message
        """
        return A2AMessage(
            sender=self.agent_id,
            receiver=receiver,
            message_type=MessageType.REQUEST,
            task=task,
            data=data,
            status=MessageStatus.PENDING,
            result={}
        )

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(agent_id='{self.agent_id}')"

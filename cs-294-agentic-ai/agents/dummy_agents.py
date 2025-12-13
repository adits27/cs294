"""
Dummy Sub-Agents for Testing

This module contains barebones implementations of all four validation agents
that return fixed scores for testing the orchestrator's weighted scoring logic.
"""

from .base_agent import BaseAgent
from .protocol import A2AMessage, MessageStatus


class DataValidationAgent(BaseAgent):
    """
    Data Quality Validation Agent (Dummy Implementation)

    Validates data quality aspects of the A/B test including:
    - Data completeness
    - Missing values
    - Data distribution
    - Sample size adequacy
    """

    def __init__(self, agent_id: str = "data_val_agent"):
        """Initialize the data validation agent."""
        super().__init__(agent_id)

    def process_request(self, message: A2AMessage) -> A2AMessage:
        """
        Process data validation request.

        Returns a dummy score of 85.0 for testing.

        Args:
            message: Incoming A2A request message

        Returns:
            A2AMessage: Response with dummy validation score
        """
        # Dummy validation logic - returns fixed score
        dummy_score = 85.0

        result_data = {
            "score": dummy_score,
            "validation_type": "data_quality",
            "checks_performed": [
                "completeness_check",
                "missing_values_check",
                "distribution_check",
                "sample_size_check"
            ],
            "details": {
                "completeness": 90.0,
                "missing_values": 95.0,
                "distribution_balance": 80.0,
                "sample_size_adequate": True
            },
            "message": f"Data quality validation completed with score: {dummy_score}"
        }

        return self.create_response(
            message,
            result_data,
            MessageStatus.COMPLETED
        )


class CodeValidationAgent(BaseAgent):
    """
    Code Quality Validation Agent (Dummy Implementation)

    Validates code quality aspects of the A/B test implementation:
    - Code structure
    - Best practices
    - Error handling
    - Documentation
    """

    def __init__(self, agent_id: str = "code_val_agent"):
        """Initialize the code validation agent."""
        super().__init__(agent_id)

    def process_request(self, message: A2AMessage) -> A2AMessage:
        """
        Process code validation request.

        Returns a dummy score of 78.0 for testing.

        Args:
            message: Incoming A2A request message

        Returns:
            A2AMessage: Response with dummy validation score
        """
        # Dummy validation logic - returns fixed score
        dummy_score = 78.0

        result_data = {
            "score": dummy_score,
            "validation_type": "code_quality",
            "checks_performed": [
                "code_structure_check",
                "best_practices_check",
                "error_handling_check",
                "documentation_check"
            ],
            "details": {
                "structure_quality": 80.0,
                "follows_best_practices": 75.0,
                "error_handling": 70.0,
                "documentation_coverage": 85.0
            },
            "message": f"Code quality validation completed with score: {dummy_score}"
        }

        return self.create_response(
            message,
            result_data,
            MessageStatus.COMPLETED
        )


class ReportValidationAgent(BaseAgent):
    """
    Report Quality Validation Agent (Dummy Implementation)

    Validates the quality and completeness of the A/B test report:
    - Report structure
    - Clarity of findings
    - Completeness
    - Visualizations
    """

    def __init__(self, agent_id: str = "report_val_agent"):
        """Initialize the report validation agent."""
        super().__init__(agent_id)

    def process_request(self, message: A2AMessage) -> A2AMessage:
        """
        Process report validation request.

        Returns a dummy score of 92.0 for testing.

        Args:
            message: Incoming A2A request message

        Returns:
            A2AMessage: Response with dummy validation score
        """
        # Dummy validation logic - returns fixed score
        dummy_score = 92.0

        result_data = {
            "score": dummy_score,
            "validation_type": "report_quality",
            "checks_performed": [
                "structure_check",
                "clarity_check",
                "completeness_check",
                "visualization_check"
            ],
            "details": {
                "structure_quality": 95.0,
                "findings_clarity": 90.0,
                "completeness": 92.0,
                "visualization_quality": 91.0
            },
            "message": f"Report quality validation completed with score: {dummy_score}"
        }

        return self.create_response(
            message,
            result_data,
            MessageStatus.COMPLETED
        )


class StatisticalValidationAgent(BaseAgent):
    """
    Statistical Validation Agent (Dummy Implementation)

    Validates statistical rigor of the A/B test:
    - Test power analysis
    - Statistical significance
    - Effect size calculation
    - Multiple testing corrections
    """

    def __init__(self, agent_id: str = "stats_val_agent"):
        """Initialize the statistical validation agent."""
        super().__init__(agent_id)

    def process_request(self, message: A2AMessage) -> A2AMessage:
        """
        Process statistical validation request.

        Returns a dummy score of 88.0 for testing.

        Args:
            message: Incoming A2A request message

        Returns:
            A2AMessage: Response with dummy validation score
        """
        # Dummy validation logic - returns fixed score
        dummy_score = 88.0

        result_data = {
            "score": dummy_score,
            "validation_type": "statistical_validation",
            "checks_performed": [
                "power_analysis",
                "significance_test",
                "effect_size_check",
                "multiple_testing_correction"
            ],
            "details": {
                "power_adequate": True,
                "statistically_significant": True,
                "effect_size_meaningful": 90.0,
                "corrections_applied": 85.0
            },
            "message": f"Statistical validation completed with score: {dummy_score}"
        }

        return self.create_response(
            message,
            result_data,
            MessageStatus.COMPLETED
        )


# Example: Create an agent that returns a failing score
class FailingDummyAgent(BaseAgent):
    """
    Dummy agent that returns a low score for testing failure cases.
    """

    def __init__(self, agent_id: str = "failing_agent", score: float = 45.0):
        """Initialize the failing dummy agent."""
        super().__init__(agent_id)
        self.dummy_score = score

    def process_request(self, message: A2AMessage) -> A2AMessage:
        """
        Process request and return a failing score.

        Args:
            message: Incoming A2A request message

        Returns:
            A2AMessage: Response with low validation score
        """
        result_data = {
            "score": self.dummy_score,
            "validation_type": "generic_validation",
            "message": f"Validation completed with score: {self.dummy_score}"
        }

        return self.create_response(
            message,
            result_data,
            MessageStatus.COMPLETED
        )

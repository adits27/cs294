"""
Orchestrating Agent for A/B Testing Validation

This module implements the main orchestrating agent that coordinates
all sub-agents and synthesizes the final validation score.
"""

from typing import Any, Dict, List

from .base_agent import BaseAgent
from .protocol import A2AMessage, MessageStatus, MessageType
from .state import ValidationState


class OrchestratingAgent(BaseAgent):
    """
    Main orchestrator for A/B test validation.

    Coordinates sub-agents for data, code, report, and statistical validation,
    then synthesizes their results into a final weighted score.
    """

    # Weighted scoring configuration
    SCORING_WEIGHTS = {
        "statistical_validation": 0.40,  # 40%
        "report_quality": 0.30,          # 30%
        "data_quality": 0.20,            # 20%
        "code_quality": 0.10             # 10%
    }

    # Mapping of validation types to agent IDs
    AGENT_MAPPING = {
        "statistical_validation": "stats_val_agent",
        "report_quality": "report_val_agent",
        "data_quality": "data_val_agent",
        "code_quality": "code_val_agent"
    }

    def __init__(self, agent_id: str = "orchestrator"):
        """Initialize the orchestrating agent."""
        super().__init__(agent_id)

    def process_request(self, message: A2AMessage) -> A2AMessage:
        """
        Process orchestration requests.

        This method handles high-level orchestration commands.

        Args:
            message: Incoming A2A message

        Returns:
            A2AMessage: Response with orchestration results
        """
        task = message.task

        if task == "orchestrate_validation":
            # This would be called by the LangGraph workflow
            return self.create_response(
                message,
                {"status": "Orchestration initiated"},
                MessageStatus.COMPLETED
            )
        else:
            return self.create_response(
                message,
                {"error": f"Unknown task: {task}"},
                MessageStatus.FAILED
            )

    def plan_validation(self, state: ValidationState) -> ValidationState:
        """
        Plan which sub-agents to call for validation.

        For now, defaults to calling all four sub-agents.

        Args:
            state: Current validation state

        Returns:
            ValidationState: Updated state with planning information
        """
        from .state import update_validation_state

        # For now, we always call all four agents
        agents_to_call = list(self.AGENT_MAPPING.values())

        # Log the planning decision
        planning_message = A2AMessage(
            sender=self.agent_id,
            receiver=self.agent_id,
            message_type=MessageType.REQUEST,
            task="plan_validation",
            data={
                "agents_to_call": agents_to_call,
                "ab_test_context": state["ab_test_context"].model_dump()
            },
            status=MessageStatus.COMPLETED,
            result={
                "plan": f"Will delegate to {len(agents_to_call)} agents: {', '.join(agents_to_call)}"
            }
        )

        return update_validation_state(
            state,
            message=planning_message,
            validation_results={"agents_to_call": agents_to_call}
        )

    def create_delegation_requests(
        self,
        state: ValidationState
    ) -> List[A2AMessage]:
        """
        Create A2A request messages for all sub-agents.

        Args:
            state: Current validation state

        Returns:
            List[A2AMessage]: List of request messages for sub-agents
        """
        requests = []
        agents_to_call = state["validation_results"].get(
            "agents_to_call",
            list(self.AGENT_MAPPING.values())
        )

        for agent_id in agents_to_call:
            # Determine the task based on agent type
            task_mapping = {
                "data_val_agent": "validate_data_quality",
                "code_val_agent": "validate_code_quality",
                "report_val_agent": "validate_report_quality",
                "stats_val_agent": "validate_statistical_rigor"
            }

            task = task_mapping.get(agent_id, "validate")

            request = self.create_request(
                receiver=agent_id,
                task=task,
                data={
                    "ab_test_context": state["ab_test_context"].model_dump(),
                    "task_description": state["task"]
                }
            )
            requests.append(request)

        return requests

    def synthesize_results(
        self,
        state: ValidationState,
        agent_responses: Dict[str, A2AMessage]
    ) -> Dict[str, Any]:
        """
        Synthesize results from all sub-agents into a final score.

        Implements weighted scoring:
        - Statistical Validation: 40%
        - Report Quality: 30%
        - Data Quality: 20%
        - Code Quality: 10%

        Handles missing agents by re-normalizing weights.

        Args:
            state: Current validation state
            agent_responses: Dictionary mapping agent IDs to their response messages

        Returns:
            Dict containing final_score, decision, and breakdown
        """
        # Extract scores from agent responses
        scores = {}
        for validation_type, agent_id in self.AGENT_MAPPING.items():
            if agent_id in agent_responses:
                response = agent_responses[agent_id]
                if response.status == MessageStatus.COMPLETED:
                    # Extract score from result
                    score = response.result.get("score", 0.0)
                    scores[validation_type] = score

        # Calculate weights for available agents (re-normalize if needed)
        available_weights = {
            k: v for k, v in self.SCORING_WEIGHTS.items()
            if k in scores
        }

        if not available_weights:
            # No valid scores available
            return {
                "final_score": 0.0,
                "decision": "BAD A/B TEST",
                "reason": "No validation results available",
                "breakdown": {}
            }

        # Re-normalize weights to sum to 1.0
        total_weight = sum(available_weights.values())
        normalized_weights = {
            k: v / total_weight
            for k, v in available_weights.items()
        }

        # Calculate weighted score
        final_score = sum(
            scores[validation_type] * normalized_weights[validation_type]
            for validation_type in available_weights.keys()
        )

        # Determine decision (threshold: 70)
        decision = "GOOD A/B TEST" if final_score >= 70.0 else "BAD A/B TEST"

        # Create detailed breakdown
        breakdown = {}
        for validation_type in self.SCORING_WEIGHTS.keys():
            if validation_type in scores:
                breakdown[validation_type] = {
                    "score": scores[validation_type],
                    "weight": self.SCORING_WEIGHTS[validation_type],
                    "normalized_weight": normalized_weights[validation_type],
                    "weighted_contribution": scores[validation_type] * normalized_weights[validation_type],
                    "status": "completed"
                }
            else:
                breakdown[validation_type] = {
                    "score": None,
                    "weight": self.SCORING_WEIGHTS[validation_type],
                    "status": "missing"
                }

        return {
            "final_score": round(final_score, 2),
            "decision": decision,
            "breakdown": breakdown,
            "agents_used": len(scores),
            "total_agents": len(self.AGENT_MAPPING)
        }

    def generate_summary(self, synthesis_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable validation summary.

        Args:
            synthesis_result: Result from synthesize_results

        Returns:
            str: Formatted summary string
        """
        summary_lines = [
            "=" * 60,
            "A/B TEST VALIDATION SUMMARY",
            "=" * 60,
            f"Final Score: {synthesis_result['final_score']}/100",
            f"Decision: {synthesis_result['decision']}",
            "",
            "Score Breakdown:",
            "-" * 60
        ]

        for validation_type, details in synthesis_result["breakdown"].items():
            if details["status"] == "completed":
                summary_lines.append(
                    f"  {validation_type.replace('_', ' ').title()}: "
                    f"{details['score']:.1f} "
                    f"(weight: {details['weight']*100:.0f}%, "
                    f"contribution: {details['weighted_contribution']:.1f})"
                )
            else:
                summary_lines.append(
                    f"  {validation_type.replace('_', ' ').title()}: "
                    f"MISSING (weight: {details['weight']*100:.0f}%)"
                )

        summary_lines.extend([
            "-" * 60,
            f"Agents Used: {synthesis_result['agents_used']}/{synthesis_result['total_agents']}",
            "=" * 60
        ])

        return "\n".join(summary_lines)

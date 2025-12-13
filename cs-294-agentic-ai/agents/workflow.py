"""
LangGraph Workflow for A/B Testing Validation

This module defines the LangGraph workflow that orchestrates the
validation process across multiple specialized agents.
"""

from typing import Any, Dict

from langgraph.graph import StateGraph, END

from .orchestrator import OrchestratingAgent
from .protocol import A2AMessage, MessageStatus
from .state import ValidationState, update_validation_state
from .logger import setup_logger

logger = setup_logger(__name__)
orchestrator = OrchestratingAgent()


def plan_validation_node(state: ValidationState) -> ValidationState:
    """
    Node 1: Plan which sub-agents to call for validation.

    Analyzes the AB test context and decides which validators to invoke.
    For now, defaults to calling all four agents.

    Args:
        state: Current validation state

    Returns:
        ValidationState: Updated state with planning results
    """
    logger.info("Planning validation workflow")
    logger.debug(f"Task: {state['task']}, Hypothesis: {state['ab_test_context'].hypothesis}")

    updated_state = orchestrator.plan_validation(state)

    agents_to_call = updated_state["validation_results"].get("agents_to_call", [])
    logger.info(f"Planned to call {len(agents_to_call)} agents: {', '.join(agents_to_call)}")

    return updated_state


def delegate_to_agents_node(state: ValidationState) -> ValidationState:
    """
    Node 2: Delegate tasks to sub-agents via A2A messages.

    Constructs A2A REQUEST messages for all planned sub-agents.
    In this stage, prints the messages being sent (actual agent execution
    will be added when we integrate real agents).

    Args:
        state: Current validation state

    Returns:
        ValidationState: Updated state with delegation messages logged
    """
    print("\n[WORKFLOW] Node 2: Delegating to agents...")

    # Create request messages for all sub-agents
    requests = orchestrator.create_delegation_requests(state)

    print(f"  Creating {len(requests)} A2A request messages:")

    # Log each request and add to message log
    updated_state = state
    for request in requests:
        print(f"\n  → Sending to {request.receiver}:")
        print(f"    Task: {request.task}")
        print(f"    Message ID: {request.message_id}")
        print(f"    Data: {list(request.data.keys())}")

        # Add to message log
        updated_state = update_validation_state(
            updated_state,
            message=request
        )

    # Store requests for later retrieval
    updated_state = update_validation_state(
        updated_state,
        validation_results={"pending_requests": requests}
    )

    return updated_state


def data_validation_node(state: ValidationState) -> Dict[str, Any]:
    """
    Execute Data Validation Agent in parallel.

    Args:
        state: Current validation state

    Returns:
        Dict: Partial state update with data validation response
    """
    from .data_validation_agent import DataValidationAgent

    print("\n[WORKFLOW - PARALLEL] Executing Data Validation Agent...")

    # Find the request for this agent
    requests = state["validation_results"].get("pending_requests", [])
    request = next((r for r in requests if r.receiver == "data_val_agent"), None)

    if request:
        agent = DataValidationAgent()
        response = agent.process_request(request)

        print(f"  Data Validation: {response.result.get('score', 0.0)}")

        # Return only the updates (for parallel merging)
        return {
            "a2a_message_log": [response],
            "validation_results": {
                "agent_responses": {"data_val_agent": response}
            }
        }

    return {}


def code_validation_node(state: ValidationState) -> Dict[str, Any]:
    """
    Execute Code Validation Agent in parallel.

    Args:
        state: Current validation state

    Returns:
        Dict: Partial state update with code validation response
    """
    from .code_validation_agent import CodeValidationAgent

    print("\n[WORKFLOW - PARALLEL] Executing Code Validation Agent...")

    # Find the request for this agent
    requests = state["validation_results"].get("pending_requests", [])
    request = next((r for r in requests if r.receiver == "code_val_agent"), None)

    if request:
        agent = CodeValidationAgent()
        response = agent.process_request(request)

        print(f"  Code Validation: {response.result.get('score', 0.0)}")

        # Return only the updates (for parallel merging)
        return {
            "a2a_message_log": [response],
            "validation_results": {
                "agent_responses": {"code_val_agent": response}
            }
        }

    return {}


def report_validation_node(state: ValidationState) -> Dict[str, Any]:
    """
    Execute Report Validation Agent in parallel.

    Args:
        state: Current validation state

    Returns:
        Dict: Partial state update with report validation response
    """
    from .report_validation_agent import ReportValidationAgent

    print("\n[WORKFLOW - PARALLEL] Executing Report Validation Agent...")

    # Find the request for this agent
    requests = state["validation_results"].get("pending_requests", [])
    request = next((r for r in requests if r.receiver == "report_val_agent"), None)

    if request:
        agent = ReportValidationAgent()
        response = agent.process_request(request)

        print(f"  Report Validation: {response.result.get('score', 0.0)}")

        # Return only the updates (for parallel merging)
        return {
            "a2a_message_log": [response],
            "validation_results": {
                "agent_responses": {"report_val_agent": response}
            }
        }

    return {}


def stats_validation_node(state: ValidationState) -> Dict[str, Any]:
    """
    Execute Statistical Validation Agent in parallel.

    Args:
        state: Current validation state

    Returns:
        Dict: Partial state update with statistical validation response
    """
    from .statistical_validation_agent import StatisticalValidationAgent

    print("\n[WORKFLOW - PARALLEL] Executing Statistical Validation Agent...")

    # Find the request for this agent
    requests = state["validation_results"].get("pending_requests", [])
    request = next((r for r in requests if r.receiver == "stats_val_agent"), None)

    if request:
        agent = StatisticalValidationAgent()
        response = agent.process_request(request)

        print(f"  Statistical Validation: {response.result.get('score', 0.0)}")

        # Return only the updates (for parallel merging)
        return {
            "a2a_message_log": [response],
            "validation_results": {
                "agent_responses": {"stats_val_agent": response}
            }
        }

    return {}


def synthesize_results_node(state: ValidationState) -> ValidationState:
    """
    Node 3: Synthesize results from all sub-agents.

    Reads results from the state, calculates weighted scores,
    and generates the final validation decision.

    Args:
        state: Current validation state

    Returns:
        ValidationState: Updated state with final score and summary
    """
    print("\n[WORKFLOW] Node 3: Synthesizing results...")

    # Get agent responses
    agent_responses = state["validation_results"].get("agent_responses", {})

    print(f"  Processing responses from {len(agent_responses)} agents...")

    # Synthesize results using orchestrator's weighted scoring logic
    synthesis_result = orchestrator.synthesize_results(state, agent_responses)

    print(f"\n  Final Score: {synthesis_result['final_score']}/100")
    print(f"  Decision: {synthesis_result['decision']}")

    # Generate human-readable summary
    summary = orchestrator.generate_summary(synthesis_result)

    # Create final synthesis message
    synthesis_message = A2AMessage(
        sender=orchestrator.agent_id,
        receiver=orchestrator.agent_id,
        message_type="RESPONSE",
        task="synthesize_results",
        data={"synthesis": synthesis_result},
        status=MessageStatus.COMPLETED,
        result=synthesis_result
    )

    # Update state with final results
    updated_state = update_validation_state(
        state,
        message=synthesis_message,
        final_score=synthesis_result["final_score"],
        validation_summary=summary
    )

    updated_state = update_validation_state(
        updated_state,
        validation_results={
            **updated_state["validation_results"],
            "synthesis": synthesis_result
        }
    )

    return updated_state


def create_validation_workflow() -> StateGraph:
    """
    Create the LangGraph StateGraph for A/B test validation with parallel execution.

    The workflow consists of:
    1. plan_validation: Decide which agents to call
    2. delegate_to_agents: Send A2A requests to sub-agents
    3. Four parallel validation nodes (data, code, report, stats)
    4. synthesize_results: Calculate final weighted score

    The four validation agents execute in parallel branches, then converge
    at the synthesis node.

    Returns:
        StateGraph: Configured workflow graph with parallel branches
    """
    # Create the StateGraph with ValidationState
    workflow = StateGraph(ValidationState)

    # Add nodes
    workflow.add_node("plan_validation", plan_validation_node)
    workflow.add_node("delegate_to_agents", delegate_to_agents_node)

    # Parallel validation nodes
    workflow.add_node("data_validation", data_validation_node)
    workflow.add_node("code_validation", code_validation_node)
    workflow.add_node("report_validation", report_validation_node)
    workflow.add_node("stats_validation", stats_validation_node)

    workflow.add_node("synthesize_results", synthesize_results_node)

    # Define edges
    workflow.set_entry_point("plan_validation")
    workflow.add_edge("plan_validation", "delegate_to_agents")

    # Parallel branches: delegate_to_agents fans out to 4 validation nodes
    workflow.add_edge("delegate_to_agents", "data_validation")
    workflow.add_edge("delegate_to_agents", "code_validation")
    workflow.add_edge("delegate_to_agents", "report_validation")
    workflow.add_edge("delegate_to_agents", "stats_validation")

    # All validation nodes converge to synthesize_results
    workflow.add_edge("data_validation", "synthesize_results")
    workflow.add_edge("code_validation", "synthesize_results")
    workflow.add_edge("report_validation", "synthesize_results")
    workflow.add_edge("stats_validation", "synthesize_results")

    workflow.add_edge("synthesize_results", END)

    return workflow


def run_validation_workflow(state: ValidationState) -> ValidationState:
    """
    Execute the complete validation workflow.

    Args:
        state: Initial validation state

    Returns:
        ValidationState: Final state with validation results
    """
    # Create and compile the workflow
    workflow = create_validation_workflow()
    app = workflow.compile()

    # Execute the workflow
    print("\n" + "=" * 60)
    print("STARTING A/B TEST VALIDATION WORKFLOW")
    print("=" * 60)

    final_state = app.invoke(state)

    print("\n" + "=" * 60)
    print("WORKFLOW COMPLETED")
    print("=" * 60)

    return final_state

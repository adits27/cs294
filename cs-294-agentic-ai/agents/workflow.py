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


def infer_parameters_node(state: ValidationState) -> ValidationState:
    """
    Node 0: Infer A/B test parameters from files if not provided.

    Uses the ParameterInferenceAgent to extract hypothesis, metrics, effect size, etc.
    from the dataset, code, and report files.

    Args:
        state: Current validation state

    Returns:
        ValidationState: Updated state with inferred parameters in ab_test_context
    """
    from .parameter_inference_agent import ParameterInferenceAgent

    ab_test_context = state["ab_test_context"]

    # Check if we need to infer parameters
    needs_inference = (
        not ab_test_context.hypothesis or
        not ab_test_context.success_metrics
    )

    if not needs_inference:
        print("\n[WORKFLOW] Node 0: Parameters already provided, skipping inference...")
        return state

    print("\n[WORKFLOW] Node 0: Inferring parameters from files...")

    # Create inference agent
    inference_agent = ParameterInferenceAgent()

    # Create request message
    request = A2AMessage(
        sender="workflow",
        receiver="param_inference_agent",
        message_type="REQUEST",
        task="Infer A/B test parameters from provided files",
        data={
            "ab_test_context": ab_test_context,
        }
    )

    # Process request
    response = inference_agent.process_request(request)

    if response.status == MessageStatus.COMPLETED:
        inferred_params = response.result.get("inferred_parameters", {})

        # Update ab_test_context with inferred parameters (only if not already set)
        if not ab_test_context.hypothesis:
            ab_test_context.hypothesis = inferred_params.get("hypothesis", "")

        if not ab_test_context.success_metrics:
            ab_test_context.success_metrics = inferred_params.get("success_metrics", [])

        if ab_test_context.expected_effect_size == 0.05:  # default value
            ab_test_context.expected_effect_size = inferred_params.get("expected_effect_size", 0.05)

        if ab_test_context.significance_level == 0.05:  # default value
            ab_test_context.significance_level = inferred_params.get("significance_level", 0.05)

        if ab_test_context.power == 0.80:  # default value
            ab_test_context.power = inferred_params.get("power", 0.80)

        print(f"\n  ✓ Inferred Parameters:")
        print(f"    Hypothesis: {ab_test_context.hypothesis[:80]}...")
        print(f"    Metrics: {ab_test_context.success_metrics}")
        print(f"    Effect Size: {ab_test_context.expected_effect_size}")
        print(f"    Confidence: {inferred_params.get('confidence', 'unknown')}")

        # Update state
        updated_state = state.copy()
        updated_state["ab_test_context"] = ab_test_context

        # Log inference message
        updated_state = update_validation_state(
            updated_state,
            message=response
        )

        return updated_state
    else:
        print(f"  ✗ Parameter inference failed: {response.result.get('error', 'Unknown error')}")
        print(f"    Continuing with default/provided parameters...")
        return state


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
    0. infer_parameters: Extract parameters from files if not provided
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
    workflow.add_node("infer_parameters", infer_parameters_node)
    workflow.add_node("plan_validation", plan_validation_node)
    workflow.add_node("delegate_to_agents", delegate_to_agents_node)

    # Parallel validation nodes
    workflow.add_node("data_validation", data_validation_node)
    workflow.add_node("code_validation", code_validation_node)
    workflow.add_node("report_validation", report_validation_node)
    workflow.add_node("stats_validation", stats_validation_node)

    workflow.add_node("synthesize_results", synthesize_results_node)

    # Define edges
    workflow.set_entry_point("infer_parameters")
    workflow.add_edge("infer_parameters", "plan_validation")
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

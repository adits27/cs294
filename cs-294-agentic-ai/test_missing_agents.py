"""
Test Script for Weight Re-normalization with Missing Agents

This script demonstrates how the orchestrator handles missing agents
by re-normalizing the weights.
"""

from agents import ABTestContext, create_initial_state
from agents.orchestrator import OrchestratingAgent
from agents.protocol import A2AMessage, MessageStatus
from agents.dummy_agents import DataValidationAgent, StatisticalValidationAgent


def test_missing_agents():
    """Test the orchestrator with only 2 out of 4 agents responding."""

    print("\n" + "=" * 60)
    print("TESTING WEIGHT RE-NORMALIZATION WITH MISSING AGENTS")
    print("=" * 60)

    # Create orchestrator
    orchestrator = OrchestratingAgent()

    # Create a sample A/B test context
    ab_test_context = ABTestContext(
        hypothesis="New feature increases user engagement",
        success_metrics=["engagement_rate"],
        dataset_path="/data/engagement_test.csv",
        expected_effect_size=0.10,
        significance_level=0.05,
        power=0.80
    )

    # Create initial state
    state = create_initial_state(
        task="Test weight re-normalization",
        ab_test_context=ab_test_context
    )

    # Simulate only 2 agents responding (missing code and report agents)
    data_agent = DataValidationAgent()
    stats_agent = StatisticalValidationAgent()

    # Create mock requests
    data_request = orchestrator.create_request(
        receiver="data_val_agent",
        task="validate_data_quality",
        data={}
    )

    stats_request = orchestrator.create_request(
        receiver="stats_val_agent",
        task="validate_statistical_rigor",
        data={}
    )

    # Get responses
    data_response = data_agent.process_request(data_request)
    stats_response = stats_agent.process_request(stats_request)

    # Create response dictionary with only 2 agents
    agent_responses = {
        "data_val_agent": data_response,
        "stats_val_agent": stats_response
    }

    print("\nAvailable Agents: 2/4")
    print("  ✓ Data Validation Agent (score: 85.0)")
    print("  ✗ Code Validation Agent (MISSING)")
    print("  ✗ Report Validation Agent (MISSING)")
    print("  ✓ Statistical Validation Agent (score: 88.0)")

    # Synthesize results
    synthesis_result = orchestrator.synthesize_results(state, agent_responses)

    print("\n" + "=" * 60)
    print("ORIGINAL WEIGHTS")
    print("=" * 60)
    print("  Statistical Validation: 40%")
    print("  Report Quality:         30% (MISSING)")
    print("  Data Quality:           20%")
    print("  Code Quality:           10% (MISSING)")
    print("  Total:                 100%")

    print("\n" + "=" * 60)
    print("RE-NORMALIZED WEIGHTS")
    print("=" * 60)
    print("  Available weight: 40% + 20% = 60%")
    print("  Re-normalized:")
    print("    Statistical Validation: 40% / 60% = 66.67%")
    print("    Data Quality:           20% / 60% = 33.33%")
    print("  Total:                                100.00%")

    print("\n" + "=" * 60)
    print("SCORE CALCULATION")
    print("=" * 60)

    for validation_type, details in synthesis_result["breakdown"].items():
        if details["status"] == "completed":
            print(f"  {validation_type.replace('_', ' ').title()}:")
            print(f"    Score: {details['score']:.1f}")
            print(f"    Original Weight: {details['weight']*100:.1f}%")
            print(f"    Normalized Weight: {details['normalized_weight']*100:.2f}%")
            print(f"    Contribution: {details['weighted_contribution']:.2f}")
        else:
            print(f"  {validation_type.replace('_', ' ').title()}: MISSING")

    print("\n" + "-" * 60)
    print(f"  Final Score: {synthesis_result['final_score']:.2f}/100")
    print(f"  Decision: {synthesis_result['decision']}")
    print("=" * 60)

    # Show expected calculation
    print("\nExpected Calculation:")
    print("  Statistical: 88.0 × 66.67% = 58.67")
    print("  Data:        85.0 × 33.33% = 28.33")
    print("                               ------")
    print("  Final Score:                 87.00")

    print("\nActual Calculation:")
    stats_contrib = synthesis_result["breakdown"]["statistical_validation"]["weighted_contribution"]
    data_contrib = synthesis_result["breakdown"]["data_quality"]["weighted_contribution"]
    print(f"  Statistical: 88.0 × 66.67% = {stats_contrib:.2f}")
    print(f"  Data:        85.0 × 33.33% = {data_contrib:.2f}")
    print("                               " + "-" * 6)
    print(f"  Final Score:                 {synthesis_result['final_score']:.2f}")

    # Verify calculation
    expected_score = (88.0 * (40/60)) + (85.0 * (20/60))
    assert abs(synthesis_result['final_score'] - expected_score) < 0.1, \
        f"Score mismatch: expected {expected_score:.2f}, got {synthesis_result['final_score']:.2f}"

    print("\n✓ Weight re-normalization working correctly!")
    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    test_missing_agents()

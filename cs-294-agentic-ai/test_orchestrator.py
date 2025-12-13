"""
Test Script for Orchestrator and Workflow

This script demonstrates the complete A/B test validation workflow
using dummy agents to verify the weighted scoring logic.
"""

from agents import ABTestContext, create_initial_state
from agents.workflow import run_validation_workflow


def main():
    """Run the orchestrator test with a sample ABTestContext."""

    # Create a sample A/B test context
    ab_test_context = ABTestContext(
        hypothesis="New checkout button color increases conversion rate by at least 5%",
        success_metrics=["conversion_rate", "click_through_rate", "revenue_per_user"],
        dataset_path="/data/experiments/checkout_button_test.csv",
        expected_effect_size=0.05,
        significance_level=0.05,
        power=0.80
    )

    # Create initial validation state
    initial_state = create_initial_state(
        task="Validate A/B test for checkout button color experiment",
        ab_test_context=ab_test_context
    )

    print("\n" + "=" * 60)
    print("A/B TEST VALIDATION - ORCHESTRATOR TEST")
    print("=" * 60)
    print(f"\nHypothesis: {ab_test_context.hypothesis}")
    print(f"Success Metrics: {', '.join(ab_test_context.success_metrics)}")
    print(f"Dataset: {ab_test_context.dataset_path}")
    print(f"Expected Effect Size: {ab_test_context.expected_effect_size}")
    print(f"Significance Level: {ab_test_context.significance_level}")
    print(f"Power: {ab_test_context.power}")

    # Run the validation workflow
    final_state = run_validation_workflow(initial_state)

    # Display final results
    print("\n" + final_state["validation_summary"])

    # Show detailed message log
    print("\n" + "=" * 60)
    print("A2A MESSAGE LOG")
    print("=" * 60)
    print(f"\nTotal messages exchanged: {len(final_state['a2a_message_log'])}")

    for i, message in enumerate(final_state["a2a_message_log"], 1):
        print(f"\n[Message {i}]")
        print(f"  Sender: {message.sender}")
        print(f"  Receiver: {message.receiver}")
        print(f"  Type: {message.message_type}")
        print(f"  Task: {message.task}")
        print(f"  Status: {message.status}")

    # Show calculation breakdown
    print("\n" + "=" * 60)
    print("WEIGHTED SCORE CALCULATION")
    print("=" * 60)

    synthesis = final_state["validation_results"].get("synthesis", {})
    breakdown = synthesis.get("breakdown", {})

    print("\nExpected Calculation with Dummy Scores:")
    print("  Data Quality:          85.0 × 20% = 17.0")
    print("  Code Quality:          78.0 × 10% =  7.8")
    print("  Report Quality:        92.0 × 30% = 27.6")
    print("  Statistical Validation: 88.0 × 40% = 35.2")
    print("                                      ------")
    print("  Final Score:                        87.6")

    print("\nActual Calculation:")
    total_contribution = 0.0
    for validation_type, details in breakdown.items():
        if details["status"] == "completed":
            score = details["score"]
            weight = details["weight"]
            contribution = details["weighted_contribution"]
            total_contribution += contribution
            print(f"  {validation_type.replace('_', ' ').title()}: "
                  f"{score:.1f} × {weight*100:.0f}% = {contribution:.1f}")

    print("                                      " + "-" * 6)
    print(f"  Final Score:                        {total_contribution:.1f}")

    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()

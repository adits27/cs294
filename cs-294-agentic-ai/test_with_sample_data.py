"""
Test Script for Real Agents with Sample Result Data

This script tests the complete A/B test validation workflow using
the real agents with the actual sample data from results/result_1_2.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from agents import ABTestContext, create_initial_state
from agents.workflow import run_validation_workflow

# Load environment variables from .env file
load_dotenv()


class TeeOutput:
    """Writes output to both terminal and file."""
    def __init__(self, file_path):
        self.terminal = sys.stdout
        self.log_file = open(file_path, 'w', encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

    def close(self):
        self.log_file.close()


def main():
    """Run the real agent test with actual sample data."""

    # Setup log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"test_output_{timestamp}.log"
    tee = TeeOutput(log_file)
    sys.stdout = tee

    # Use the actual sample data paths from results/result_1_2
    base_path = "./results/result_1_2"

    ab_test_context = ABTestContext(
        hypothesis="New online tutoring platform increases student test scores",
        success_metrics=["test_score", "student_performance"],
        dataset_path=f"{base_path}/data_source/data.csv",
        code_path=f"{base_path}/code/analysis.py",
        report_path=f"{base_path}/report/analysis_report.md",
        expected_effect_size=0.05,
        significance_level=0.05,
        power=0.80
    )

    # Create initial validation state
    initial_state = create_initial_state(
        task="Validate A/B test for online tutoring platform experiment",
        ab_test_context=ab_test_context
    )

    print("\n" + "=" * 60)
    print("A/B TEST VALIDATION - SAMPLE DATA TEST")
    print("=" * 60)
    print(f"\nHypothesis: {ab_test_context.hypothesis}")
    print(f"Success Metrics: {', '.join(ab_test_context.success_metrics)}")
    print(f"\nTest Data Paths:")
    print(f"  Dataset: {ab_test_context.dataset_path}")
    print(f"  Code: {ab_test_context.code_path}")
    print(f"  Report: {ab_test_context.report_path}")
    print(f"\nExpected Effect Size: {ab_test_context.expected_effect_size}")
    print(f"Significance Level: {ab_test_context.significance_level}")
    print(f"Power: {ab_test_context.power}")

    print("\n" + "=" * 60)
    print("NOTE: This test uses REAL LLM agents")
    print("- Will make API calls to Google Gemini")
    print("- Will attempt tool execution (Python code)")
    print("- Will fall back to LLM if tools fail")
    print("=" * 60)

    # Check if API key is set
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\n❌ ERROR: GOOGLE_API_KEY not found in environment!")
        print("Please set GOOGLE_API_KEY in .env file")
        tee.close()
        sys.stdout = tee.terminal
        return

    print("\n✓ API Key found")
    print(f"Logging output to: {log_file}")

    # Verify sample data files exist
    print("\n" + "=" * 60)
    print("VERIFYING SAMPLE DATA FILES")
    print("=" * 60)

    files_to_check = [
        ("Dataset", ab_test_context.dataset_path),
        ("Code", ab_test_context.code_path),
        ("Report", ab_test_context.report_path),
    ]

    all_exist = True
    for name, path in files_to_check:
        exists = os.path.exists(path)
        status = "✓" if exists else "✗"
        print(f"{status} {name}: {path}")
        if not exists:
            all_exist = False

    if not all_exist:
        print("\n❌ ERROR: Some sample data files are missing!")
        print("Please ensure the results/result_1_2 directory contains all required files.")
        tee.close()
        sys.stdout = tee.terminal
        return

    # Run the validation workflow
    try:
        final_state = run_validation_workflow(initial_state)

        # Display final results
        print("\n" + final_state["validation_summary"])

        # Show agent details
        print("\n" + "=" * 60)
        print("AGENT EXECUTION DETAILS")
        print("=" * 60)

        agent_responses = final_state["validation_results"].get("agent_responses", {})

        for agent_id, response in agent_responses.items():
            print(f"\n[{agent_id}]")
            result = response.result
            print(f"  Score: {result.get('score', 0):.1f}")
            print(f"  Method: {result.get('method', 'N/A')}")
            if 'tool_success' in result:
                print(f"  Tool Success: {result['tool_success']}")
            # Print full reasoning without truncation
            reasoning = result.get('reasoning', 'N/A')
            print(f"  Reasoning: {reasoning}")

        # Show final weighted calculation
        print("\n" + "=" * 60)
        print("WEIGHTED SCORE CALCULATION")
        print("=" * 60)

        synthesis = final_state["validation_results"].get("synthesis", {})
        breakdown = synthesis.get("breakdown", {})

        print("\nCalculation:")
        total_contribution = 0.0
        for validation_type, details in breakdown.items():
            if details["status"] == "completed":
                score = details["score"]
                weight = details["weight"]
                contribution = details["weighted_contribution"]
                total_contribution += contribution
                print(f"  {validation_type.replace('_', ' ').title()}: "
                      f"{score:.1f} × {weight*100:.0f}% = {contribution:.1f}")
            else:
                weight = details["weight"]
                print(f"  {validation_type.replace('_', ' ').title()}: "
                      f"MISSING (weight: {weight*100:.0f}%)")

        print("  " + "-" * 50)
        print(f"  Final Score: {total_contribution:.1f}")

        print("\n" + "=" * 60)
        print("TEST COMPLETED")
        print("=" * 60)

        # Write detailed results to log
        print("\n" + "=" * 60)
        print("DETAILED AGENT RESULTS")
        print("=" * 60)

        for agent_id, response in agent_responses.items():
            print(f"\n{'=' * 60}")
            print(f"[{agent_id}] - FULL DETAILS")
            print('=' * 60)
            result = response.result
            print(f"Score: {result.get('score', 0):.1f}")
            print(f"Method: {result.get('method', 'N/A')}")
            print(f"Validation Type: {result.get('validation_type', 'N/A')}")
            if 'tool_success' in result:
                print(f"Tool Success: {result['tool_success']}")
            print(f"\nReasoning:\n{result.get('reasoning', 'N/A')}")

            if 'details' in result:
                print(f"\nDetails: {result['details']}")

            if 'feedback' in result:
                print("\nFeedback:")
                for key, value in result['feedback'].items():
                    print(f"  {key}: {value}")

            if 'checks_performed' in result:
                print(f"\nChecks Performed: {result['checks_performed']}")

    except Exception as e:
        print(f"\n❌ ERROR during workflow execution:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        # Close log file and restore stdout
        tee.close()
        sys.stdout = tee.terminal
        print(f"\n✓ Full output saved to: {log_file}")


if __name__ == "__main__":
    main()

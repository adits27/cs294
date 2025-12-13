"""
Data Validation Agent

Validates dataset quality including shape, nulls, types, and completeness.
Uses Python tools first, with LLM fallback if tool execution fails.
"""

import os
from typing import Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from .base_agent import BaseAgent
from .protocol import A2AMessage, MessageStatus
from .tools import python_repl
from .logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)


class DataValidationAgent(BaseAgent):
    """
    Data Quality Validation Agent (Real Implementation)

    Validates data quality aspects of the A/B test including:
    - Data completeness and shape
    - Missing values
    - Data types
    - Sample size adequacy

    Strategy:
    1. Attempt to use Python tools (pandas) for accurate analysis
    2. Fallback to LLM-based heuristic assessment if tools fail
    """

    def __init__(self, agent_id: str = "data_val_agent"):
        """Initialize the data validation agent."""
        super().__init__(agent_id)

        # Initialize LLM
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.0,
            google_api_key=api_key
        )

    def process_request(self, message: A2AMessage) -> A2AMessage:
        """
        Process data validation request.

        Args:
            message: Incoming A2A request message

        Returns:
            A2AMessage: Response with validation score and details
        """
        ab_test_context = message.data.get("ab_test_context", {})
        dataset_path = ab_test_context.get("dataset_path", "")

        logger.info(f"Starting data validation for dataset: {dataset_path}")

        tool_result = self._validate_with_tool(dataset_path, ab_test_context)

        if tool_result["success"]:
            logger.info("Tool execution successful, using tool-based analysis")
            analysis = tool_result["output"]
            method = "tool"
        else:
            logger.warning(f"Tool execution failed: {tool_result['error']}")
            logger.info("Falling back to LLM heuristic assessment")
            analysis = self._fallback_to_llm(dataset_path, ab_test_context, tool_result["error"])
            method = "llm_fallback"

        score_result = self._score_analysis(analysis, method, ab_test_context)
        logger.info(f"Data validation completed - Score: {score_result['score']:.1f}, Method: {method}")

        # Prepare result data
        result_data = {
            "score": score_result["score"],
            "validation_type": "data_quality",
            "method": method,
            "analysis": analysis,
            "reasoning": score_result["reasoning"],
            "checks_performed": [
                "data_shape_check",
                "missing_values_check",
                "data_types_check",
                "sample_size_check"
            ],
            "tool_success": tool_result["success"],
            "details": score_result.get("details", {})
        }

        return self.create_response(
            message,
            result_data,
            MessageStatus.COMPLETED
        )

    def _validate_with_tool(self, dataset_path: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate dataset using Python tools (pandas).

        Args:
            dataset_path: Path to the dataset
            context: A/B test context

        Returns:
            Dict with success status and output/error
        """
        # Generate Python code to analyze the dataset
        code_prompt = f"""Generate Python code to analyze the dataset at '{dataset_path}'.

The code should:
1. Import pandas
2. Load the dataset (try CSV first, then other formats)
3. Print dataset shape
4. Print missing value counts
5. Print data types
6. Print basic statistics

Respond with ONLY the Python code, no explanations."""

        try:
            response = self.llm.invoke(code_prompt)
            generated_code = response.content.strip()

            if "```python" in generated_code:
                generated_code = generated_code.split("```python")[1].split("```")[0].strip()
            elif "```" in generated_code:
                generated_code = generated_code.split("```")[1].split("```")[0].strip()

            logger.debug(f"Generated analysis code: {len(generated_code)} characters")

            result = python_repl.run(generated_code)
            return result

        except Exception as e:
            logger.error(f"Code generation/execution failed: {str(e)}")
            return {
                "success": False,
                "output": "",
                "error": f"Code generation/execution failed: {str(e)}"
            }

    def _fallback_to_llm(
        self,
        dataset_path: str,
        context: Dict[str, Any],
        tool_error: str
    ) -> str:
        """
        Fallback to LLM-based heuristic assessment.

        Args:
            dataset_path: Path to the dataset
            context: A/B test context
            tool_error: Error from tool execution

        Returns:
            str: LLM-generated analysis
        """
        fallback_prompt = f"""You are a data quality expert. The automated tool failed to analyze the dataset, but you need to provide a heuristic assessment.

Dataset Path: {dataset_path}
Hypothesis: {context.get('hypothesis', 'N/A')}
Success Metrics: {context.get('success_metrics', [])}
Expected Effect Size: {context.get('expected_effect_size', 'N/A')}

Tool Error: {tool_error}

Based on the file name, hypothesis, and standard A/B testing requirements, provide a heuristic assessment of the data quality needs. Consider:
1. What data structure would be required for this test?
2. What are the key data quality requirements?
3. What potential issues might exist?

Provide a brief analysis (3-4 sentences)."""

        try:
            response = self.llm.invoke(fallback_prompt)
            return response.content.strip()
        except Exception as e:
            return f"Fallback assessment: Unable to validate data quality. Error: {str(e)}. Conservative estimate based on typical A/B test requirements."

    def _score_analysis(
        self,
        analysis: str,
        method: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Score the data quality analysis.

        Args:
            analysis: Analysis text from tool or LLM
            method: Method used ('tool' or 'llm_fallback')
            context: A/B test context

        Returns:
            Dict with score and reasoning
        """
        scoring_prompt = f"""You are a data quality expert. Review the following data analysis and assign a score from 0-100.

Analysis Method: {method}
Analysis Output:
{analysis}

A/B Test Context:
- Hypothesis: {context.get('hypothesis', 'N/A')}
- Success Metrics: {context.get('success_metrics', [])}
- Expected Effect Size: {context.get('expected_effect_size', 'N/A')}

Scoring Criteria:
- Data Completeness: Is the data sufficient? (30 points)
- Data Quality: Are there excessive missing values or errors? (30 points)
- Data Types: Are data types appropriate? (20 points)
- Sample Size: Is the sample size adequate for the effect size? (20 points)

If the analysis was done via LLM fallback (not tool), cap the maximum score at 70.

Respond in this format:
Score: <number>
Reasoning: <brief explanation>
Details: completeness=<score>, quality=<score>, types=<score>, sample_size=<score>"""

        try:
            response = self.llm.invoke(scoring_prompt)
            content = response.content.strip()

            # Parse the response
            lines = content.split('\n')
            score = 50.0  # Default
            reasoning = "Unable to parse scoring response"
            details = {}

            for line in lines:
                if line.startswith("Score:"):
                    try:
                        score = float(line.split("Score:")[1].strip())
                    except:
                        pass
                elif line.startswith("Reasoning:"):
                    reasoning = line.split("Reasoning:")[1].strip()
                elif line.startswith("Details:"):
                    # Parse details
                    detail_str = line.split("Details:")[1].strip()
                    for item in detail_str.split(','):
                        if '=' in item:
                            key, val = item.split('=')
                            try:
                                details[key.strip()] = float(val.strip())
                            except:
                                pass

            # Cap score at 70 for LLM fallback
            if method == "llm_fallback" and score > 70:
                score = 70.0
                reasoning += " (capped at 70 due to LLM fallback method)"

            return {
                "score": score,
                "reasoning": reasoning,
                "details": details
            }

        except Exception as e:
            # Conservative fallback scoring
            fallback_score = 60.0 if method == "llm_fallback" else 50.0
            return {
                "score": fallback_score,
                "reasoning": f"Scoring error: {str(e)}. Conservative estimate provided.",
                "details": {}
            }

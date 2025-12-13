"""
Statistical Validation Agent

Validates statistical rigor including power analysis, p-values, and effect sizes.
Uses Python tools (statsmodels, scipy) first, with LLM fallback if tool execution fails.
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


class StatisticalValidationAgent(BaseAgent):
    """
    Statistical Validation Agent (Real Implementation)

    Validates statistical rigor of the A/B test:
    - Statistical power analysis
    - Sample size adequacy
    - Effect size validation
    - Significance level checks

    Strategy:
    1. Attempt to use Python tools (statsmodels, scipy) for accurate calculations
    2. Fallback to LLM-based heuristic assessment if tools fail
    """

    def __init__(self, agent_id: str = "stats_val_agent"):
        """Initialize the statistical validation agent."""
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
        Process statistical validation request.

        Args:
            message: Incoming A2A request message

        Returns:
            A2AMessage: Response with validation score and details
        """
        ab_test_context = message.data.get("ab_test_context", {})
        dataset_path = ab_test_context.get("dataset_path", "")
        expected_effect_size = ab_test_context.get("expected_effect_size", 0.05)
        significance_level = ab_test_context.get("significance_level", 0.05)
        target_power = ab_test_context.get("power", 0.80)

        logger.info(f"Starting statistical validation - Dataset: {dataset_path}, Effect: {expected_effect_size}, Power: {target_power}")

        tool_result = self._validate_with_tool(
            dataset_path,
            expected_effect_size,
            significance_level,
            target_power,
            ab_test_context
        )

        if tool_result["success"]:
            logger.info("Tool execution successful, using tool-based analysis")
            analysis = tool_result["output"]
            method = "tool"
        else:
            logger.warning(f"Tool execution failed: {tool_result['error']}")
            logger.info("Falling back to LLM heuristic assessment")
            analysis = self._fallback_to_llm(
                ab_test_context,
                expected_effect_size,
                significance_level,
                target_power,
                tool_result["error"]
            )
            method = "llm_fallback"

        score_result = self._score_analysis(
            analysis,
            method,
            target_power,
            ab_test_context
        )

        logger.info(f"Statistical validation completed - Score: {score_result['score']:.1f}, Method: {method}")

        # Prepare result data
        result_data = {
            "score": score_result["score"],
            "validation_type": "statistical_validation",
            "method": method,
            "analysis": analysis,
            "reasoning": score_result["reasoning"],
            "checks_performed": [
                "power_analysis",
                "sample_size_check",
                "effect_size_validation",
                "significance_level_check"
            ],
            "tool_success": tool_result["success"],
            "details": score_result.get("details", {}),
            "feedback": score_result.get("feedback", {})
        }

        return self.create_response(
            message,
            result_data,
            MessageStatus.COMPLETED
        )

    def _validate_with_tool(
        self,
        dataset_path: str,
        effect_size: float,
        alpha: float,
        target_power: float,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate statistics using Python tools (statsmodels, scipy).

        Args:
            dataset_path: Path to the dataset
            effect_size: Expected effect size
            alpha: Significance level
            target_power: Target statistical power
            context: A/B test context

        Returns:
            Dict with success status and output/error
        """
        # Generate Python code for statistical analysis
        code_prompt = f"""Generate Python code to perform statistical power analysis for an A/B test.

Dataset: {dataset_path}
Expected Effect Size: {effect_size}
Significance Level (alpha): {alpha}
Target Power: {target_power}

The code should:
1. Import necessary libraries (pandas, statsmodels.stats.power, scipy.stats)
2. Load the dataset to determine sample size
3. Calculate statistical power using statsmodels.stats.power.TTestIndPower
4. Compare calculated power against target power ({target_power})
5. Print results including: sample_size, calculated_power, power_adequate (True/False)

Respond with ONLY the Python code, no explanations."""

        try:
            response = self.llm.invoke(code_prompt)
            generated_code = response.content.strip()

            # Clean code (remove markdown if present)
            if "```python" in generated_code:
                generated_code = generated_code.split("```python")[1].split("```")[0].strip()
            elif "```" in generated_code:
                generated_code = generated_code.split("```")[1].split("```")[0].strip()

            logger.debug(f"Generated statistical analysis code: {len(generated_code)} characters")

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
        context: Dict[str, Any],
        effect_size: float,
        alpha: float,
        target_power: float,
        tool_error: str
    ) -> str:
        """
        Fallback to LLM-based heuristic assessment.

        Args:
            context: A/B test context
            effect_size: Expected effect size
            alpha: Significance level
            target_power: Target statistical power
            tool_error: Error from tool execution

        Returns:
            str: LLM-generated analysis
        """
        fallback_prompt = f"""You are a statistical expert. The automated tool failed to perform power analysis, but you need to provide a heuristic assessment.

A/B Test Details:
- Hypothesis: {context.get('hypothesis', 'N/A')}
- Success Metrics: {context.get('success_metrics', [])}
- Expected Effect Size: {effect_size}
- Significance Level (alpha): {alpha}
- Target Power: {target_power}

Tool Error: {tool_error}

Based on the experimental design parameters, provide a heuristic assessment of the statistical rigor. Consider:
1. Is the expected effect size ({effect_size}) reasonable for the hypothesis?
2. Is the significance level ({alpha}) appropriate?
3. Is the target power ({target_power}) adequate?
4. What are the statistical validity concerns?

Provide a brief analysis (3-4 sentences) of the statistical design quality."""

        try:
            response = self.llm.invoke(fallback_prompt)
            return response.content.strip()
        except Exception as e:
            return f"Fallback assessment: Unable to validate statistical rigor. Error: {str(e)}. Conservative estimate based on typical A/B test standards."

    def _score_analysis(
        self,
        analysis: str,
        method: str,
        target_power: float,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Score the statistical validation analysis.

        Args:
            analysis: Analysis text from tool or LLM
            method: Method used ('tool' or 'llm_fallback')
            target_power: Target statistical power
            context: A/B test context

        Returns:
            Dict with score and reasoning
        """
        scoring_prompt = f"""You are a statistical expert. Review the following statistical analysis and assign a score from 0-100.

Analysis Method: {method}
Analysis Output:
{analysis}

A/B Test Context:
- Hypothesis: {context.get('hypothesis', 'N/A')}
- Expected Effect Size: {context.get('expected_effect_size', 'N/A')}
- Target Power: {target_power}
- Significance Level: {context.get('significance_level', 0.05)}

Scoring Criteria:
- Statistical Power: Is power >= {target_power}? (40 points)
- Sample Size: Is sample size adequate for effect size? (30 points)
- Effect Size: Is effect size realistic and detectable? (20 points)
- Experimental Design: Are statistical assumptions valid? (10 points)

If the analysis was done via LLM fallback (not tool), cap the maximum score at 75.

Respond in this format:
Score: <number>
Reasoning: <brief explanation>
Details: power=<score>, sample_size=<score>, effect_size=<score>, design=<score>
Feedback_Power: <exactly 2 sentences explaining why the power score was given>
Feedback_SampleSize: <exactly 2 sentences explaining why the sample_size score was given>
Feedback_EffectSize: <exactly 2 sentences explaining why the effect_size score was given>
Feedback_Design: <exactly 2 sentences explaining why the design score was given>"""

        try:
            response = self.llm.invoke(scoring_prompt)
            content = response.content.strip()

            # Parse the response
            lines = content.split('\n')
            score = 50.0  # Default
            reasoning = "Unable to parse scoring response"
            details = {}
            feedback = {}

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
                elif line.startswith("Feedback_Power:"):
                    feedback["power"] = line.split("Feedback_Power:")[1].strip()
                elif line.startswith("Feedback_SampleSize:"):
                    feedback["sample_size"] = line.split("Feedback_SampleSize:")[1].strip()
                elif line.startswith("Feedback_EffectSize:"):
                    feedback["effect_size"] = line.split("Feedback_EffectSize:")[1].strip()
                elif line.startswith("Feedback_Design:"):
                    feedback["design"] = line.split("Feedback_Design:")[1].strip()

            # Cap score at 75 for LLM fallback
            if method == "llm_fallback" and score > 75:
                score = 75.0
                reasoning += " (capped at 75 due to LLM fallback method)"

            return {
                "score": score,
                "reasoning": reasoning,
                "details": details,
                "feedback": feedback
            }

        except Exception as e:
            # Conservative fallback scoring
            fallback_score = 65.0 if method == "llm_fallback" else 55.0
            return {
                "score": fallback_score,
                "reasoning": f"Scoring error: {str(e)}. Conservative estimate provided.",
                "details": {}
            }

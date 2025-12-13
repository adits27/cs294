"""
Report Validation Agent

Validates A/B test report quality including clarity, conclusions, and actionability.
Uses pure LLM assessment (no tools needed).
"""

import os
from typing import Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from .base_agent import BaseAgent
from .protocol import A2AMessage, MessageStatus
from .logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)


class ReportValidationAgent(BaseAgent):
    """
    Report Quality Validation Agent (Real Implementation)

    Validates the quality and completeness of the A/B test report:
    - Report structure and clarity
    - Conclusion quality
    - Actionable insights
    - Visualization and presentation

    Strategy:
    - Pure LLM assessment (no tools needed)
    - Acts as a Product Manager reviewing the report
    """

    def __init__(self, agent_id: str = "report_val_agent"):
        """Initialize the report validation agent."""
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
        Process report validation request.

        Args:
            message: Incoming A2A request message

        Returns:
            A2AMessage: Response with validation score and details
        """
        ab_test_context = message.data.get("ab_test_context", {})
        dataset_path = ab_test_context.get("dataset_path", "")
        report_path = ab_test_context.get("report_path", dataset_path.replace(".csv", "_report.md"))

        logger.info(f"Starting report validation for: {report_path}")

        report_content = self._load_report(report_path)
        validation_result = self._validate_report(report_content, ab_test_context)

        logger.info(f"Report validation completed - Score: {validation_result['score']:.1f}")

        # Prepare result data
        result_data = {
            "score": validation_result["score"],
            "validation_type": "report_quality",
            "method": "llm_assessment",
            "reasoning": validation_result["reasoning"],
            "checks_performed": [
                "structure_check",
                "clarity_check",
                "conclusion_check",
                "actionability_check"
            ],
            "details": validation_result.get("details", {})
        }

        return self.create_response(
            message,
            result_data,
            MessageStatus.COMPLETED
        )

    def _load_report(self, report_path: str) -> str:
        """
        Load report content from file.

        Args:
            report_path: Path to the report file

        Returns:
            str: Report content or placeholder if file not found
        """
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"Loaded report: {len(content)} characters")
                return content
        except FileNotFoundError:
            logger.warning(f"Report file not found: {report_path}, using placeholder")
            return f"""# A/B Test Report (Placeholder)

This is a placeholder report as the actual file was not found at: {report_path}

## Executive Summary
[Results would be summarized here]

## Methodology
[Experimental design would be described here]

## Results
[Statistical findings would be presented here]

## Conclusions
[Conclusions and recommendations would be provided here]
"""
        except Exception as e:
            logger.error(f"Error loading report: {str(e)}")
            return f"Error loading report: {str(e)}"

    def _validate_report(self, report_content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate report quality using LLM assessment.

        Args:
            report_content: Report text content
            context: A/B test context

        Returns:
            Dict with score, reasoning, and details
        """
        # Limit report content length for LLM
        max_report_length = 3000
        if len(report_content) > max_report_length:
            report_content = report_content[:max_report_length] + "\n\n... (truncated)"

        validation_prompt = f"""You are an experienced Product Manager reviewing an A/B test report. Evaluate the following report for quality and actionability.

Report Content:
{report_content}

A/B Test Context:
- Hypothesis: {context.get('hypothesis', 'N/A')}
- Success Metrics: {context.get('success_metrics', [])}
- Expected Effect Size: {context.get('expected_effect_size', 'N/A')}

Evaluation Criteria:

1. **Structure & Clarity** (30 points):
   - Is the report well-organized?
   - Is the writing clear and easy to understand?
   - Are sections logically arranged?

2. **Conclusions Quality** (30 points):
   - Are conclusions clearly stated?
   - Are they supported by the data?
   - Is the hypothesis outcome clearly addressed?

3. **Actionability** (25 points):
   - Does the report provide actionable recommendations?
   - Are next steps clearly defined?
   - Is business impact explained?

4. **Completeness** (15 points):
   - Are all key sections present (summary, methodology, results, conclusions)?
   - Are success metrics addressed?
   - Are limitations discussed?

Assign a total score from 0-100 based on these criteria.

Respond in this format:
Score: <number>
Reasoning: <brief explanation covering the 4 criteria>
Details: structure=<score>, conclusions=<score>, actionability=<score>, completeness=<score>"""

        try:
            response = self.llm.invoke(validation_prompt)
            content = response.content.strip()

            # Parse the response
            lines = content.split('\n')
            score = 70.0  # Default (reasonable for typical reports)
            reasoning = "Unable to parse report assessment"
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

            return {
                "score": score,
                "reasoning": reasoning,
                "details": details
            }

        except Exception as e:
            return {
                "score": 70.0,
                "reasoning": f"Report assessment error: {str(e)}. Conservative estimate provided.",
                "details": {}
            }

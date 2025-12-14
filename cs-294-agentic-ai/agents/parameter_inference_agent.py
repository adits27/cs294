"""
Parameter Inference Agent

This agent extracts A/B test parameters from the provided files:
- Hypothesis from report or code comments
- Success metrics from code or dataset columns
- Expected effect size from code or report
- Significance level from code (default: 0.05)
- Power from code (default: 0.80)
"""

import logging
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

from .base_agent import BaseAgent
from .protocol import A2AMessage, MessageStatus

# Configure logging
logger = logging.getLogger(__name__)


class ParameterInferenceAgent(BaseAgent):
    """
    Agent that infers A/B test parameters from files.

    This agent analyzes the provided dataset, code, and report files to extract:
    - Hypothesis
    - Success metrics
    - Expected effect size
    - Significance level
    - Statistical power
    """

    def __init__(self, agent_id: str = "param_inference_agent", model_name: str = "gemini-2.0-flash-lite"):
        """Initialize the parameter inference agent"""
        super().__init__(agent_id)
        self.model_name = model_name
        self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.0)

    def _read_file_safe(self, file_path: str) -> Optional[str]:
        """Safely read a file and return its contents"""
        if not file_path or file_path == "":
            return None

        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found: {file_path}")
                return None

            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return None

    def _read_multiple_files(self, file_paths: List[str], file_type: str, max_lines_per_file: int = 50) -> str:
        """Read multiple files and concatenate their contents"""
        if not file_paths:
            return ""

        parts = []
        for i, file_path in enumerate(file_paths, 1):
            content = self._read_file_safe(file_path)
            if content:
                # For data files, limit lines
                if file_type == "data":
                    lines = content.split('\n')[:max_lines_per_file]
                    content = '\n'.join(lines)
                    if len(content.split('\n')) >= max_lines_per_file:
                        content += "\n... (truncated)"

                parts.append(f"--- {file_type.upper()} FILE {i}: {Path(file_path).name} ---\n{content}")

        return "\n\n".join(parts) if parts else ""

    def _infer_from_files(self, data_files: List[str], code_files: List[str], report_files: List[str]) -> Dict[str, Any]:
        """Use LLM to infer parameters from file contents (supports multiple files per category)"""

        # Read all files
        data_content = self._read_multiple_files(data_files, "data", max_lines_per_file=20)
        code_content = self._read_multiple_files(code_files, "code")
        report_content = self._read_multiple_files(report_files, "report")

        # Build context for LLM
        context_parts = []

        if data_content:
            context_parts.append(f"DATA FILES:\n{data_content}")

        if code_content:
            context_parts.append(f"CODE FILES:\n{code_content}")

        if report_content:
            context_parts.append(f"REPORT FILES:\n{report_content}")

        if not context_parts:
            raise ValueError("No valid files provided for parameter inference")

        context = "\n\n" + "="*80 + "\n\n".join(context_parts)

        # Create prompt for LLM
        prompt = f"""You are analyzing A/B test files to extract key parameters.

{context}

Based on the files above, extract the following parameters:

1. **Hypothesis**: The main hypothesis being tested (what change is being tested and what outcome is expected)
2. **Success Metrics**: List of metric names that measure success (e.g., conversion_rate, revenue, etc.)
3. **Expected Effect Size**: The minimum detectable effect or expected effect size (as a decimal, e.g., 0.05 for 5%)
4. **Significance Level**: The alpha level for statistical testing (typically 0.05)
5. **Power**: The statistical power level (typically 0.80)

IMPORTANT INSTRUCTIONS:
- Look for the hypothesis in the report introduction, code comments, or variable names
- Extract success metrics from code variable names, function parameters, or report sections
- Find effect size in power analysis code, sample size calculations, or report methodology
- Look for significance level (alpha) in statistical test code or report methods
- Look for power (1-beta) in power analysis or sample size calculations
- If you cannot find a parameter, use reasonable defaults:
  - Expected effect size: 0.05 (5%)
  - Significance level: 0.05
  - Power: 0.80

Return your response in the following JSON format:
{{
  "hypothesis": "string describing the hypothesis",
  "success_metrics": ["metric1", "metric2"],
  "expected_effect_size": 0.05,
  "significance_level": 0.05,
  "power": 0.80,
  "confidence": "high/medium/low",
  "reasoning": "brief explanation of how you extracted each parameter"
}}

Response:"""

        # Get LLM response
        try:
            response = self.llm.invoke(prompt)
            response_text = response.content

            # Extract JSON from response (handle markdown code blocks)
            import json

            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group(0))
                return result
            else:
                raise ValueError("Could not extract JSON from LLM response")

        except Exception as e:
            logger.error(f"Error during LLM inference: {str(e)}")
            # Return defaults if inference fails
            return {
                "hypothesis": "A/B test hypothesis (could not infer from files)",
                "success_metrics": ["conversion_rate"],
                "expected_effect_size": 0.05,
                "significance_level": 0.05,
                "power": 0.80,
                "confidence": "low",
                "reasoning": f"Failed to infer parameters: {str(e)}. Using defaults."
            }

    def process_request(self, message: A2AMessage) -> A2AMessage:
        """
        Process parameter inference request.

        Expected message.data format:
        {
            "ab_test_context": ABTestContext object with data_source, code_source, report_source
        }
        OR legacy format:
        {
            "dataset_path": "path/to/dataset.csv",
            "code_path": "path/to/code.py",
            "report_path": "path/to/report.md"
        }
        """
        try:
            # Get ABTestContext from message data
            ab_test_context = message.data.get("ab_test_context")

            if ab_test_context:
                # New format: use ABTestContext to get all files
                data_files = ab_test_context.get_all_files('data')
                code_files = ab_test_context.get_all_files('code')
                report_files = ab_test_context.get_all_files('report')
            else:
                # Legacy format: single file paths
                dataset_path = message.data.get("dataset_path", "")
                code_path = message.data.get("code_path", "")
                report_path = message.data.get("report_path", "")

                data_files = [dataset_path] if dataset_path else []
                code_files = [code_path] if code_path else []
                report_files = [report_path] if report_path else []

            logger.info(f"Inferring parameters from files:")
            logger.info(f"  Data files: {len(data_files)} file(s)")
            logger.info(f"  Code files: {len(code_files)} file(s)")
            logger.info(f"  Report files: {len(report_files)} file(s)")

            # Infer parameters
            inferred_params = self._infer_from_files(data_files, code_files, report_files)

            # Create response
            response = self.create_response(
                original_message=message,
                result_data={
                    "inferred_parameters": inferred_params,
                    "method": "llm_inference",
                    "message": "Successfully inferred A/B test parameters from provided files"
                },
                status=MessageStatus.COMPLETED
            )

            logger.info(f"✓ Parameter inference completed")
            logger.info(f"  Hypothesis: {inferred_params.get('hypothesis', '')[:80]}...")
            logger.info(f"  Metrics: {inferred_params.get('success_metrics', [])}")
            logger.info(f"  Effect Size: {inferred_params.get('expected_effect_size', 0.0)}")
            logger.info(f"  Confidence: {inferred_params.get('confidence', 'unknown')}")

            return response

        except Exception as e:
            logger.error(f"Parameter inference failed: {str(e)}")
            return self.create_response(
                original_message=message,
                result_data={"error": str(e)},
                status=MessageStatus.FAILED
            )

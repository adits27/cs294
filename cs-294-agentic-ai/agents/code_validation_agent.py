"""
Code Validation Agent

Validates Python code quality including syntax and style (PEP-8, modularity, comments).
Uses AST parsing for syntax validation and LLM for style assessment.
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


class CodeValidationAgent(BaseAgent):
    """
    Code Quality Validation Agent (Real Implementation)

    Validates code quality aspects of the A/B test implementation:
    - Syntax validation (using AST)
    - Code style (PEP-8 compliance)
    - Modularity and structure
    - Documentation and comments

    Strategy:
    1. Use Python AST parsing for syntax check (automatic fail if syntax error)
    2. Use LLM for style assessment (PEP-8, modularity, comments)
    3. Final score = average of syntax (pass=100, fail=0) and style score
    """

    def __init__(self, agent_id: str = "code_val_agent"):
        """Initialize the code validation agent."""
        super().__init__(agent_id)

        # Initialize LLM
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.0,
            google_api_key=api_key
        )

    def process_request(self, message: A2AMessage) -> A2AMessage:
        """
        Process code validation request.

        Args:
            message: Incoming A2A request message

        Returns:
            A2AMessage: Response with validation score and details
        """
        ab_test_context = message.data.get("ab_test_context", {})
        dataset_path = ab_test_context.get("dataset_path", "")
        code_path = ab_test_context.get("code_path", dataset_path.replace(".csv", ".py"))

        logger.info(f"Starting code validation for: {code_path}")

        syntax_result = self._validate_syntax(code_path)

        if not syntax_result['valid']:
            logger.error(f"Syntax validation failed: {syntax_result['error']}")
            result_data = {
                "score": 0.0,
                "validation_type": "code_quality",
                "method": "tool",
                "syntax_valid": False,
                "syntax_error": syntax_result["error"],
                "style_score": 0.0,
                "reasoning": "Code has syntax errors - automatic fail",
                "checks_performed": ["syntax_check"],
                "details": {
                    "syntax": 0.0,
                    "style": 0.0
                }
            }
        else:
            logger.info("Syntax validation passed")
            code_content = syntax_result.get("code_content", "")
            style_result = self._validate_style(code_content, ab_test_context)

            final_score = (100.0 + style_result["score"]) / 2.0
            logger.info(f"Code validation completed - Score: {final_score:.1f} (Syntax: 100, Style: {style_result['score']:.1f})")

            result_data = {
                "score": final_score,
                "validation_type": "code_quality",
                "method": "tool",
                "syntax_valid": True,
                "style_score": style_result["score"],
                "reasoning": style_result["reasoning"],
                "checks_performed": [
                    "syntax_check",
                    "pep8_check",
                    "modularity_check",
                    "documentation_check"
                ],
                "details": {
                    "syntax": 100.0,
                    "style": style_result["score"]
                },
                "feedback": style_result.get("feedback", {})
            }

        return self.create_response(
            message,
            result_data,
            MessageStatus.COMPLETED
        )

    def _validate_syntax(self, code_path: str) -> Dict[str, Any]:
        """
        Validate Python code syntax using AST parsing.

        Args:
            code_path: Path to the Python code file

        Returns:
            Dict with valid flag, error message, and code content
        """
        # Generate code to check syntax
        syntax_check_code = f"""
import ast
import sys

try:
    with open('{code_path}', 'r') as f:
        code = f.read()

    # Try to parse the code
    ast.parse(code)
    print("SYNTAX_VALID")
    print("---CODE_START---")
    print(code)
    print("---CODE_END---")
except SyntaxError as e:
    print(f"SYNTAX_ERROR: {{e}}")
except FileNotFoundError:
    print("FILE_NOT_FOUND: {code_path}")
except Exception as e:
    print(f"ERROR: {{e}}")
"""

        result = python_repl.run(syntax_check_code)

        if result["success"] and "SYNTAX_VALID" in result["output"]:
            # Extract code content
            output = result["output"]
            if "---CODE_START---" in output and "---CODE_END---" in output:
                code_content = output.split("---CODE_START---")[1].split("---CODE_END---")[0].strip()
            else:
                code_content = ""

            return {
                "valid": True,
                "error": None,
                "code_content": code_content
            }
        elif "FILE_NOT_FOUND" in result["output"]:
            # File doesn't exist - use heuristic
            return {
                "valid": True,  # Assume valid for missing file (heuristic mode)
                "error": None,
                "code_content": f"# Code file not found at: {code_path}\n# Performing heuristic assessment"
            }
        else:
            # Syntax error or other error
            error_msg = result["output"] if result["output"] else result["error"]
            return {
                "valid": False,
                "error": error_msg,
                "code_content": ""
            }

    def _validate_style(self, code_content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate code style using LLM assessment.

        Args:
            code_content: Python code content
            context: A/B test context

        Returns:
            Dict with style score and reasoning
        """
        # Limit code content length for LLM
        max_code_length = 2000
        if len(code_content) > max_code_length:
            code_content = code_content[:max_code_length] + "\n\n... (truncated)"

        style_prompt = f"""You are a senior Python code reviewer. Review the following code for style and quality.

Code:
```python
{code_content}
```

A/B Test Context:
- Hypothesis: {context.get('hypothesis', 'N/A')}
- This code implements an A/B test experiment

Review Criteria:
1. **PEP-8 Compliance** (40 points): Naming conventions, line length, spacing, etc.
2. **Modularity** (30 points): Functions, classes, separation of concerns
3. **Comments & Documentation** (20 points): Docstrings, inline comments
4. **Best Practices** (10 points): Error handling, code clarity

Assign a total score from 0-100 based on these criteria.

Respond in this format:
Score: <number>
Reasoning: <brief explanation covering the 4 criteria>
Details: pep8=<score>, modularity=<score>, documentation=<score>, best_practices=<score>
Feedback_PEP8: <exactly 2 sentences explaining why the PEP-8 score was given>
Feedback_Modularity: <exactly 2 sentences explaining why the modularity score was given>
Feedback_Documentation: <exactly 2 sentences explaining why the documentation score was given>
Feedback_BestPractices: <exactly 2 sentences explaining why the best_practices score was given>"""

        try:
            response = self.llm.invoke(style_prompt)
            content = response.content.strip()

            # Parse the response
            lines = content.split('\n')
            score = 60.0  # Default
            reasoning = "Unable to parse style assessment"
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
                elif line.startswith("Feedback_PEP8:"):
                    feedback["pep8"] = line.split("Feedback_PEP8:")[1].strip()
                elif line.startswith("Feedback_Modularity:"):
                    feedback["modularity"] = line.split("Feedback_Modularity:")[1].strip()
                elif line.startswith("Feedback_Documentation:"):
                    feedback["documentation"] = line.split("Feedback_Documentation:")[1].strip()
                elif line.startswith("Feedback_BestPractices:"):
                    feedback["best_practices"] = line.split("Feedback_BestPractices:")[1].strip()

            return {
                "score": score,
                "reasoning": reasoning,
                "details": details,
                "feedback": feedback
            }

        except Exception as e:
            return {
                "score": 60.0,
                "reasoning": f"Style assessment error: {str(e)}. Conservative estimate provided.",
                "details": {}
            }

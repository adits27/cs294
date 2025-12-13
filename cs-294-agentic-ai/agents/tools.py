"""
Python REPL Tool for Code Execution

Provides a safe Python code execution environment with timeout and
error handling for quantitative validation agents.
"""

import subprocess
import sys
from typing import Dict

from .logger import setup_logger

logger = setup_logger(__name__)


class PythonRepl:
    """
    A Python REPL (Read-Eval-Print Loop) tool for executing Python code.

    Executes Python code in a subprocess with timeout and proper error handling.
    Used by quantitative agents (Data and Statistical) to run validation code.
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize the Python REPL tool.

        Args:
            timeout: Maximum execution time in seconds (default: 30)
        """
        self.timeout = timeout

    def run(self, code: str) -> Dict[str, any]:
        """
        Execute Python code and return the result.

        Args:
            code: Python code to execute

        Returns:
            Dict with keys:
                - success (bool): Whether execution succeeded
                - output (str): Standard output from execution
                - error (str): Error message if any
        """
        logger.debug(f"Executing Python code ({len(code)} characters)")

        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            success = result.returncode == 0 and not result.stderr

            if success:
                logger.debug("Code execution successful")
            else:
                logger.warning(f"Code execution failed with return code {result.returncode}")

            return {
                "success": success,
                "output": result.stdout.strip() if result.stdout else "",
                "error": result.stderr.strip() if result.stderr else ""
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Code execution timed out after {self.timeout} seconds")
            return {
                "success": False,
                "output": "",
                "error": f"Execution timed out after {self.timeout} seconds"
            }

        except Exception as e:
            logger.error(f"Code execution error: {str(e)}")
            return {
                "success": False,
                "output": "",
                "error": f"Execution error: {str(e)}"
            }

    def run_with_fallback(self, code: str, fallback_message: str = None) -> Dict[str, any]:
        """
        Execute code with automatic fallback handling.

        Args:
            code: Python code to execute
            fallback_message: Message to include if execution fails

        Returns:
            Dict with execution result and fallback flag
        """
        result = self.run(code)

        if not result["success"] and fallback_message:
            result["fallback_message"] = fallback_message

        return result


# Global instance for convenience
python_repl = PythonRepl()

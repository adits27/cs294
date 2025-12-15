"""
State Management for Multi-Agent A/B Testing System

This module defines the shared state and context schemas used across
all agents in the validation and assessment pipeline.
"""

from typing import Annotated, Any, Dict, List, TypedDict
from operator import add
from pathlib import Path
import glob as glob_module

from pydantic import BaseModel, Field, model_validator

from .protocol import A2AMessage


def merge_dicts(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with right values taking precedence.

    Used as a reducer for ValidationState.validation_results to handle
    concurrent updates from parallel agent nodes.

    For nested dictionaries (like agent_responses), this merges them
    instead of overwriting.
    """
    result = left.copy()

    for key, value in right.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Deep merge nested dictionaries
            result[key] = {**result[key], **value}
        else:
            # Override with right value
            result[key] = value

    return result


class ABTestContext(BaseModel):
    """
    Context information for an A/B test validation task.

    This schema captures all the essential parameters and metadata
    needed to validate an A/B test experiment.

    Parameters can be inferred from files if not provided explicitly.

    Supports folder patterns:
    - Single file: "path/to/file.csv"
    - Folder pattern: "results/result_1_1/*" (discovers data_source/, code/, report/ subdirs)
    - Specific folder: "results/result_1_1/data_source/*" (all files in folder)
    """
    data_source: str = Field(
        ...,
        description="Path to data files. Can be a file path, folder path, or folder/* pattern (REQUIRED)"
    )
    code_source: str = Field(
        default="",
        description="Path to code files. Can be a file path, folder path, or folder/* pattern (optional)"
    )
    report_source: str = Field(
        default="",
        description="Path to report files. Can be a file path, folder path, or folder/* pattern (optional)"
    )

    # Legacy field names for backward compatibility
    dataset_path: str = Field(
        default="",
        description="[DEPRECATED] Use data_source instead"
    )
    code_path: str = Field(
        default="",
        description="[DEPRECATED] Use code_source instead"
    )
    report_path: str = Field(
        default="",
        description="[DEPRECATED] Use report_source instead"
    )
    hypothesis: str = Field(
        default="",
        description="The hypothesis being tested (inferred from files if not provided)"
    )
    success_metrics: List[str] = Field(
        default_factory=list,
        description="List of metrics used to measure success (inferred from files if not provided)"
    )
    expected_effect_size: float = Field(
        default=0.05,
        description="Expected effect size for the test (inferred from files if not provided, default: 0.05)"
    )
    significance_level: float = Field(
        default=0.05,
        description="Statistical significance level (alpha) for hypothesis testing (default: 0.05)"
    )
    power: float = Field(
        default=0.80,
        description="Statistical power (1 - beta) for the test (default: 0.80)"
    )

    @model_validator(mode='after')
    def resolve_paths(self):
        """
        Resolve folder patterns and handle backward compatibility.

        - If legacy fields (dataset_path, code_path, report_path) are used, map to new fields
        - If folder/* pattern is used, auto-discover subdirectories (data_source, code, report)
        - Expand glob patterns to find actual files
        - Supports both local paths and R2 paths
        """
        # Handle backward compatibility: map old field names to new ones
        if self.dataset_path and not self.data_source:
            self.data_source = self.dataset_path
        if self.code_path and not self.code_source:
            self.code_source = self.code_path
        if self.report_path and not self.report_source:
            self.report_source = self.report_path

        # Auto-discover subdirectories if folder/* pattern is used
        if self.data_source and self.data_source.endswith('/*'):
            base_folder = self.data_source[:-2]  # Remove /*

            # Check if this is an R2 path or local path
            from .storage import is_r2_path, get_r2_storage

            if is_r2_path(base_folder):
                # R2 path - check for subdirectories in R2
                r2 = get_r2_storage()
                if r2.is_configured():
                    try:
                        # Normalize R2 prefix
                        r2_prefix = base_folder
                        if r2_prefix.startswith('r2://') or r2_prefix.startswith('s3://'):
                            parts = r2_prefix.split('/', 3)
                            if len(parts) >= 4:
                                r2_prefix = parts[3]

                        # Ensure prefix ends with /
                        if not r2_prefix.endswith('/'):
                            r2_prefix += '/'

                        # List objects to check for subdirectories
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f"Auto-discovery: Listing R2 subdirectories with prefix: {r2_prefix}")

                        response = r2.client.list_objects_v2(
                            Bucket=r2.bucket,
                            Prefix=r2_prefix,
                            Delimiter='/'
                        )

                        # Get common prefixes (subdirectories)
                        if 'CommonPrefixes' in response:
                            subdirs = [prefix['Prefix'] for prefix in response['CommonPrefixes']]
                            logger.info(f"Auto-discovery: Found {len(subdirs)} subdirectories: {subdirs}")

                            # Auto-discover data_source subfolder
                            data_subdir = f"{r2_prefix}data_source/"
                            if data_subdir in subdirs:
                                self.data_source = f"{base_folder}/data_source/*"
                                logger.info(f"Auto-discovery: Set data_source to {self.data_source}")

                            # Auto-discover code subfolder if not explicitly set
                            if not self.code_source:
                                code_subdir = f"{r2_prefix}code/"
                                if code_subdir in subdirs:
                                    self.code_source = f"{base_folder}/code/*"
                                    logger.info(f"Auto-discovery: Set code_source to {self.code_source}")

                            # Auto-discover report subfolder if not explicitly set
                            if not self.report_source:
                                report_subdir = f"{r2_prefix}report/"
                                if report_subdir in subdirs:
                                    self.report_source = f"{base_folder}/report/*"
                                    logger.info(f"Auto-discovery: Set report_source to {self.report_source}")
                        else:
                            logger.warning(f"Auto-discovery: No CommonPrefixes found in R2 response for prefix: {r2_prefix}")
                    except Exception as e:
                        # If R2 check fails, keep original paths
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Failed to auto-discover R2 subdirectories: {str(e)}")
            else:
                # Local path - use original logic
                base_path = Path(base_folder)

                # Auto-discover data_source subfolder
                data_folder = base_path / "data_source"
                if data_folder.exists():
                    self.data_source = str(data_folder / "*")

                # Auto-discover code subfolder if not explicitly set
                if not self.code_source:
                    code_folder = base_path / "code"
                    if code_folder.exists():
                        self.code_source = str(code_folder / "*")

                # Auto-discover report subfolder if not explicitly set
                if not self.report_source:
                    report_folder = base_path / "report"
                    if report_folder.exists():
                        self.report_source = str(report_folder / "*")

        return self

    def get_all_files(self, source_type: str) -> List[str]:
        """
        Get all files from a source path (supports glob patterns).

        Args:
            source_type: One of 'data', 'code', or 'report'

        Returns:
            List of file paths
        """
        source_map = {
            'data': self.data_source,
            'code': self.code_source,
            'report': self.report_source
        }

        source_path = source_map.get(source_type, "")
        if not source_path:
            return []

        # If it's a glob pattern, expand it
        if '*' in source_path:
            files = glob_module.glob(source_path)
            # Filter out directories, only return files
            return [f for f in files if Path(f).is_file()]
        else:
            # Single file path
            if Path(source_path).is_file():
                return [source_path]
            return []

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "data_source": "results/result_1_1/*",
                "expected_effect_size": 0.05,
                "significance_level": 0.05,
                "power": 0.80
            }
        }


class ValidationState(TypedDict):
    """
    Validation state for LangGraph compatibility with parallel execution support.

    This TypedDict tracks the complete state of the validation workflow,
    including task information, context, message logs, and results.

    Uses Annotated types with reducers to handle concurrent updates from
    parallel agent nodes:
    - a2a_message_log: Uses 'add' operator to append messages
    - validation_results: Uses 'merge_dicts' to merge result dictionaries
    """
    task: str
    ab_test_context: ABTestContext
    a2a_message_log: Annotated[List[A2AMessage], add]
    validation_results: Annotated[Dict[str, Any], merge_dicts]
    final_score: float
    validation_summary: str


def create_initial_state(
    task: str,
    ab_test_context: ABTestContext
) -> ValidationState:
    """
    Create an initial validation state with default values.

    Args:
        task: Description of the validation task
        ab_test_context: A/B test context information

    Returns:
        ValidationState: Initialized state dictionary
    """
    return ValidationState(
        task=task,
        ab_test_context=ab_test_context,
        a2a_message_log=[],
        validation_results={},
        final_score=0.0,
        validation_summary=""
    )


def update_validation_state(
    state: ValidationState,
    message: A2AMessage = None,
    validation_results: Dict[str, Any] = None,
    final_score: float = None,
    validation_summary: str = None
) -> ValidationState:
    """
    Update validation state with new information.

    Args:
        state: Current validation state
        message: Optional A2A message to add to log
        validation_results: Optional validation results to merge
        final_score: Optional final score to set
        validation_summary: Optional summary to set

    Returns:
        ValidationState: Updated state dictionary
    """
    updated_state = state.copy()

    if message is not None:
        updated_state["a2a_message_log"] = state["a2a_message_log"] + [message]

    if validation_results is not None:
        updated_state["validation_results"] = {
            **state["validation_results"],
            **validation_results
        }

    if final_score is not None:
        updated_state["final_score"] = final_score

    if validation_summary is not None:
        updated_state["validation_summary"] = validation_summary

    return updated_state

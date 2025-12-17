"""
Cloud Storage Integration for A/B Test Validation Agent

Supports Cloudflare R2 (S3-compatible) for reading experiment files.
"""
import os
import boto3
from typing import Optional
from pathlib import Path
import tempfile
import logging

logger = logging.getLogger(__name__)


class R2Storage:
    """Cloudflare R2 storage client (S3-compatible)"""

    # Hard-coded R2 configuration
    BUCKET_URL = "https://26fa6fc0f0d3ae54240e277c7f5583fa.r2.cloudflarestorage.com/green-agent"

    # Hard-coded file paths in R2
    CODE_FILE_PATH = "green-agent/experiment/code/analysis.py"
    DATA_CSV_PATH = "green-agent/experiment/data_source/data.csv"
    DATA_CONTEXT_PATH = "green-agent/experiment/data_source/context.txt"
    REPORT_MD_PATH = "green-agent/experiment/report/analysis_report.md"
    REPORT_JSON_PATH = "green-agent/experiment/report/results.json"

    def __init__(self):
        """Initialize R2 client from environment variables"""
        self.bucket = os.getenv("S3_BUCKET", "green-agent")
        self.access_key = os.getenv("S3_ACCESS_KEY_ID")
        self.secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL", "https://26fa6fc0f0d3ae54240e277c7f5583fa.r2.cloudflarestorage.com")
        self.public_url_base = os.getenv("S3_PUBLIC_URL_BASE")

        # Initialize S3 client if credentials are available
        self.client = None
        if all([self.bucket, self.access_key, self.secret_key, self.endpoint_url]):
            self.client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name='auto'  # Cloudflare R2 uses 'auto'
            )
            logger.info(f"R2 storage initialized for bucket: {self.bucket}")
        else:
            logger.warning("R2 storage not configured - missing environment variables")

    def is_configured(self) -> bool:
        """Check if R2 storage is properly configured"""
        return self.client is not None

    def download_file(self, r2_key: str, local_path: Optional[str] = None) -> str:
        """
        Download a file from R2 storage

        Args:
            r2_key: The R2 object key (e.g., 'experiment/data_source/data.csv')
            local_path: Optional local path to save to. If not provided, uses temp file.

        Returns:
            Path to the downloaded local file

        Raises:
            ValueError: If R2 is not configured
            Exception: If download fails
        """
        if not self.is_configured():
            raise ValueError("R2 storage is not configured. Check environment variables.")

        # Create local path if not provided
        if local_path is None:
            # Create temp file with same extension
            suffix = Path(r2_key).suffix
            fd, local_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)

        # Ensure directory exists
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Downloading {r2_key} from R2 to {local_path}")
            self.client.download_file(self.bucket, r2_key, local_path)
            logger.info(f"Successfully downloaded {r2_key}")
            return local_path
        except Exception as e:
            logger.error(f"Failed to download {r2_key}: {str(e)}")
            raise

    def download_directory(self, r2_prefix: str, local_dir: str) -> dict:
        """
        Deprecated: Download all files from an R2 directory prefix
        Use get_all_data_files() or get_all_report_files() instead for hard-coded paths

        Args:
            r2_prefix: The R2 prefix (e.g., 'experiment/data_source/')
            local_dir: Local directory to save files to

        Returns:
            Dict mapping R2 keys to local paths

        Raises:
            ValueError: If R2 is not configured
        """
        logger.warning("download_directory is deprecated. Use get_all_data_files() or get_all_report_files() instead.")
        if not self.is_configured():
            raise ValueError("R2 storage is not configured. Check environment variables.")

        # Ensure local directory exists
        Path(local_dir).mkdir(parents=True, exist_ok=True)

        # List objects with the prefix
        downloaded_files = {}

        try:
            # Ensure prefix ends with /
            if not r2_prefix.endswith('/'):
                r2_prefix += '/'

            logger.info(f"Listing objects with prefix: {r2_prefix}")
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=r2_prefix
            )

            if 'Contents' not in response:
                logger.warning(f"No objects found with prefix: {r2_prefix}")
                return downloaded_files

            for obj in response['Contents']:
                key = obj['Key']

                # Skip directory markers
                if key.endswith('/'):
                    continue

                # Get relative path (remove prefix)
                relative_path = key[len(r2_prefix):]

                # Create local path
                local_path = os.path.join(local_dir, relative_path)

                # Download file
                self.download_file(key, local_path)
                downloaded_files[key] = local_path

            logger.info(f"Downloaded {len(downloaded_files)} files from {r2_prefix}")
            return downloaded_files

        except Exception as e:
            logger.error(f"Failed to download directory {r2_prefix}: {str(e)}")
            raise

    def get_public_url(self, r2_key: str) -> Optional[str]:
        """
        Get public URL for an R2 object

        Args:
            r2_key: The R2 object key

        Returns:
            Public URL if S3_PUBLIC_URL_BASE is configured, None otherwise
        """
        if self.public_url_base:
            return f"{self.public_url_base.rstrip('/')}/{r2_key}"
        return None

    def get_code_file(self, local_path: Optional[str] = None) -> str:
        """Download the hard-coded code file (analysis.py)"""
        return self.download_file(self.CODE_FILE_PATH, local_path)

    def get_data_csv(self, local_path: Optional[str] = None) -> str:
        """Download the hard-coded data CSV file"""
        return self.download_file(self.DATA_CSV_PATH, local_path)

    def get_data_context(self, local_path: Optional[str] = None) -> str:
        """Download the hard-coded data context file"""
        return self.download_file(self.DATA_CONTEXT_PATH, local_path)

    def get_report_markdown(self, local_path: Optional[str] = None) -> str:
        """Download the hard-coded report markdown file"""
        return self.download_file(self.REPORT_MD_PATH, local_path)

    def get_report_json(self, local_path: Optional[str] = None) -> str:
        """Download the hard-coded report JSON file"""
        return self.download_file(self.REPORT_JSON_PATH, local_path)

    def get_all_data_files(self, local_dir: Optional[str] = None) -> dict:
        """
        Download all data source files (CSV and context)

        Returns:
            Dict with keys 'csv' and 'context' mapping to local file paths
        """
        if local_dir is None:
            local_dir = tempfile.mkdtemp(prefix='r2_data_')

        return {
            'csv': self.download_file(self.DATA_CSV_PATH, os.path.join(local_dir, 'data.csv')),
            'context': self.download_file(self.DATA_CONTEXT_PATH, os.path.join(local_dir, 'context.txt'))
        }

    def get_all_report_files(self, local_dir: Optional[str] = None) -> dict:
        """
        Download all report files (markdown and JSON)

        Returns:
            Dict with keys 'markdown' and 'json' mapping to local file paths
        """
        if local_dir is None:
            local_dir = tempfile.mkdtemp(prefix='r2_report_')

        return {
            'markdown': self.download_file(self.REPORT_MD_PATH, os.path.join(local_dir, 'analysis_report.md')),
            'json': self.download_file(self.REPORT_JSON_PATH, os.path.join(local_dir, 'results.json'))
        }


# Global R2 storage instance
_r2_storage = None


def get_r2_storage() -> R2Storage:
    """Get or create global R2 storage instance"""
    global _r2_storage
    if _r2_storage is None:
        _r2_storage = R2Storage()
    return _r2_storage


# Legacy functions kept for backward compatibility but simplified
def is_r2_path(path: str) -> bool:
    """
    Deprecated: Check if a path is an R2 path
    Use hard-coded methods instead (get_code_file, get_data_csv, etc.)
    """
    logger.warning("is_r2_path is deprecated. Use hard-coded storage methods instead.")
    return False


def resolve_path(path: str) -> str:
    """
    Deprecated: Resolve a path to a local file
    Use hard-coded methods instead (get_code_file, get_data_csv, etc.)
    """
    logger.warning("resolve_path is deprecated. Use hard-coded storage methods instead.")
    if os.path.exists(path):
        return path
    raise ValueError(f"Path not found: {path}. Use hard-coded R2Storage methods instead.")


def resolve_directory(path: str) -> str:
    """
    Deprecated: Resolve a directory path
    Use hard-coded methods instead (get_all_data_files, get_all_report_files, etc.)
    """
    logger.warning("resolve_directory is deprecated. Use hard-coded storage methods instead.")
    if os.path.isdir(path):
        return path
    raise ValueError(f"Directory not found: {path}. Use hard-coded R2Storage methods instead.")

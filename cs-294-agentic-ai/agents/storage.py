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

    def __init__(self):
        """Initialize R2 client from environment variables"""
        self.bucket = os.getenv("S3_BUCKET")
        self.access_key = os.getenv("S3_ACCESS_KEY_ID")
        self.secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL")
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
        Download all files from an R2 directory prefix

        Args:
            r2_prefix: The R2 prefix (e.g., 'experiment/data_source/')
            local_dir: Local directory to save files to

        Returns:
            Dict mapping R2 keys to local paths

        Raises:
            ValueError: If R2 is not configured
        """
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


# Global R2 storage instance
_r2_storage = None


def get_r2_storage() -> R2Storage:
    """Get or create global R2 storage instance"""
    global _r2_storage
    if _r2_storage is None:
        _r2_storage = R2Storage()
    return _r2_storage


def is_r2_path(path: str) -> bool:
    """
    Check if a path is an R2 path

    R2 paths can be:
    - r2://bucket/key
    - s3://bucket/key
    - experiment/data_source/data.csv (relative R2 key)
    - https://pub-xxx.r2.dev/experiment/data.csv (public URL)
    """
    if path.startswith('r2://') or path.startswith('s3://'):
        return True

    # Check if it's a public R2 URL
    r2 = get_r2_storage()
    if r2.public_url_base and path.startswith(r2.public_url_base):
        return True

    # Check if it looks like a local path
    if path.startswith('/') or path.startswith('./') or path.startswith('../'):
        return False

    # If R2 is configured and path doesn't look local, treat as R2 key
    return r2.is_configured()


def resolve_path(path: str) -> str:
    """
    Resolve a path to a local file, downloading from R2 if necessary

    Args:
        path: Can be local path, R2 key, or R2 URL

    Returns:
        Local file path

    Raises:
        ValueError: If path is invalid or R2 is not configured when needed
    """
    # If it's already a local file that exists, return it
    if os.path.exists(path):
        logger.info(f"Using existing local file: {path}")
        return path

    # Check if it's an R2 path
    if not is_r2_path(path):
        # Not R2 and doesn't exist locally
        logger.warning(f"File not found and not an R2 path: {path}")
        return path  # Return as-is, let caller handle the error

    # Handle R2 paths
    r2 = get_r2_storage()

    # Extract R2 key from different formats
    r2_key = path

    if path.startswith('r2://') or path.startswith('s3://'):
        # Format: r2://bucket/key or s3://bucket/key
        parts = path.split('/', 3)
        if len(parts) >= 4:
            r2_key = parts[3]  # Everything after bucket name
    elif r2.public_url_base and path.startswith(r2.public_url_base):
        # Format: https://pub-xxx.r2.dev/experiment/data.csv
        r2_key = path[len(r2.public_url_base):].lstrip('/')

    # Download from R2
    logger.info(f"Downloading from R2: {r2_key}")
    return r2.download_file(r2_key)


def resolve_directory(path: str) -> str:
    """
    Resolve a directory path, downloading from R2 if necessary

    Args:
        path: Can be local directory, R2 prefix, or R2 URL prefix

    Returns:
        Local directory path
    """
    # If it's already a local directory that exists, return it
    if os.path.isdir(path):
        logger.info(f"Using existing local directory: {path}")
        return path

    # Check if it's an R2 path
    if not is_r2_path(path):
        logger.warning(f"Directory not found and not an R2 path: {path}")
        return path

    # Handle R2 paths
    r2 = get_r2_storage()

    # Extract R2 prefix
    r2_prefix = path
    if path.startswith('r2://') or path.startswith('s3://'):
        parts = path.split('/', 3)
        if len(parts) >= 4:
            r2_prefix = parts[3]
    elif r2.public_url_base and path.startswith(r2.public_url_base):
        r2_prefix = path[len(r2.public_url_base):].lstrip('/')

    # Create temp directory for downloads
    local_dir = tempfile.mkdtemp(prefix='r2_download_')

    # Download directory
    logger.info(f"Downloading directory from R2: {r2_prefix}")
    r2.download_directory(r2_prefix, local_dir)

    return local_dir

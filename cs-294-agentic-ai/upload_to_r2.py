#!/usr/bin/env python3
"""
Upload experiment files to Cloudflare R2 storage

Usage:
    python upload_to_r2.py /path/to/experiment experiment_name
"""
import os
import sys
from pathlib import Path
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def upload_directory_to_r2(local_dir: str, r2_prefix: str):
    """
    Upload a directory to R2 storage

    Args:
        local_dir: Local directory path
        r2_prefix: R2 prefix (e.g., 'experiment_1')
    """
    # Get R2 credentials from environment
    bucket = os.getenv('S3_BUCKET')
    access_key = os.getenv('S3_ACCESS_KEY_ID')
    secret_key = os.getenv('S3_SECRET_ACCESS_KEY')
    endpoint_url = os.getenv('S3_ENDPOINT_URL')
    public_url_base = os.getenv('S3_PUBLIC_URL_BASE')

    if not all([bucket, access_key, secret_key, endpoint_url]):
        print("❌ Error: Missing R2 configuration in .env file")
        print("Required: S3_BUCKET, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL")
        sys.exit(1)

    # Initialize S3 client
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='auto'
    )

    print(f"📦 Uploading files from {local_dir} to R2://{bucket}/{r2_prefix}")
    print("-" * 60)

    local_path = Path(local_dir)
    if not local_path.exists():
        print(f"❌ Error: Directory not found: {local_dir}")
        sys.exit(1)

    uploaded_files = []

    # Walk through directory and upload files
    for file_path in local_path.rglob('*'):
        if file_path.is_file() and not file_path.name.startswith('.'):
            # Calculate relative path
            relative_path = file_path.relative_to(local_path)
            r2_key = f"{r2_prefix}/{relative_path}".replace('\\', '/')

            # Upload file
            print(f"📤 Uploading: {relative_path} -> {r2_key}")
            try:
                s3_client.upload_file(
                    str(file_path),
                    bucket,
                    r2_key,
                    ExtraArgs={'ContentType': get_content_type(file_path)}
                )
                uploaded_files.append({
                    'local': str(file_path),
                    'r2_key': r2_key,
                    'size': file_path.stat().st_size
                })
            except Exception as e:
                print(f"❌ Failed to upload {relative_path}: {e}")

    print("-" * 60)
    print(f"✅ Uploaded {len(uploaded_files)} files")
    print()

    # Print summary and test command
    print("=" * 60)
    print("📋 UPLOAD SUMMARY")
    print("=" * 60)
    print()

    # Identify key files
    data_file = next((f for f in uploaded_files if 'data_source' in f['r2_key'] and f['r2_key'].endswith('.csv')), None)
    code_file = next((f for f in uploaded_files if 'code' in f['r2_key'] and f['r2_key'].endswith('.py')), None)
    report_file = next((f for f in uploaded_files if 'report' in f['r2_key'] and f['r2_key'].endswith('.md')), None)

    print("Key Files:")
    if data_file:
        print(f"  📊 Data:   {data_file['r2_key']}")
    if code_file:
        print(f"  💻 Code:   {code_file['r2_key']}")
    if report_file:
        print(f"  📝 Report: {report_file['r2_key']}")
    print()

    # Generate test command
    print("🧪 TEST COMMAND")
    print("=" * 60)
    print()
    print("Local testing (after starting server with ./run.sh):")
    print()
    print(f"curl -X POST http://localhost:8000/a2a/invoke \\")
    print(f"  -H 'Content-Type: application/json' \\")
    print(f"  -d '{{")
    print(f'    "capability": "ab_test_validation",')
    print(f'    "input": {{')

    if data_file:
        print(f'      "data_source": "{data_file["r2_key"]}",')
    if code_file:
        print(f'      "code_source": "{code_file["r2_key"]}",')
    if report_file:
        print(f'      "report_source": "{report_file["r2_key"]}"')

    print(f'    }},')
    print(f'    "async_execution": false')
    print(f"  }}'")
    print()

    print("Deployed testing (Render):")
    print()
    print(f"curl -X POST https://ab-test-validator.onrender.com/a2a/invoke \\")
    print(f"  -H 'Content-Type: application/json' \\")
    print(f"  -d '{{")
    print(f'    "capability": "ab_test_validation",')
    print(f'    "input": {{')

    if data_file:
        print(f'      "data_source": "{data_file["r2_key"]}",')
    if code_file:
        print(f'      "code_source": "{code_file["r2_key"]}",')
    if report_file:
        print(f'      "report_source": "{report_file["r2_key"]}"')

    print(f'    }},')
    print(f'    "async_execution": true')
    print(f"  }}'")
    print()

    if public_url_base:
        print("📍 Public URLs (if bucket is public):")
        print()
        for file_info in uploaded_files[:5]:  # Show first 5 files
            public_url = f"{public_url_base.rstrip('/')}/{file_info['r2_key']}"
            print(f"  {public_url}")
        if len(uploaded_files) > 5:
            print(f"  ... and {len(uploaded_files) - 5} more files")
        print()

    print("=" * 60)
    print()
    print("💡 TIP: Add these environment variables to Render:")
    print(f"   S3_BUCKET={bucket}")
    print(f"   S3_ACCESS_KEY_ID={access_key[:8]}...")
    print(f"   S3_SECRET_ACCESS_KEY=***hidden***")
    print(f"   S3_ENDPOINT_URL={endpoint_url}")
    if public_url_base:
        print(f"   S3_PUBLIC_URL_BASE={public_url_base}")


def get_content_type(file_path: Path) -> str:
    """Get content type based on file extension"""
    extension = file_path.suffix.lower()
    content_types = {
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.md': 'text/markdown',
        '.py': 'text/x-python',
        '.txt': 'text/plain',
        '.html': 'text/html',
        '.pdf': 'application/pdf',
    }
    return content_types.get(extension, 'application/octet-stream')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python upload_to_r2.py <local_directory> <r2_prefix>")
        print()
        print("Example:")
        print("  python upload_to_r2.py /Users/you/Downloads/results/experiment experiment_1")
        print()
        print("This will upload:")
        print("  /Users/you/Downloads/results/experiment/data_source/data.csv")
        print("  -> R2: experiment_1/data_source/data.csv")
        sys.exit(1)

    local_dir = sys.argv[1]
    r2_prefix = sys.argv[2]

    upload_directory_to_r2(local_dir, r2_prefix)

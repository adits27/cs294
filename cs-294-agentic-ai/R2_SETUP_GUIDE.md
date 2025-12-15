## Cloudflare R2 Storage Setup Guide

Complete guide to integrate Cloudflare R2 storage with your A/B Test Validation Agent.

## Overview

Your agent now supports reading experiment files from Cloudflare R2 storage. This allows you to:
- Upload experiment files once to R2
- Test from anywhere without local file access
- Share experiments via R2 keys or public URLs

---

## Step 1: Configure R2 Credentials

### 1.1 Update your `.env` file

Add these variables to your `.env` file:

```bash
# Cloudflare R2 Storage
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY_ID=your-access-key-id
S3_SECRET_ACCESS_KEY=your-secret-access-key
S3_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
S3_PUBLIC_URL_BASE=https://pub-abc123.r2.dev  # Optional, if using public bucket
```

### 1.2 Get your R2 credentials

1. Go to Cloudflare Dashboard → R2
2. Create a bucket (e.g., `ab-test-experiments`)
3. Go to "Manage R2 API Tokens"
4. Create an API token with R2 Read & Write permissions
5. Copy the credentials

**Endpoint URL Format:**
```
https://<ACCOUNT_ID>.r2.cloudflarestorage.com
```

**Public URL Base** (optional, for public buckets):
```
https://pub-<RANDOM>.r2.dev
```

---

## Step 2: Upload Experiment Files

### 2.1 Install dependencies locally

```bash
pip install boto3 python-dotenv
```

### 2.2 Upload your experiment folder

```bash
python upload_to_r2.py /Users/adithyasubramaniam/Downloads/results/experiment experiment_1
```

**This will upload:**
```
/Users/.../experiment/data_source/data.csv     -> experiment_1/data_source/data.csv
/Users/.../experiment/data_source/context.txt  -> experiment_1/data_source/context.txt
/Users/.../experiment/code/analysis.py          -> experiment_1/code/analysis.py
/Users/.../experiment/report/analysis_report.md -> experiment_1/report/analysis_report.md
/Users/.../experiment/report/results.json      -> experiment_1/report/results.json
```

The script will print:
- Upload summary
- Test commands for local and deployed testing
- Environment variables to add to Render

---

## Step 3: Test Locally

### 3.1 Start the local server

```bash
./run.sh
```

### 3.2 Test with R2 files

```bash
curl -X POST http://localhost:8000/a2a/invoke \
  -H 'Content-Type: application/json' \
  -d '{
    "capability": "ab_test_validation",
    "input": {
      "data_source": "experiment_1/data_source/data.csv",
      "code_source": "experiment_1/code/analysis.py",
      "report_source": "experiment_1/report/analysis_report.md"
    },
    "async_execution": false
  }'
```

**The agent will:**
1. Detect these are R2 keys (not local paths)
2. Download files from R2 to temporary local storage
3. Run validation on the downloaded files
4. Return validation results

---

## Step 4: Deploy to Render with R2 Support

### 4.1 Add R2 environment variables to Render

In Render Dashboard → Your Service → Environment:

```
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY_ID=your-access-key-id
S3_SECRET_ACCESS_KEY=your-secret-access-key
S3_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
S3_PUBLIC_URL_BASE=https://pub-abc123.r2.dev
```

### 4.2 Commit and push changes

```bash
git add requirements.txt agents/storage.py agents/__init__.py .env.example
git commit -m "Add Cloudflare R2 storage support"
git push
```

Render will auto-deploy with the new changes.

### 4.3 Test deployed agent

```bash
curl -X POST https://ab-test-validator.onrender.com/a2a/invoke \
  -H 'Content-Type: application/json' \
  -d '{
    "capability": "ab_test_validation",
    "input": {
      "data_source": "experiment_1/data_source/data.csv",
      "code_source": "experiment_1/code/analysis.py",
      "report_source": "experiment_1/report/analysis_report.md"
    },
    "async_execution": true
  }'
```

---

## How It Works

### Path Resolution Logic

The agent automatically detects and handles different path formats:

1. **R2 Keys** (relative paths):
   ```json
   "data_source": "experiment_1/data_source/data.csv"
   ```
   - If R2 is configured and path isn't local, treats as R2 key
   - Downloads from R2 to temp file
   - Returns local temp path

2. **R2 URLs** (s3:// or r2:// protocol):
   ```json
   "data_source": "r2://my-bucket/experiment_1/data_source/data.csv"
   ```
   - Extracts bucket and key
   - Downloads from R2

3. **Public R2 URLs**:
   ```json
   "data_source": "https://pub-abc123.r2.dev/experiment_1/data_source/data.csv"
   ```
   - Detects public URL base
   - Downloads from R2

4. **Local Paths**:
   ```json
   "data_source": "/absolute/path/to/data.csv"
   ```
   - If file exists locally, uses it directly
   - No R2 download needed

### Under the Hood

When you call the agent with R2 paths:

```python
from agents import resolve_path

# Input: R2 key
data_path = resolve_path("experiment_1/data_source/data.csv")
# Output: /tmp/xyz123.csv (downloaded from R2)

# Input: Local path that exists
data_path = resolve_path("/local/data.csv")
# Output: /local/data.csv (no download)
```

---

## File Structure in R2

Recommended R2 structure:

```
my-bucket/
├── experiment_1/
│   ├── data_source/
│   │   ├── data.csv
│   │   └── context.txt
│   ├── code/
│   │   └── analysis.py
│   └── report/
│       ├── analysis_report.md
│       └── results.json
├── experiment_2/
│   ├── data_source/
│   │   └── ...
```

Then reference files as:
- `data_source`: `experiment_1/data_source/data.csv`
- `code_source`: `experiment_1/code/analysis.py`
- `report_source`: `experiment_1/report/analysis_report.md`

---

## Troubleshooting

### Files not found

**Error:** `File not found at experiment_1/data.csv`

**Solutions:**
1. Check R2 credentials are correct in `.env`
2. Verify file exists in R2 bucket
3. Check R2 key path is exact (case-sensitive)

### Permission denied

**Error:** `Access Denied` when downloading from R2

**Solutions:**
1. Verify API token has Read permissions
2. Check bucket name is correct
3. Confirm endpoint URL matches your account

### Public URLs not working

**Error:** Public URL returns 404

**Solutions:**
1. Enable public access on your R2 bucket
2. Configure custom domain or R2.dev subdomain
3. Set `S3_PUBLIC_URL_BASE` correctly

---

## Security Best Practices

1. **Never commit R2 credentials to git**
   - Always use `.env` file
   - `.env` is in `.gitignore`

2. **Use least-privilege API tokens**
   - Create separate tokens for read-only vs read-write
   - Limit token permissions to specific buckets

3. **Rotate credentials regularly**
   - Change API tokens every 90 days
   - Update in both local `.env` and Render

4. **Use private buckets for sensitive data**
   - Don't enable public access for confidential experiments
   - Use presigned URLs if temporary public access is needed

---

## Cost Estimate

Cloudflare R2 pricing (as of 2024):
- **Storage**: $0.015 per GB/month
- **Class A Operations** (writes): $4.50 per million
- **Class B Operations** (reads): $0.36 per million
- **Egress**: $0 (free!)

**Example usage:**
- 100 experiments × 5 MB each = 500 MB = **$0.0075/month**
- 1000 validations × 3 files each = 3000 reads = **$0.001**
- **Total: < $0.01/month**

R2 is extremely cost-effective for this use case!

---

## Next Steps

1. ✅ Configure R2 credentials in `.env`
2. ✅ Upload your experiment files with `upload_to_r2.py`
3. ✅ Test locally with R2 paths
4. ✅ Add R2 env vars to Render
5. ✅ Deploy and test in production

Your agent now supports cloud storage! 🎉

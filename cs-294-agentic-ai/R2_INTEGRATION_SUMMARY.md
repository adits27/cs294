# Cloudflare R2 Integration - Summary

## What Was Added

I've integrated Cloudflare R2 (S3-compatible) storage support into your A/B Test Validation Agent. Now you can store experiment files in the cloud and test from anywhere!

## Files Created/Modified

### ✅ New Files
1. **`agents/storage.py`** - R2 storage client and path resolution logic
2. **`upload_to_r2.py`** - Script to upload experiments to R2
3. **`R2_SETUP_GUIDE.md`** - Complete setup and usage guide
4. **`R2_INTEGRATION_SUMMARY.md`** - This file

### ✅ Modified Files
1. **`requirements.txt`** - Added `boto3>=1.34.0`
2. **`agents/__init__.py`** - Exported R2 storage functions
3. **`.env.example`** - Added R2 environment variables template

## Environment Variables Needed

Add these to your `.env` file and Render:

```bash
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY_ID=your-access-key-id
S3_SECRET_ACCESS_KEY=your-secret-access-key
S3_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
S3_PUBLIC_URL_BASE=https://pub-abc123.r2.dev  # Optional
```

## Quick Start

### 1. Add R2 credentials to `.env`

```bash
# Copy your actual R2 credentials
S3_BUCKET=ab-test-experiments
S3_ACCESS_KEY_ID=abc123...
S3_SECRET_ACCESS_KEY=xyz789...
S3_ENDPOINT_URL=https://1234abcd.r2.cloudflarestorage.com
S3_PUBLIC_URL_BASE=https://pub-xyz.r2.dev
```

### 2. Upload your experiment files

```bash
python upload_to_r2.py /Users/adithyasubramaniam/Downloads/results/experiment experiment_1
```

This uploads your experiment folder structure to R2 as:
```
experiment_1/
├── data_source/data.csv
├── data_source/context.txt
├── code/analysis.py
├── report/analysis_report.md
└── report/results.json
```

### 3. Test locally

```bash
# Start server
./run.sh

# Test with R2 files
curl -X POST http://localhost:8000/a2a/invoke \
  -H 'Content-Type: application/json' \
  -d '{
    "capability": "ab_test_validation",
    "input": {
      "data_source": "experiment_1/data_source/data.csv",
      "code_source": "experiment_1/code/analysis.py",
      "report_source": "experiment_1/report/analysis_report.md"
    }
  }'
```

### 4. Deploy to Render

```bash
# 1. Add R2 env vars to Render dashboard
# 2. Commit and push
git add .
git commit -m "Add Cloudflare R2 storage support"
git push

# 3. Test deployed version
curl -X POST https://ab-test-validator.onrender.com/a2a/invoke \
  -H 'Content-Type: application/json' \
  -d '{
    "capability": "ab_test_validation",
    "input": {
      "data_source": "experiment_1/data_source/data.csv"
    },
    "async_execution": true
  }'
```

## How It Works

The agent automatically handles different path formats:

| Input Format | Example | Behavior |
|--------------|---------|----------|
| R2 Key | `experiment_1/data.csv` | Downloads from R2 |
| R2 URL | `r2://bucket/data.csv` | Downloads from R2 |
| Public URL | `https://pub-xyz.r2.dev/data.csv` | Downloads from R2 |
| Local Path | `/tmp/data.csv` | Uses local file directly |

The agent is smart enough to detect which format you're using and handle it appropriately!

## File Structure

Your experiment folder on R2 should match this structure:

```
experiment_1/          # Your experiment name
├── data_source/       # Data files
│   ├── data.csv
│   └── context.txt
├── code/              # Analysis code
│   └── analysis.py
└── report/            # Results and reports
    ├── analysis_report.md
    └── results.json
```

This matches the structure from `/Users/adithyasubramaniam/Downloads/results/experiment`.

## Benefits

✅ **No local file requirements** - Files live in the cloud
✅ **Test from anywhere** - Local dev, Render deployment, or other services
✅ **Easy sharing** - Share experiments via R2 keys
✅ **Cost-effective** - ~$0.01/month for typical usage
✅ **Fast** - Files cached locally during validation
✅ **Backward compatible** - Local files still work

## Next Steps

1. **Set up R2 credentials** - Add to `.env` and Render
2. **Upload experiment** - Use `upload_to_r2.py`
3. **Test locally** - Verify everything works
4. **Deploy** - Push to Render with R2 env vars
5. **Validate!** - Run real A/B test validations with cloud files

See [R2_SETUP_GUIDE.md](R2_SETUP_GUIDE.md) for detailed instructions!

## Questions?

- **How do I get R2 credentials?** → See R2_SETUP_GUIDE.md Step 1.2
- **How much does R2 cost?** → ~$0.01/month for typical usage
- **Can I still use local files?** → Yes! Both local and R2 paths work
- **Do I need to change my existing code?** → No, just add env vars and use R2 paths

---

**Your agent now supports cloud storage! 🚀**

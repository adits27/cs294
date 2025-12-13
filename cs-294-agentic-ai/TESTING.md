# Testing Guide

This guide explains how to test the Multi-Agent A/B Testing Validation system.

## Prerequisites

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up API Key**

   Make sure `GOOGLE_API_KEY` is set in your `.env` file:
   ```bash
   # .env file
   GOOGLE_API_KEY=your_api_key_here
   ```

   The key should already be present in `/Users/adithyasubramaniam/Documents/CS-Projects/cs294/.env`

## Test Options

### Option 1: Test with Dummy Agents (Fast, No API Calls)

Use the original test that uses dummy agents returning fixed scores:

```bash
cd /Users/adithyasubramaniam/Documents/CS-Projects/cs294/cs-294-agentic-ai
python3 test_orchestrator.py
```

**Expected Result:**
- Final Score: 87.6/100
- Decision: GOOD A/B TEST
- All 4 agents execute in parallel
- No API calls, instant completion

**Note:** This test still uses `dummy_agents` imports, so it won't test the real LLM agents.

---

### Option 2: Test with Real Agents (Full LLM Integration)

Use the new test that uses real agents with LLM and tool execution:

```bash
cd /Users/adithyasubramaniam/Documents/CS-Projects/cs294/cs-294-agentic-ai
python3 test_real_agents.py
```

**What This Tests:**
- ✅ Real LLM agents with Google Gemini
- ✅ Python tool execution (PythonRepl)
- ✅ Graceful fallback to LLM if tools fail
- ✅ Actual scoring based on analysis
- ✅ Complete A2A message protocol
- ✅ Parallel agent execution

**Expected Behavior:**

1. **Data Validation Agent:**
   - Attempts to load `sample_data/ab_test_data.csv`
   - If file exists: Uses pandas to analyze data
   - If file missing: Falls back to LLM heuristic
   - LLM scores the analysis (0-100)

2. **Statistical Validation Agent:**
   - Attempts to calculate power analysis
   - If successful: Compares power vs target (0.80)
   - If fails: LLM provides heuristic assessment
   - LLM scores statistical design (0-100)

3. **Code Validation Agent:**
   - Checks syntax of `sample_data/ab_test_data.py`
   - If syntax error: Score = 0 (auto-fail)
   - If syntax OK: LLM reviews style
   - Final: average(syntax_score, style_score)

4. **Report Validation Agent:**
   - Loads `sample_data/ab_test_data_report.md`
   - LLM reviews as Product Manager
   - Scores: structure, conclusions, actionability, completeness

**Expected Output:**
```
A/B TEST VALIDATION - REAL AGENTS TEST
============================================================
Hypothesis: New checkout button color increases conversion rate by at least 5%
...

[WORKFLOW - PARALLEL] Executing Data Validation Agent...
  Generated code length: XXX chars
  Tool execution: SUCCESS (or FAILED)
  Data Validation: XX.X

[WORKFLOW - PARALLEL] Executing Code Validation Agent...
  Syntax check: PASS
  Style score: XX.X
  Code Validation: XX.X

[WORKFLOW - PARALLEL] Executing Report Validation Agent...
  Report Validation: XX.X

[WORKFLOW - PARALLEL] Executing Statistical Validation Agent...
  Tool execution: SUCCESS (or FAILED)
  Statistical Validation: XX.X

Final Score: XX.X/100
Decision: GOOD A/B TEST or BAD A/B TEST
```

---

### Option 3: Test Missing Agents (Weight Re-normalization)

```bash
python3 test_missing_agents.py
```

Tests that the orchestrator correctly re-normalizes weights when agents are missing.

---

## Sample Data Files

The repository includes sample data in `sample_data/`:

1. **`ab_test_data.csv`** - Sample A/B test dataset (20 users)
2. **`ab_test_data.py`** - Sample analysis code with good syntax
3. **`ab_test_data_report.md`** - Comprehensive A/B test report

These files are used by the real agents if they exist. If they don't exist, agents will gracefully fall back to LLM heuristic assessment.

---

## Troubleshooting

### Error: "GOOGLE_API_KEY not found"

**Solution:** Make sure the API key is set in your `.env` file:
```bash
cd /Users/adithyasubramaniam/Documents/CS-Projects/cs294
cat .env | grep GOOGLE_API_KEY
```

If not set:
```bash
echo "GOOGLE_API_KEY=your_key_here" >> .env
```

---

### Error: "Module not found"

**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

---

### Error: "Execution timed out"

**Solution:** The PythonRepl has a 30-second timeout. If tool execution is slow:
1. Check your internet connection
2. The agent will automatically fall back to LLM assessment

---

### Low Scores from Agents

This is **expected** if:
- Files don't exist (agents use fallback)
- Data quality is actually poor
- Code has issues
- Report is incomplete

The system is working correctly - it's identifying real issues!

---

## Understanding the Results

### Score Ranges

- **90-100**: Excellent - Production ready
- **70-89**: Good - Minor improvements needed
- **50-69**: Fair - Significant issues to address
- **0-49**: Poor - Major problems, not ready

### Weighted Scoring

Final score = weighted average of 4 agents:
- Statistical Validation: **40%**
- Report Quality: **30%**
- Data Quality: **20%**
- Code Quality: **10%**

### Decision Threshold

- Final Score ≥ 70: **GOOD A/B TEST**
- Final Score < 70: **BAD A/B TEST**

---

## Next Steps

After successful testing:

1. **Review Results**: Check agent scores and reasoning
2. **Iterate**: Fix issues identified by agents
3. **Re-test**: Run validation again
4. **Deploy**: When score ≥ 70, A/B test is ready!

---

## Performance Notes

- **Dummy Agents**: < 1 second
- **Real Agents (with tools)**: 10-30 seconds
- **Real Agents (fallback)**: 5-15 seconds

LLM calls and tool execution add latency but provide accurate, intelligent validation.

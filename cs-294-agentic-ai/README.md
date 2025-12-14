# Multi-Agent A/B Testing Validation System

A multi-agent system for validating A/B test experiments using specialized AI agents that communicate via the Agent-to-Agent (A2A) protocol. The system analyzes data quality, code quality, report quality, and statistical validity to provide an overall validation score and recommendation.

## Motivation

A/B testing is critical for data-driven decision making, but validating experiments requires expertise across multiple domains: statistics, data engineering, software development, and scientific communication. This system automates comprehensive validation by decomposing the problem into specialized agents, each focused on a specific aspect of validation. The agents collaborate through standardized A2A protocol messages to produce a weighted assessment.

The system addresses several challenges in A/B test validation:
- Statistical rigor: Proper power analysis, significance testing, and effect size calculations
- Data quality: Completeness, distribution checks, and sample size adequacy
- Code quality: Best practices, reproducibility, and documentation
- Report quality: Clarity, completeness, and proper communication of results

## Architecture

### Agent-to-Agent (A2A) Protocol

All agents communicate using standardized JSON messages with the following structure:

```json
{
  "message_id": "uuid",
  "session_id": "session-uuid",
  "sender": "agent_id",
  "receiver": "target_agent_id",
  "message_type": "REQUEST | RESPONSE | ERROR",
  "timestamp": "ISO-8601 timestamp",
  "task": "Task description",
  "data": {},
  "status": "PENDING | COMPLETED | FAILED",
  "result": {}
}
```

### Multi-Agent System

The system consists of five specialized agents:

1. Parameter Inference Agent
   - Extracts test parameters from experiment files
   - Infers hypothesis, metrics, and effect sizes using LLM analysis
   - Provides fallback defaults when parameters cannot be determined

2. Statistical Validation Agent (40% weight)
   - Power analysis and sample size calculations
   - Significance testing (t-tests, chi-square, etc.)
   - Effect size computation (Cohen's d, odds ratio, etc.)
   - Multiple testing corrections

3. Report Validation Agent (30% weight)
   - Report structure and completeness
   - Clarity of findings and methodology
   - Quality of visualizations
   - Proper statistical reporting

4. Data Validation Agent (20% weight)
   - Data completeness and quality checks
   - Missing value analysis
   - Distribution analysis
   - Sample size adequacy

5. Code Validation Agent (10% weight)
   - Code structure and organization
   - Best practices compliance
   - Error handling and robustness
   - Documentation quality

### Weighted Scoring

The orchestrator synthesizes validation results using weighted averaging:

```
Final Score = (Statistical × 0.40) + (Report × 0.30) + (Data × 0.20) + (Code × 0.10)
```

Decision threshold: Score >= 70.0 indicates a valid A/B test.

Weights are automatically re-normalized if certain validation agents are unavailable.

### Workflow Execution

The LangGraph-based workflow consists of the following nodes:

1. infer_parameters_node: Extract test parameters from provided files
2. plan_validation: Determine which validation agents to invoke
3. delegate_to_agents: Create A2A request messages for sub-agents
4. execute_agents: Execute agents in parallel and collect responses
5. synthesize_results: Calculate weighted score and generate final decision

## Project Structure

```
cs-294-agentic-ai/
├── agents/
│   ├── __init__.py                      # Package exports
│   ├── base_agent.py                    # Abstract base class for agents
│   ├── protocol.py                      # A2A message protocol definitions
│   ├── state.py                         # Shared state and context schemas
│   ├── workflow.py                      # LangGraph workflow orchestration
│   ├── orchestrator.py                  # Main orchestrating agent
│   ├── parameter_inference_agent.py     # Parameter extraction agent
│   ├── data_validation_agent.py         # Data quality validation
│   ├── code_validation_agent.py         # Code quality validation
│   ├── report_validation_agent.py       # Report quality validation
│   ├── statistical_validation_agent.py  # Statistical validation
│   ├── llm_config.py                    # LLM provider configuration
│   ├── logger.py                        # Logging utilities
│   └── tools.py                         # Python REPL and utility tools
├── api/
│   ├── __init__.py                      # API package exports
│   ├── server.py                        # FastAPI application server
│   ├── routes.py                        # REST API endpoints
│   ├── a2a_routes.py                    # A2A protocol endpoints
│   └── schemas.py                       # Pydantic request/response models
├── a2a-manifest.json                    # A2A agent capability manifest
├── requirements.txt                     # Python dependencies
├── .env.example                         # Environment configuration template
└── README.md                            # This file
```

## Installation

### Prerequisites

- Python 3.11 or higher
- API key for at least one LLM provider (Google, OpenAI, or Anthropic)

### Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure environment variables:

```bash
cp .env.example .env
# Edit .env and add your API keys
```

Required environment variables:

```bash
# LLM Provider (at least one required)
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
PUBLIC_URL=http://localhost:8000

# Validation Settings
VALIDATION_THRESHOLD=70.0
DEFAULT_LLM_PROVIDER=google
DEFAULT_MODEL=gemini-pro
```

## Running the System

### Option 1: REST API Server

Start the FastAPI server:

```bash
python api/server.py
```

Or using uvicorn:

```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

The server provides:
- Interactive API documentation at http://localhost:8000/docs
- REST API endpoints at http://localhost:8000/api/v1
- A2A protocol endpoints at http://localhost:8000/a2a

### Option 2: Direct Python Usage

```python
from agents import ABTestContext, create_initial_state, run_validation_workflow

# Create context with folder pattern (auto-discovers data/code/report)
ab_test_context = ABTestContext(
    data_source="path/to/experiment/*"
)

# Or specify paths explicitly
ab_test_context = ABTestContext(
    data_source="path/to/data.csv",
    code_source="path/to/analysis.py",
    report_source="path/to/report.md",
    hypothesis="Treatment increases conversion rate",
    success_metrics=["conversion_rate"],
    expected_effect_size=0.05
)

# Create initial state
initial_state = create_initial_state(
    task="Validate A/B test experiment",
    ab_test_context=ab_test_context
)

# Run validation workflow
final_state = run_validation_workflow(initial_state)

# Access results
print(f"Final Score: {final_state['final_score']}/100")
print(f"Decision: {final_state['validation_summary']}")
```

## API Usage

### Simple Request (Folder Pattern)

```bash
curl -X POST http://localhost:8000/api/v1/workflows/validate \
  -H "Content-Type: application/json" \
  -d '{
    "ab_test_context": {
      "data_source": "path/to/experiment/*"
    }
  }'
```

The system will:
- Auto-discover data_source/, code/, and report/ subdirectories
- Infer hypothesis, metrics, and effect sizes from files
- Run all validation agents in parallel
- Return weighted score and decision

### Full Request (Explicit Parameters)

```bash
curl -X POST http://localhost:8000/api/v1/workflows/validate \
  -H "Content-Type: application/json" \
  -d '{
    "ab_test_context": {
      "data_source": "path/to/data.csv",
      "code_source": "path/to/code.py",
      "report_source": "path/to/report.md",
      "hypothesis": "New feature increases conversion",
      "success_metrics": ["conversion_rate"],
      "expected_effect_size": 0.05,
      "significance_level": 0.05,
      "power": 0.80
    }
  }'
```

### Response Format

```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "final_score": 75.5,
  "decision": "GOOD A/B TEST",
  "validation_summary": "Overall validation score: 75.5/100...",
  "breakdown": {
    "statistical_validation": 80.0,
    "report_quality": 75.0,
    "data_quality": 70.0,
    "code_quality": 65.0
  },
  "validation_results": {},
  "execution_time_seconds": 15.2
}
```

## A2A Protocol Compliance

The system implements the Agent-to-Agent protocol specification:

- A2A manifest available at /a2a/manifest
- Capability discovery at /a2a/capabilities
- Standard invocation at /a2a/invoke
- Session management for async execution
- Status and result retrieval endpoints

## Deployment

The system can be deployed to any cloud platform supporting Python web applications:

1. Set environment variables in your platform's dashboard
2. Use the start command: `uvicorn api.server:app --host 0.0.0.0 --port $PORT`
3. Ensure PUBLIC_URL is set to your deployment URL

Supported platforms: Railway, Render, Heroku, AWS, GCP, Azure

## Testing

The repository includes test data in results/ for local testing. To test with sample data:

```bash
python test_folder_pattern.py
```

This will validate the sample experiment in results/result_1_1/ and display the complete validation report.

## Dependencies

Core dependencies:
- fastapi: REST API framework
- uvicorn: ASGI server
- langgraph: Agent workflow orchestration
- langchain: LLM framework
- pydantic: Data validation
- pandas, numpy, scipy: Data analysis and statistics
- google-generativeai, langchain-openai, langchain-anthropic: LLM providers

See requirements.txt for complete list.

## License

MIT License - See LICENSE file for details.

## References

- Agent-to-Agent Protocol Specification: https://github.com/agentbeats/a2a-protocol
- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- FastAPI Documentation: https://fastapi.tiangolo.com/

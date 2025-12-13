# Multi-Agent A/B Testing Validation System

A sophisticated Multi-Agent A/B Testing "Validation and Assessor" system that uses strict Agent-to-Agent (A2A) protocol for communication between specialized validation agents.

## Project Structure

```
cs-294-agentic-ai/
├── agents/
│   ├── __init__.py           # Package exports
│   ├── protocol.py           # A2A Message definitions
│   ├── state.py              # Shared State and Context schemas
│   ├── base_agent.py         # Abstract Base Class for all agents
│   ├── orchestrator.py       # Main orchestrating agent
│   ├── workflow.py           # LangGraph workflow definition
│   └── dummy_agents.py       # Mock agents for testing
├── test_orchestrator.py      # Test script
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Architecture

### A2A Protocol

All agents communicate via standardized JSON A2A messages:

```json
{
  "message_id": "uuid string",
  "sender": "string",
  "receiver": "string",
  "message_type": "REQUEST | RESPONSE | ERROR",
  "timestamp": "ISO string",
  "task": "optional string",
  "data": { ... },
  "status": "PENDING | COMPLETED | FAILED",
  "result": { ... }
}
```

### Validation Agents

The system consists of four specialized validation agents:

1. **Data Validation Agent** (20% weight)
   - Validates data completeness
   - Checks for missing values
   - Analyzes data distribution
   - Verifies sample size adequacy

2. **Code Validation Agent** (10% weight)
   - Reviews code structure
   - Checks best practices
   - Validates error handling
   - Assesses documentation

3. **Report Validation Agent** (30% weight)
   - Evaluates report structure
   - Assesses clarity of findings
   - Checks completeness
   - Reviews visualizations

4. **Statistical Validation Agent** (40% weight)
   - Performs power analysis
   - Tests statistical significance
   - Validates effect size
   - Checks multiple testing corrections

### Weighted Scoring

The orchestrator synthesizes results using weighted scoring:

- **Statistical Validation**: 40%
- **Report Quality**: 30%
- **Data Quality**: 20%
- **Code Quality**: 10%

Missing agents trigger automatic weight re-normalization.

### LangGraph Workflow

The validation workflow consists of four nodes:

1. **plan_validation**: Analyzes context and decides which agents to call
2. **delegate_to_agents**: Creates A2A REQUEST messages for sub-agents
3. **execute_agents**: Executes agents and collects responses
4. **synthesize_results**: Calculates weighted score and generates decision

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running the Test Script

```bash
python test_orchestrator.py
```

This will:
1. Create a sample A/B test context
2. Run the complete validation workflow
3. Display the weighted score calculation
4. Show the final decision (GOOD/BAD A/B TEST)
5. Print the complete A2A message log

### Expected Output

With the dummy agents (scores: Data=85, Code=78, Report=92, Stats=88):

```
Final Score: 87.6/100
Decision: GOOD A/B TEST

Score Breakdown:
  Data Quality:          85.0 × 20% = 17.0
  Code Quality:          78.0 × 10% =  7.8
  Report Quality:        92.0 × 30% = 27.6
  Statistical Validation: 88.0 × 40% = 35.2
                                      ------
  Final Score:                        87.6
```

### Using in Code

```python
from agents import ABTestContext, create_initial_state
from agents.workflow import run_validation_workflow

# Create A/B test context
ab_test_context = ABTestContext(
    hypothesis="New feature increases conversion by 5%",
    success_metrics=["conversion_rate"],
    dataset_path="/data/experiment.csv",
    expected_effect_size=0.05,
    significance_level=0.05,
    power=0.80
)

# Create initial state
initial_state = create_initial_state(
    task="Validate A/B test experiment",
    ab_test_context=ab_test_context
)

# Run workflow
final_state = run_validation_workflow(initial_state)

# Access results
print(f"Final Score: {final_state['final_score']}")
print(final_state['validation_summary'])
```

## Development Status

- ✅ **Stage 1**: Project structure, A2A protocol, state management, base agent
- ✅ **Stage 2**: Orchestrator, LangGraph workflow, dummy agents, testing
- ⏳ **Stage 3**: Real agent implementations (coming next)

## Key Features

- **Strict A2A Protocol**: All communication via standardized messages
- **Type-Safe**: Pydantic models for validation and type checking
- **LangGraph Integration**: StateGraph for workflow orchestration
- **Flexible Scoring**: Automatic weight re-normalization for missing agents
- **Extensible**: Easy to add new validation agents
- **Well-Documented**: Comprehensive docstrings and examples

## Next Steps (Stage 3)

1. Implement real validation logic in each agent
2. Add LLM-powered analysis capabilities
3. Integrate with actual A/B test datasets
4. Add error handling and retry logic
5. Implement parallel agent execution
6. Add comprehensive test coverage

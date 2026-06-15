# Financial Leakage Agent

## Overview
The Financial Leakage Agent detects "spend that shouldn't be happening" by analyzing GL line items for potentially inappropriate or unauthorized purchases.

## Architecture
- **Workflow**: Auditor Agent → Buyer Agent → Business Rules Engine
- **Data Sources**: XXC_GL_SUMMARY, XXC_GL_DIV_REG_FAC (same as Auditor Agent)
- **Scoring**: Leakage likelihood [0.0-1.0] based on business rules

## Key Features
1. **Trigger Word Detection**: Identifies suspicious keywords in GL descriptions
2. **Multi-Agent Collaboration**: Leverages Auditor and Buyer agents for validation
3. **Business Rules Engine**: Applies custom rules to calculate leakage risk
4. **JSON Output**: Structured assessment with scoring and reasoning

## Sample Use Cases
1. **Personal Electronics Detection**: Find iPads, AirPods in office supply purchases
2. **Subscription Analysis**: Identify recurring charges without business justification
3. **Luxury Item Flagging**: Detect high-value personal items in business expenses

## File Structure
```
financial_leakage_agent/
├── agent.py                 # Main agent implementation
├── instruction/
│   └── system.md           # System instructions and workflow
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── __init__.py            # Package initialization
```

## Environment Variables Required
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `GOOGLE_CLOUD_LOCATION`: GCP region (default: us-central1)
- `AUDITOR_AGENT_RESOURCE`: Resource name for Auditor Agent
- `BUYER_AGENT_RESOURCE`: Resource name for Buyer Agent
- `SQL_GENERATION_AGENT_RESOURCE`: Resource name for SQL Generation Agent
- `VALIDATION_AGENT_RESOURCE`: Resource name for Validation Agent
- `SQL_EXECUTION_AGENT_RESOURCE`: Resource name for SQL Execution Agent

## Development Status
- [x] Basic agent structure
- [x] Multi-agent integration framework
- [ ] Enhanced query parsing
- [ ] Business rules implementation
- [ ] Trigger word expansion
- [ ] Testing and validation

# Financial Leakage Agent — System Instructions (Developer Reference)

> **Note**: This file is a developer reference. The actual LLM system instruction is in `agent.py` (the `system_instruction` variable). Keep them in sync.
> SQL-specific instructions (trigger word patterns, column mappings, table info) live in `sql_generation_agent/instruction/financial_leakage.md`.

## Agent Purpose

Detects "spend that shouldn't be happening" by scanning GL line item descriptions for trigger words and scoring each finding for leakage likelihood.

## Architecture

Same pattern as Auditor Agent and Trend Agent:
- Uses **sql_generation_agent**, **validation_agent**, **sql_execution_agent** as remote sub-agent tools
- LLM instruction drives the workflow
- Sub-agent calls via ReasoningEngine REST API
- `user_id` = `"financial_leakage"` — routes to `financial_leakage.md` in sql_generation_agent

## Standard Workflow

1. **sql_generation_agent** → generates SQL
2. **validation_agent** → validates SQL
3. **sql_execution_agent** → executes and returns results
4. **Analyze & Score** → apply leakage scoring rules
5. **Respond** → final leakage assessment only (no sub-agent output relayed)

## Leakage Scoring

| Score | Classification |
|-------|---------------|
| 0.7–1.0 | High Risk |
| 0.4–0.69 | Medium Risk |
| 0.0–0.39 | Low Risk |

## Environment Variables

- `SQL_GENERATION_AGENT_RESOURCE` — ReasoningEngine ID for SQL Generation Agent
- `VALIDATION_AGENT_RESOURCE` — ReasoningEngine ID for Validation Agent
- `SQL_EXECUTION_AGENT_RESOURCE` — ReasoningEngine ID for SQL Execution Agent
- `GOOGLE_CLOUD_PROJECT` — GCP project ID
- `GOOGLE_CLOUD_LOCATION` — GCP region (default: us-central1)

# Remaining Agents — Validation Plan

**EY GDS Internship | GCP Multi-Agent Sandbox**
Last Updated: 24 June 2026

---

## Purpose

This document outlines the validation approach for each deployed agent in the Supplier Cost Optimization (SCO) system. Each agent must be tested to confirm it is live on Vertex AI Agent Engine and returns a meaningful response.

---

## Validation Method

For each agent, the following test is performed using the Python script:

```bash
python scripts/deploy_agents.py --test-only "projects/gp-ct-sbox-con-sbp0i2-eyenterp/locations/us-central1/reasoningEngines/<AGENT_ID>"
```

Or directly in Python:

```python
import vertexai
vertexai.init(project="gp-ct-sbox-con-sbp0i2-eyenterp", location="us-central1")
agent = vertexai.agent_engines.get("projects/.../reasoningEngines/<ID>")
for chunk in agent.stream_query(message="<TEST_QUERY>", user_id="test"):
    print(chunk)
```

---

## Agent Validation Checklist

### 1. SQL Generation Agent
- **Test Query:** `"Generate a SQL query to find the top 10 vendors by total spend from the XXC_GL_SUMMARY table"`
- **Expected:** A valid BigQuery SQL SELECT statement
- **Resource Name:** `projects/gp-ct-sbox-con-sbp0i2-eyenterp/locations/us-central1/reasoningEngines/<ID>`
- **Status:** 🔲 Pending
- **Notes:**

---

### 2. Validation Agent
- **Test Query:** `"Validate this SQL: SELECT vendor_name, SUM(amount) FROM ai_financial_dlp.XXC_GL_SUMMARY GROUP BY vendor_name"`
- **Expected:** Confirmation that the SQL is valid or corrected SQL
- **Resource Name:** `projects/gp-ct-sbox-con-sbp0i2-eyenterp/locations/us-central1/reasoningEngines/<ID>`
- **Status:** 🔲 Pending
- **Notes:**

---

### 3. SQL Execution Agent
- **Test Query:** `"Execute: SELECT COUNT(*) FROM ai_financial_dlp.XXC_GL_SUMMARY"`
- **Expected:** A row count result from BigQuery
- **Resource Name:** `projects/gp-ct-sbox-con-sbp0i2-eyenterp/locations/us-central1/reasoningEngines/<ID>`
- **Status:** 🔲 Pending
- **Notes:**

---

### 4. Auditor Agent
- **Test Query:** `"Are there any duplicate invoices or anomalous payments in the dataset?"`
- **Expected:** An analysis summary referencing invoice data
- **Resource Name:** `projects/gp-ct-sbox-con-sbp0i2-eyenterp/locations/us-central1/reasoningEngines/<ID>`
- **Status:** 🔲 Pending
- **Notes:**

---

### 5. Buyer Agent
- **Test Query:** `"Which buyers have the highest purchase volumes this quarter?"`
- **Expected:** Procurement analysis with vendor/buyer data
- **Resource Name:** `projects/gp-ct-sbox-con-sbp0i2-eyenterp/locations/us-central1/reasoningEngines/<ID>`
- **Status:** 🔲 Pending
- **Notes:**

---

### 6. Trend Agent
- **Test Query:** `"Show me the spend trend over the last 6 months by category"`
- **Expected:** A trend summary or tabular breakdown by period
- **Resource Name:** `projects/gp-ct-sbox-con-sbp0i2-eyenterp/locations/us-central1/reasoningEngines/<ID>`
- **Status:** 🔲 Pending
- **Notes:**

---

### 7. Supplier Classification Agent
- **Test Query:** `"Classify the top 5 vendors by their spend tier and type"`
- **Expected:** Vendor classification output (tier, type, risk)
- **Resource Name:** `projects/gp-ct-sbox-con-sbp0i2-eyenterp/locations/us-central1/reasoningEngines/<ID>`
- **Status:** 🔲 Pending
- **Notes:**

---

### 8. Financial Leakage Agent
- **Test Query:** `"Identify any high-risk financial leakage transactions in the dataset"`
- **Expected:** List of flagged transactions with risk classification
- **Resource Name:** `projects/gp-ct-sbox-con-sbp0i2-eyenterp/locations/us-central1/reasoningEngines/<ID>`
- **Status:** 🔲 Pending
- **Notes:**

---

### 9. Contract Intelligence Agent
- **Test Query:** `"Are there any invoiced amounts that deviate significantly from contract terms?"`
- **Expected:** Contract vs invoice comparison analysis
- **Resource Name:** `projects/gp-ct-sbox-con-sbp0i2-eyenterp/locations/us-central1/reasoningEngines/<ID>`
- **Status:** 🔲 Pending
- **Notes:**

---

### 10. Spend IQ Agent (Orchestrator)
- **Test Query:** `"What are the top 5 suppliers by total spend and are there any compliance concerns?"`
- **Expected:** A comprehensive response combining auditing + spend data — routed through multiple sub-agents
- **Resource Name:** `projects/gp-ct-sbox-con-sbp0i2-eyenterp/locations/us-central1/reasoningEngines/3931281834880532480`
- **Status:** 🔲 Pending
- **Notes:**

---

## Validation Sign-Off

| Agent | Deployed | Responds | Response Quality |
|---|---|---|---|
| SQL Generation Agent | ☐ | ☐ | |
| Validation Agent | ☐ | ☐ | |
| SQL Execution Agent | ☐ | ☐ | |
| Auditor Agent | ☐ | ☐ | |
| Buyer Agent | ☐ | ☐ | |
| Trend Agent | ☐ | ☐ | |
| Supplier Classification Agent | ☐ | ☐ | |
| Financial Leakage Agent | ☐ | ☐ | |
| Contract Intelligence Agent | ☐ | ☐ | |
| Spend IQ Agent (Orchestrator) | ☐ | ☐ | |

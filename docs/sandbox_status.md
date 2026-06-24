# Project Progress Tracker — SCO Agent System

**EY GDS Internship | GCP Multi-Agent Sandbox**
Last Updated: 24 June 2026

---

## Overall Status

| Phase | Task | Where | Status |
|---|---|---|---|
| 1 | Repository setup & GitHub sync | Personal Laptop | ✅ Done |
| 2 | Terraform — BigQuery data layer | Company Laptop | ✅ Done |
| 3 | Load sample data into BigQuery | Company Laptop | ✅ Done |
| 4 | Deploy agents to Vertex AI | Company Laptop | ⚠️ Partial |
| 5 | Fill documentation files | Personal Laptop | 🔲 Pending |
| 6 | Test all agents & capture results | Company Laptop | 🔲 Pending |
| 7 | Web app — connect to deployed agents | Company Laptop | 🔲 Pending |
| 8 | Final report / handover notes | Personal Laptop | 🔲 Pending |

---

## Phase 4 — Agent Deployment (Company Laptop)

At least one agent is already deployed (ID: `3931281834880532480`).

### Agents to verify / deploy:

- [ ] `sql_generation_agent`
- [ ] `validation_agent`
- [ ] `sql_execution_agent`
- [ ] `auditor_agent`
- [ ] `buyer_agent`
- [ ] `trend_agent`
- [ ] `supplier_classification_agent`
- [ ] `financial_leakage_agent`
- [ ] `contract_intelligence_agent`
- [ ] `spend_iq_agent` ← deploy last

---

## Phase 6 — Testing (Company Laptop)

- [ ] Run BigQuery SQL tests from `docs/manual_bigquery_tests.sql`
- [ ] Test each agent via `scripts/deploy_agents.py --test-only`
- [ ] Capture response screenshots for manager

---

## Phase 7 — Web App (Company Laptop)

- [ ] Create `web-app/.env.local` with project ID and agent ID
- [ ] Run `npm install && npm run dev`
- [ ] Open http://localhost:3000 and test chat with Spend IQ agent

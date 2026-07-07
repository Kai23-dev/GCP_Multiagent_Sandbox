# Running the agents locally (no Agent Engine / MCP toolbox / Cloud Run IAM)

Use this when the sandbox project can't provision the GitLab Terraform module,
the GenAI MCP toolbox, or Cloud Run invoker IAM. The agents run as plain
Python/ADK objects on your laptop; BigQuery and Gemini are reached directly
through your own `gcloud` credentials (ADC).

## One-time setup

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project <YOUR_SANDBOX_PROJECT_ID>

git clone https://github.com/Kai23-dev/GCP_Multiagent_Sandbox
cd GCP_Multiagent_Sandbox
git checkout fix/security-cleanup

pip install -e .
pip install -r infra/local_server/requirements.txt
```

Your sandbox account needs, at minimum:
- `roles/bigquery.dataViewer` + `roles/bigquery.jobUser` (query the dataset)
- `roles/aiplatform.user` (Gemini inference via Vertex AI)

## Configure once

```bash
cp infra/local_server/local.env.example infra/local_server/local.env
# edit local.env and set GOOGLE_CLOUD_PROJECT to your sandbox project id
```

## Run it — two terminals

Both terminals must `source` the same env file. This matters: `adk web` runs
the `spend_iq` orchestrator, which reads the `*_AGENT_RESOURCE` vars from **its
own** process to decide which sub-agents to build. If you set them in only one
terminal, `spend_iq` loads with zero sub-agents and can't delegate.

**Terminal 1 — local agent backend** (loads every agent; talks to BigQuery/Vertex AI directly):

```bash
set -a; source infra/local_server/local.env; set +a
export PORT=8001
python infra/local_server/main.py
```

Wait for `Successfully loaded agent: spend_iq_agent` (and the other agents) in
the log.

**Terminal 2 — ADK dev UI:**

```bash
set -a; source infra/local_server/local.env; set +a
adk web infra/agents
```

`VERTEX_API_BASE` in `local.env` points at `127.0.0.1:8001` (Terminal 1), so
`adk web` (on 8000) delegates to the backend. Open http://localhost:8000, pick
`spend_iq_agent`, and ask a question (e.g. "top 5 suppliers by spend this quarter").

> On Windows PowerShell, `source` isn't available. Either run under Git Bash /
> WSL, or load the file with:
> `Get-Content infra/local_server/local.env | ForEach-Object { if ($_ -and $_ -notmatch '^#') { $k,$v = $_.split('=',2); Set-Item "env:$k" $v } }`

## How it works

- `spend_iq_agent` and the domain agents (`auditor`, `buyer`, `trend`,
  `supplier_classification`, `financial_leakage`) still call each other over
  HTTP `streamQuery`, but `VERTEX_API_BASE` redirects those calls to the local
  FastAPI server in Terminal 1 instead of the real Reasoning Engine REST API.
  `contract_intelligence_agent` composes its sub-agents in-process (ADK
  `AgentTool`), so it needs no redirect.
- `sql_execution_agent` runs SQL directly via `bigquery.Client()` (ADC) when
  no `GENAI_MCP_URL` is configured, enforcing the same read-only guard used
  in production (`_is_read_only_sql`) purely in code — not just the prompt.
- `sql_generation_agent` / `validation_agent` reason from their static table
  docs (`instruction/table/*.md`) with no external tool dependency, so they
  work the same locally as in production.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `adk: command not found` | `google-adk` not installed in this environment — check `pip show google-adk`. |
| BigQuery `403 Forbidden` | Sandbox account is missing `bigquery.dataViewer` / `bigquery.jobUser` — an IAM ask, not a code issue. |
| Gemini call fails / 403 | Vertex AI API not enabled, or account missing `aiplatform.user` on the sandbox project. |
| Agent missing from `adk web` dropdown | Check Terminal 1's startup log for `Failed to load agent: <name>` — the traceback names the missing import. |
| Port 8000 already in use | `adk web` and the local server both default to 8000 — keep the local server on `PORT=8001` (or any free port) and point `VERTEX_API_BASE` at it. |

## Optional: point the existing Next.js web-app at it instead of `adk web`

```bash
# web-app/.env.local
AGENT_BACKEND_URL=http://localhost:8001
```
Then use `spend_iq_agent` as the `agentId` when calling `/api/agent-engine` or
`/api/agent-engine-stream`.

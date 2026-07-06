"""Auditor Agent - orchestrates SQL generation, validation, and execution for audit queries."""
from __future__ import annotations

import json
import logging
import os
import time
import traceback

import google.auth
import requests
import vertexai
from google.adk.agents import Agent
from google.api_core import exceptions as gapi_exceptions
from google.auth.transport.requests import Request as AuthRequest
from google.genai import types
from vertexai.agent_engines import AdkApp

# OpenTelemetry for distributed tracing across agents
from opentelemetry import trace
from opentelemetry.propagate import inject as otel_inject

tracer = trace.get_tracer('auditor_agent', '1.0.0')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('AUDITOR')

# Initialize Vertex AI
vertexai.init(
    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    api_transport="rest",
)
logger.info("au===== Vertex AI initialized (project=%s, location=%s)",
            os.environ.get("GOOGLE_CLOUD_PROJECT"),
            os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"))

# Cache for remote agent clients
_REMOTE_AGENTS = {}

# Sub-agent resource configuration
SQL_GENERATION_AGENT_RESOURCE = os.environ.get("SQL_GENERATION_AGENT_RESOURCE", "")
VALIDATION_AGENT_RESOURCE = os.environ.get("VALIDATION_AGENT_RESOURCE", "")
SQL_EXECUTION_AGENT_RESOURCE = os.environ.get("SQL_EXECUTION_AGENT_RESOURCE", "")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

logger.info("au===== Sub-agents configured: sql_gen=%s, validation=%s, sql_exec=%s",
            bool(SQL_GENERATION_AGENT_RESOURCE),
            bool(VALIDATION_AGENT_RESOURCE),
            bool(SQL_EXECUTION_AGENT_RESOURCE))


def _call_remote_agent(resource_name: str, query: str) -> str:
    """Call a remote agent's stream_query via direct HTTP POST."""
    max_attempts = int(os.environ.get("REMOTE_AGENT_MAX_ATTEMPTS", "3"))
    base_sleep_s = float(os.environ.get("REMOTE_AGENT_RETRY_BASE_SLEEP_S", "0.5"))

    # Extract agent name from resource for logging
    agent_name = resource_name.split("/")[-1] if resource_name else "unknown"

    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info("au===== Calling remote agent (attempt %d/%d): %s", attempt, max_attempts, agent_name)
            logger.debug("au===== Query length: %d chars", len(query) if query else 0)

            # Get auth token
            creds, _ = google.auth.default()
            creds.refresh(AuthRequest())
            token = creds.token

            # Inject W3C trace context so child agent joins the same trace
            trace_ctx = trace.get_current_span().get_span_context()
            trace_id = format(trace_ctx.trace_id, '032x') if trace_ctx.trace_id else ''

            # Build the REST API URL (honor VERTEX_API_BASE for local/GKE loopback)
            base_url = os.environ.get("VERTEX_API_BASE", f"https://{GOOGLE_CLOUD_LOCATION}-aiplatform.googleapis.com")
            api_endpoint = f"{base_url}/v1beta1/{resource_name}:streamQuery"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            otel_inject(headers)  # adds traceparent, tracestate

            payload = {
                "input": {
                    "message": query,
                    "user_id": "auditor",
                },
                "class_method": "stream_query",
            }

            resp = requests.post(api_endpoint, json=payload, headers=headers, stream=True)
            logger.info("au===== HTTP response: %d", resp.status_code)

            if resp.status_code != 200:
                error_text = resp.text[:500]
                logger.error("au===== HTTP error: %s", error_text)
                if resp.status_code in (500, 503):
                    raise gapi_exceptions.InternalServerError(f"HTTP {resp.status_code}: {error_text}")
                raise RuntimeError(f"HTTP {resp.status_code}: {error_text}")

            # Parse streamed JSON response
            responses = []
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded_line = line.decode("utf-8", errors="replace").strip()
                if not decoded_line:
                    continue

                try:
                    data = json.loads(decoded_line)
                except json.JSONDecodeError:
                    continue

                # Extract text from response structure
                if isinstance(data, dict):
                    output = data.get("output", data)
                    if isinstance(output, dict):
                        content = output.get("content", {})
                        if isinstance(content, dict):
                            parts = content.get("parts", [])
                            for part in parts:
                                if isinstance(part, dict) and "text" in part:
                                    responses.append(part["text"])
                                # Log function calls for testing
                                if isinstance(part, dict) and "function_call" in part:
                                    fc = part["function_call"]
                                    logger.info("au===== Tool call: %s", fc.get("name", "unknown"))
                                    # Log SQL query if present
                                    args = fc.get("args", {})
                                    for key in ["query", "sql", "sql_query"]:
                                        if key in args and args[key].strip().upper().startswith(("SELECT", "WITH")):
                                            logger.info("au===== SQL Query:%s", args[key].replace('\n', ' '))

            result = "\n".join(responses) if responses else "No response from agent"
            logger.info("au===== Response received: %d chars", len(result))
            return result

        except (gapi_exceptions.InternalServerError, gapi_exceptions.ServiceUnavailable) as e:
            last_exc = e
            logger.warning("au===== Transient error (attempt %d/%d): %s", attempt, max_attempts, e)
            if attempt < max_attempts:
                sleep_s = base_sleep_s * (2 ** (attempt - 1))
                time.sleep(sleep_s)
                continue
            break
        except Exception as e:
            last_exc = e
            logger.error("au===== Error calling remote agent: %s\n%s", e, traceback.format_exc())
            break

    return f"Error calling remote agent: {type(last_exc).__name__}: {last_exc}"


def sql_generation_agent(query: str) -> str:
    """Query the SQL Generation agent to determine which BigQuery tables to use.

    Args:
        query: Natural language query asking which tables to use for a question.

    Returns:
        Response from the SQL Generation agent with table recommendations.
    """
    if not SQL_GENERATION_AGENT_RESOURCE:
        return "SQL Generation agent is not configured"
    logger.info("au===== Delegating to sql_generation_agent")
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{SQL_GENERATION_AGENT_RESOURCE}"
    return _call_remote_agent(resource, query)


def validation_agent(query: str) -> str:
    """Query the Validation agent to validate a SQL query before execution.

    Args:
        query: SQL query to validate.

    Returns:
        Response from the Validation agent with validation results.
    """
    if not VALIDATION_AGENT_RESOURCE:
        return "Validation agent is not configured"
    logger.info("au===== Delegating to validation_agent")
    # Log the SQL being validated
    if query and query.strip().upper().startswith(("SELECT", "WITH")):
        logger.info("au===== SQL to validate:\n%s", query)
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{VALIDATION_AGENT_RESOURCE}"
    return _call_remote_agent(resource, query)


def sql_execution_agent(query: str) -> str:
    """Query the SQL Execution agent to execute a validated SQL query.

    Args:
        query: Validated SQL query to execute.

    Returns:
        Response from the SQL Execution agent with query results.
    """
    if not SQL_EXECUTION_AGENT_RESOURCE:
        return "SQL Execution agent is not configured"
    logger.info("au===== Delegating to sql_execution_agent")
    # Log the SQL being executed
    if query and query.strip().upper().startswith(("SELECT", "WITH")):
        logger.info("au===== SQL to execute:\n%s", query)
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{SQL_EXECUTION_AGENT_RESOURCE}"
    return _call_remote_agent(resource, query)


# Collect available remote agent tools
remote_agent_tools = []
if SQL_GENERATION_AGENT_RESOURCE:
    remote_agent_tools.append(sql_generation_agent)
if VALIDATION_AGENT_RESOURCE:
    remote_agent_tools.append(validation_agent)
if SQL_EXECUTION_AGENT_RESOURCE:
    remote_agent_tools.append(sql_execution_agent)

logger.info("au===== Remote agent tools configured: %d", len(remote_agent_tools))

system_instruction = """
You are an Auditor Agent specialized in audit and compliance data analysis. Your role is to orchestrate data queries by delegating to specialized sub-agents and providing expert audit insights based on the results.

## CRITICAL RULE: VALIDATION BEFORE EXECUTION

**NEVER call sql_execution_agent if validation_agent returns INVALID status.**

**This is a mandatory gating condition:**
- Validation status VALID → Proceed to execution
- Validation status INVALID → STOP. Return to sql_generation_agent for fixes. DO NOT execute.

**Violating this rule will result in wrong answers and data corruption.**

## Your Capabilities
- Interpret audit and compliance questions
- Orchestrate data retrieval through specialized sub-agents
- Analyze query results through an audit lens
- Provide insights on compliance, audit trails, internal controls, and regulatory reporting

## Available Sub-Agents

You have three specialized sub-agents that work sequentially to answer data questions:

1. **sql_generation_agent** - Table Selection Expert
   - When to use: At the start of ANY data question
   - Purpose: Analyzes the question and recommends which tables/columns to query
   - Input: Natural language question about the data needed

2. **validation_agent** - SQL Validator
   - When to use: After you generate SQL, BEFORE execution (MANDATORY)
   - Purpose: Validates SQL syntax, table names, column names, and query structure
   - Input: The SQL query you generated
   - Output: VALID or INVALID status

3. **sql_execution_agent** - Query Executor
   - When to use: ONLY after validation returns VALID status
   - Purpose: Executes validated SQL and returns formatted results with statistics
   - Input: Validated SQL query
   - **BLOCKED IF:** Validation status is INVALID

**Important:** You CANNOT execute SQL directly. All execution must go through sql_execution_agent AFTER validation passes.

## Standard Workflow

For any data question, follow this workflow strictly:

1. **Delegate to SQL Generation Agent**
   - Call sql_generation_agent with the user's question
   - Receive table and column recommendations
   - Based on recommendations, write a SQL query
   - Ensure it addresses the user's question

2. **Delegate to Validation Agent (MANDATORY GATE)**
   - Call validation_agent with SQL query generated by sql_generation_agent
   - Review validation feedback carefully
   - **If validation returns VALID:**
     - Proceed to step 3
   - **If validation returns INVALID:**
     - DO NOT proceed to step 3
     - DO NOT call sql_execution_agent
     - Return to step 1: Ask sql_generation_agent to fix the SQL based on validation feedback
     - Repeat steps 1 and 2 until validation returns VALID
   - **If validation returns ERROR, "No response from agent", or any unexpected response:**
     - This indicates a transient infrastructure issue with the validation service
     - Retry calling validation_agent up to 2 more times (3 total attempts)
     - If validation still fails after retries, SKIP validation and proceed to step 3 with caution
     - When skipping validation due to service unavailability, note this in your final response to the user
     - DO NOT block the user indefinitely due to validation service issues

3. **Delegate to Execution Agent (ONLY IF VALIDATION PASSED)**
   - **PREREQUISITE:** validation_agent must have returned VALID status in step 2
   - Call sql_execution_agent with validated SQL, only give the SQL query, don't add anything to the query
   - Receive query results and execution statistics
   - **If execution fails:**
     - Return to step 1: Ask sql_generation_agent to fix the SQL based on execution feedback
     - Then repeat steps 2 and 3 (including re-validation)
   - **If execution passes:** Proceed to step 4

4. **Check if Additional Queries Are Needed**
   - Some questions require multiple separate queries (e.g., invoice lookup + payment confirmation, spend data + comparison data)
   - If the user's question has not been fully answered by the first query, repeat steps 1-3 for each additional query needed
   - Example: "Find invoice X and confirm if it was paid" needs: (a) GL query for invoice details, (b) AP query for payment status

5. **Analyze**
   - Interpret results through an audit/compliance lens
   - Provide actionable insights
   - If calculations are needed (savings estimates, percentages, totals), perform them on the query results
   - If the results are not relevant to the question, go back to step 1 and ask the sql_generation_agent to fix the SQL based on feedback
   - If the results are good, proceed to step 6

6. **Respond**
   - Use the results to answer the user's question
   - Cite specific data points from results
   - Include any calculations you performed with clear methodology
   - Note any limitations or uncertainties

To ensure consistent and accurate handling of date formats in SQL queries, I will integrate the following internal protocol into my workflow:

**Auditor Agent Date Handling Protocol**

When processing any user query that involves date columns (e.g., filtering by date range, aggregating by period, comparing dates), I will adhere strictly to the following protocol:

1.  **Initial Date Format Discovery:**
    *   Before generating the primary SQL query for the user's request, I will execute a preliminary `SELECT DISTINCT <date_column> FROM <table> LIMIT N` query on the identified date column(s).
    *   I will analyze the results of this preliminary query to ascertain the precise date format(s) present in the data and identify any inconsistencies (e.g., mixed formats, non-date strings, nulls).

2.  **SQL Generation with Robust Date Parsing:**
    *   I will instruct the `sql_generation_agent` to construct the SQL query using date parsing functions (e.g., `PARSE_DATE`, `PARSE_TIMESTAMP`) that explicitly specify the *exact* format string(s) identified in step 1.
    *   If multiple formats are detected or if there's a risk of malformed data, I will prioritize robust parsing methods like `SAFE_CAST` or `TRY_PARSE_DATE`/`TRY_PARSE_TIMESTAMP` to prevent query failures and handle invalid entries gracefully.
    *   I will ensure that any date literals used in the query (e.g., for comparison) are also in a format compatible with the parsing function or are explicitly cast.

3.  **Validation and Iterative Refinement:**
    *   If the `validation_agent` or `sql_execution_agent` returns an error specifically related to date format, parsing, or casting, I will immediately revert to step 1. I will re-sample the date column if necessary, re-evaluate the format, and instruct the `sql_generation_agent` to revise the SQL query with the corrected parsing logic.

4.  **Transparency in Response:**
    *   In the final response to the user, I will explicitly state the identified date format of the column(s) and any assumptions made during parsing, especially if inconsistencies were found.

## Multi-Query Workflow

Some user questions require multiple separate SQL queries to fully answer. When a question requires multiple queries, run the full SQL generation → validation → execution workflow for EACH query separately. Combine the results in your final analysis.

### MANDATORY: Invoice Lookup (find invoice / P&L lookup / GL lookup)

When the user asks to find an invoice, look up an invoice in the P&L/GL, or confirm payment for an invoice, you MUST run EXACTLY TWO queries in this order:

**Query 1 — GL Details (MUST run FIRST):**
Ask sql_generation_agent: "Find invoice #<NUMBER> in XXC_GL_SUMMARY. Use SELECT DISTINCT with location, facility_description, account, account_name, period_name. Filter with SAFE_CAST(account AS INT64) > 5000, TRIM(ledger_id) = '1', period_name = 'OCT-25'. Join XXC_GL_DIV_REG_FAC for facility description."

**Query 2 — Payment Confirmation (run SECOND):**
Ask sql_generation_agent: "Check payment status for invoice <NUMBER> using AP_INVOICES_ALL joined with AP_INVOICE_PAYMENTS_ALL and AP_CHECKS_ALL. Use INVOICE_NUM (not invoice_number) for the AP tables. Select invoice_num, invoice_amount, amount_paid, payment_status_flag, check_number, check_date, check_amount, status_lookup_code."

**CRITICAL:** Do NOT skip Query 1. Do NOT run only Query 2. The user needs the GL details (location, account, period) which only exist in XXC_GL_SUMMARY.

### Other Multi-Query Scenarios
- **Savings estimation / vendor consolidation:** First query spend data by vendor, then perform calculations on the results.
- **Cross-table analysis:** Query different table groups (GL vs AP) separately when they answer different parts of the question.

## Calculations and Analytical Queries

When users ask for calculations (savings estimates, percentages, projections, aggregations with thresholds):
1. First retrieve the raw data through the standard SQL workflow
2. Perform the mathematical calculations yourself based on the query results
3. Present both the raw data AND your calculated results
4. Clearly state any assumptions made in your calculations

**Example:** For "estimate 3% savings on consolidated spend from tail suppliers":
1. Query all vendors on the GL account (single query joining XXC_GL_SUMMARY to AP_SUPPLIERS for real vendor names)
2. From the results, identify which are "tail" suppliers vs "preferred" based on the user's question
3. Present three sections in the response:
   - **Tail Supplier Identification**: Each tail supplier with their spend from the query results
   - **Consolidation Impact**: Total tail spend and how consolidating changes the top supplier landscape
   - **Negotiated Discount Savings**: Total Tail Spend × Discount Rate = Potential Annual Savings

## Table Name Mapping

Users may refer to tables by informal names. Always map to actual tables:
- "XXC_GL_SUMMARY_OCT_2025" or similar month/year suffixed names → Use `XXC_GL_SUMMARY` with period_name filter
- "GL" / "General Ledger" / "P&L" → `XXC_GL_SUMMARY`
- "AP" / "Accounts Payable" → Relevant AP table

Never tell the user a table doesn't exist if they use an informal name. Map it to the correct actual table.

## FINAL CHECK — Before Responding

Before generating your final response, verify:
1. If the user asked to find/look up an invoice: Did you run BOTH Query 1 (XXC_GL_SUMMARY for GL details) AND Query 2 (AP tables for payment)? If you only ran one query, STOP and run the missing query.
2. If you queried XXC_GL_SUMMARY: Does the SQL include `TRIM(ledger_id) = '1'`, `period_name = 'OCT-25'`, and `SELECT DISTINCT` (for non-aggregation)?
3. If the user asked about expenses/spend with a category name: Did you use `glrpt_category` (not SUPER_CATEGORY)?

## Response Guidelines

- **Always present query results in a markdown table format.** Do NOT use bulleted lists, numbered lists, or paragraph text to show data rows. Example:

| Location | Location Description | Account | Account Name | Time Period |
|---|---|---|---|---|
| 03056 | Some Facility Name | 7620 | Patient Morale Items-No Food | OCT-25 |

- Be concise yet comprehensive in your analysis
- Always cite specific values and metrics from query results
- Flag any anomalies or compliance concerns
- Acknowledge uncertainty when data is incomplete or ambiguous
- Focus on audit-relevant insights (risk, controls, compliance, patterns)
- Use clear, professional language appropriate for audit reporting

## Handling Uncertainty

If you cannot provide a definitive answer or compute the requested information, it is acceptable and expected to respond with "I don't know" or "I can't compute that." Explain concisely why you cannot fulfill the request (e.g., insufficient data, out of scope, missing tool capability) without attempting to fabricate an answer or offer alternative approaches.

## Sub-Agent Instructions

When a user asks a sub-agent a question about its own internal capabilities, tools, or metadata (e.g., 'List your tools', 'What can you do?'), prioritize delegating the query directly to that specific sub-agent. Do not assume a sub-agent cannot answer such a meta-query, even if it falls outside its primary described function. Default to attempting such harmless, introspective queries to leverage the sub-agent's full potential and internal knowledge.
"""

# Define the auditor agent
root_agent = Agent(
    name="auditor_agent",
    model="gemini-2.5-flash",
    description="Agent specialized in audit and compliance queries using BigQuery tools for audit data analysis.",
    instruction=system_instruction,
    tools=remote_agent_tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        http_options=types.HttpOptions(
            headers={
                "X-Vertex-AI-LLM-Request-Type": "shared",
                "X-Vertex-AI-LLM-Shared-Request-Type": "priority",
            }
        ),
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_MEDIUM_AND_ABOVE",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_MEDIUM_AND_ABOVE",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_MEDIUM_AND_ABOVE",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_MEDIUM_AND_ABOVE",
            ),
        ],
    ),
)

# Wrap the agent with AdkApp for Agent Engine deployment
adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
)

logger.info("au===== Auditor Agent initialization complete")

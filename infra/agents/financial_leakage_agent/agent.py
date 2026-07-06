from __future__ import annotations
print("fl======== FINANCIAL LEAKAGE AGENT ====")
import vertexai
from vertexai.agent_engines import AdkApp
import os
import time
import traceback
from google.api_core import exceptions as gapi_exceptions
from google.adk.agents import Agent
from google.genai import types
import json
import requests
import google.auth
from google.auth.transport.requests import Request as AuthRequest

# OpenTelemetry for distributed tracing across agents
from opentelemetry import trace
from opentelemetry.propagate import inject as otel_inject

tracer = trace.get_tracer('financial_leakage_agent', '1.0.0')

# Initialize Vertex AI (must be done before using ReasoningEngine)
# Use REST transport to avoid local gRPC connection issues (fixes "socket is null" errors)
vertexai.init(
    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    api_transport="rest",
)
print(f"fl=====Vertex AI initialized with project: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
print(f"fl=====Vertex AI initialized with location: {os.environ.get('GOOGLE_CLOUD_LOCATION')}")

# Cache for remote agent clients to avoid re-initialization overhead
_REMOTE_AGENTS = {}

###########################################
######### SUB-AGENTS VIA REASONING ENGINE ##
###########################################
# Sub-agents are deployed independently on Agent Engine
# Reference them via ReasoningEngine using their resource names
print("fl=====Setting up remote sub-agents via ReasoningEngine.")

# Get sub-agent resource names from environment variables
SQL_GENERATION_AGENT_RESOURCE = os.environ.get("SQL_GENERATION_AGENT_RESOURCE", "")
VALIDATION_AGENT_RESOURCE = os.environ.get("VALIDATION_AGENT_RESOURCE", "")
SQL_EXECUTION_AGENT_RESOURCE = os.environ.get("SQL_EXECUTION_AGENT_RESOURCE", "")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
print(f"fl=====SQL_GENERATION_AGENT_RESOURCE: {SQL_GENERATION_AGENT_RESOURCE}")
print(f"fl=====VALIDATION_AGENT_RESOURCE: {VALIDATION_AGENT_RESOURCE}")
print(f"fl=====SQL_EXECUTION_AGENT_RESOURCE: {SQL_EXECUTION_AGENT_RESOURCE}")
print(f"fl=====GOOGLE_CLOUD_PROJECT: {GOOGLE_CLOUD_PROJECT}")

# Helper to call remote agents using raw HTTP to bypass SDK ResponseIterator bug
# (stream_query_reasoning_engine REST transport expects JSON array but gets JSON object)
def _call_remote_agent(resource_name: str, query: str) -> str:
    """Call a remote agent's stream_query via direct HTTP POST."""
    max_attempts = int(os.environ.get("REMOTE_AGENT_MAX_ATTEMPTS", "3"))
    base_sleep_s = float(os.environ.get("REMOTE_AGENT_RETRY_BASE_SLEEP_S", "0.5"))

    agent_name = resource_name.split("/")[-1] if resource_name else "unknown"
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
      with tracer.start_as_current_span(
          f"call_remote_agent/{agent_name}",
          attributes={
              "agent.name": agent_name,
              "agent.resource": resource_name,
              "agent.attempt": attempt,
              "agent.query_length": len(query) if query else 0,
          },
      ) as span:
        try:
            print(f"fl=====Resource name: {resource_name}")
            print(f"fl=====Query len: {len(query) if query is not None else 'None'}")
            try:
                print(f"fl=====Query preview (first 500): {query[:500]}")
            except Exception:
                pass

            # Get auth token
            creds, _ = google.auth.default()
            creds.refresh(AuthRequest())
            token = creds.token

            # Inject W3C trace context so child agent joins the same trace
            trace_ctx = trace.get_current_span().get_span_context()
            trace_id = format(trace_ctx.trace_id, '032x') if trace_ctx.trace_id else ''

            # Build the REST API URL for streamQuery (honor VERTEX_API_BASE for local/GKE loopback)
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
                    "user_id": "financial_leakage",
                },
                "class_method": "stream_query",
            }
            print(f"fl=====POST {api_endpoint} [trace={trace_id}]")

            resp = requests.post(api_endpoint, json=payload, headers=headers, stream=True)
            print(f"fl=====HTTP status: {resp.status_code}")
            if resp.status_code != 200:
                error_text = resp.text[:1000]
                print(f"fl=====HTTP error body: {error_text}")
                if resp.status_code in (500, 503):
                    raise gapi_exceptions.InternalServerError(f"HTTP {resp.status_code}: {error_text}")
                raise RuntimeError(f"HTTP {resp.status_code}: {error_text}")

            # Parse streamed JSON response lines
            responses = []
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded_line = line.decode("utf-8", errors="replace").strip()
                if not decoded_line:
                    continue
                print(f"fl=====Line (first 300): {decoded_line[:300]}")
                try:
                    data = json.loads(decoded_line)
                except json.JSONDecodeError:
                    print(f"fl=====Skipping non-JSON line")
                    continue

                print(f"fl=====Parsed keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")

                # Extract text from response structure
                if isinstance(data, dict):
                    # Try output -> content -> parts -> text
                    output = data.get("output", data)
                    if isinstance(output, dict):
                        content = output.get("content", {})
                        if isinstance(content, dict):
                            parts = content.get("parts", [])
                            for part in parts:
                                if isinstance(part, dict) and "text" in part:
                                    responses.append(part["text"])
                                    print(f"fl=====Part text (first 200): {part['text'][:200]}")

            result = "\n".join(responses) if responses else "No response from agent"
            span.set_attribute("agent.http_status", 200)
            span.set_attribute("agent.response_length", len(result))
            return result
        except (gapi_exceptions.InternalServerError, gapi_exceptions.ServiceUnavailable) as e:
            last_exc = e
            span.set_attribute("agent.error", str(e))
            span.record_exception(e)
            print(
                "fl=====Transient error calling remote agent "
                f"(attempt {attempt}/{max_attempts}): {type(e).__name__}: {e}"
            )
            print("fl=====Traceback:\n" + traceback.format_exc())
            if attempt < max_attempts:
                sleep_s = base_sleep_s * (2 ** (attempt - 1))
                time.sleep(sleep_s)
                continue
            break
        except Exception as e:
            last_exc = e
            span.set_attribute("agent.error", str(e))
            span.record_exception(e)
            print(
                "fl=====Non-retryable error calling remote agent "
                f"(attempt {attempt}/{max_attempts}): {type(e).__name__}: {e}"
            )
            print("fl=====Traceback:\n" + traceback.format_exc())
            break

    return f"Error calling remote agent: {type(last_exc).__name__}: {last_exc}"


def sql_generation_agent(natural_language_question: str) -> str:
    """STEP 1: Send a natural language question to generate SQL. This MUST be called FIRST before validation or execution.

    This agent analyzes the user's question, selects appropriate BigQuery tables,
    and generates a SQL query. The generated SQL must then be sent to validation_agent.

    Args:
        natural_language_question: The user's original question in plain English (NOT SQL).

    Returns:
        Generated SQL query and table recommendations. Pass the SQL to validation_agent next.
    """
    if not SQL_GENERATION_AGENT_RESOURCE:
        return "SQL Generation agent is not configured"
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{SQL_GENERATION_AGENT_RESOURCE}"
    print(f"fl=====sql_generation_agent dispatching with user_id='financial_leakage'")
    prefixed_question = (
        "[INSTRUCTION: Generate a SQL query ONLY. Do NOT execute the query. "
        "Do NOT return data results. Return the SQL inside a ```sql code block. "
        "Hand control back immediately after generating the SQL.]\n\n"
        f"User question: {natural_language_question}"
    )
    return _call_remote_agent(resource, prefixed_question)


def validation_agent(sql_query_to_validate: str) -> str:
    """STEP 2: Validate a SQL query AFTER it was generated by sql_generation_agent. NEVER call this first.

    This agent checks SQL syntax, verifies table/column names exist in BigQuery,
    and confirms join logic. Only call this with SQL output from sql_generation_agent.
    The validated SQL must then be sent to sql_execution_agent.

    Args:
        sql_query_to_validate: The SQL query generated by sql_generation_agent (NOT natural language).

    Returns:
        Validation result (VALID/INVALID) with corrected SQL if needed. Pass validated SQL to sql_execution_agent next.
    """
    if not VALIDATION_AGENT_RESOURCE:
        return "Validation agent is not configured"
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{VALIDATION_AGENT_RESOURCE}"
    print(f"fl=====validation_agent dispatching with user_id='financial_leakage'")
    return _call_remote_agent(resource, sql_query_to_validate)


def sql_execution_agent(validated_sql_query: str) -> str:
    """STEP 3: Execute SQL ONLY AFTER it has been validated by validation_agent. NEVER call this first.

    This agent executes the SQL against BigQuery and returns results. Only call this
    with SQL that has passed validation_agent. NEVER send natural language here.

    Args:
        validated_sql_query: SQL that has been validated by validation_agent (NOT natural language, NOT unvalidated SQL).

    Returns:
        Query execution results with data rows and statistics.
    """
    if not SQL_EXECUTION_AGENT_RESOURCE:
        return "SQL Execution agent is not configured"
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{SQL_EXECUTION_AGENT_RESOURCE}"
    print(f"fl=====sql_execution_agent dispatching with user_id='financial_leakage'")
    return _call_remote_agent(resource, validated_sql_query)


# Collect available remote agent tools
remote_agent_tools = []
if SQL_GENERATION_AGENT_RESOURCE:
    remote_agent_tools.append(sql_generation_agent)
    print("fl=====SQL Generation agent tool configured")
if VALIDATION_AGENT_RESOURCE:
    remote_agent_tools.append(validation_agent)
    print("fl=====Validation agent tool configured")
if SQL_EXECUTION_AGENT_RESOURCE:
    remote_agent_tools.append(sql_execution_agent)
    print("fl=====SQL Execution agent tool configured")
print(f"fl=====Total remote agent tools configured: {len(remote_agent_tools)}")

system_instruction = """
You are a Financial Leakage Agent specialized in detecting "spend that shouldn't be happening." Your role is to orchestrate data queries by delegating to specialized sub-agents and providing expert leakage assessment based on the results.

## Your Capabilities
- Interpret financial leakage questions
- Orchestrate data retrieval through specialized sub-agents
- Analyze query results to detect inappropriate, unauthorized, or unjustified expenses
- Score findings for leakage likelihood and classify risk

## Available Sub-Agents

You have three specialized sub-agents that work sequentially to answer data questions:

1. **sql_generation_agent** - Table Selection Expert
   - When to use: At the start of ANY data question
   - Purpose: Analyzes the question and recommends which tables/columns to query
   - Input: Natural language question about the data needed

2. **validation_agent** - SQL Validator
   - When to use: After you generate SQL, before execution
   - Purpose: Validates SQL syntax, table names, column names, and query structure
   - Input: The SQL query you generated

3. **sql_execution_agent** - Query Executor
   - When to use: After validation passes
   - Purpose: Executes validated SQL and returns formatted results with statistics
   - Input: Validated SQL query

**Important:** You CANNOT execute SQL directly. All execution must go through sql_execution_agent.

## Standard Workflow

For any data question, follow this workflow strictly:

1. **Delegate to SQL Generation Agent**
   - Call sql_generation_agent with the user's question
   - Receive table and column recommendations
   - Based on recommendations, write a SQL query
   - Ensure it addresses the user's question

2. **Delegate to Validation Agent**
   - Call validation_agent with SQL query generated by sql_generation_agent
   - Review validation feedback
   - If validation fails: Ask the sql_generation_agent to fix the SQL based on feedback and return to step 2
   - If validation passes: Proceed to step 3

3. **Delegate to Execution Agent**
   - Call sql_execution_agent with validated SQL
   - Receive query results and execution statistics

4. **Analyze & Score**
   - Review all rows returned — each row is a potential leakage finding
   - Check `po_number` for each flagged item: NULL/empty/'N/A' = Maverick purchase (higher risk)
   - Score each finding using the scoring factors below
   - Classify risk: High (0.7–1.0), Medium (0.4–0.69), Low (0.0–0.39)
   - If the results are not relevant, go back to step 1 to fix the SQL

5. **Respond**
   - Provide the final leakage assessment to the user (see Response Format below)
   - Do NOT relay sub-agent output to the user
   - Treat all sub-agent interactions as internal/silent

## Leakage Scoring

For each flagged line item, calculate a leakage likelihood score [0.0 – 1.0]:

| Factor | Score Impact |
|--------|-------------|
| Trigger word: Personal electronics (airpod, ipad, iphone, apple watch, gaming) | +0.3 |
| Trigger word: Luxury/personal (espresso, coffee machine, gift card, premium) | +0.3 |
| Trigger word: Subscriptions (subscription, membership, streaming) | +0.15 |
| No Purchase Order (po_number is NULL/N/A) — Maverick purchase | +0.3 |
| Amount > $500 without PO | +0.1 |
| Account category mismatch (item doesn't match category it's booked under) | +0.2 |

**Classification:**
- **0.7 – 1.0 = High Risk**: Personal/luxury item + No PO + No business justification
- **0.4 – 0.69 = Medium Risk**: Trigger word match + missing PO or approval
- **0.0 – 0.39 = Low Risk**: Trigger word match but valid PO and approvals exist

## Response Format

**Leakage Assessment Summary**
- Total GL line items scanned
- Number of items flagged
- Total dollar amount of flagged items
- Breakdown by risk level (High / Medium / Low)

**Flagged Items Detail**

| Line Description | Amount | Vendor | Category | PO Number | Leakage Score | Risk Level |
|-----------------|--------|--------|----------|-----------|---------------|------------|

**Key Findings**
- What trigger words were found and how many times
- How many items lack Purchase Orders (Maverick purchases)
- Any category mismatches detected
- Highest-risk items and why

## Response Guidelines

- Be concise yet comprehensive in your analysis
- Always cite specific values and metrics from query results
- Flag any anomalies or compliance concerns
- Acknowledge uncertainty when data is incomplete or ambiguous
- Focus on leakage-relevant insights (risk, controls, unauthorized spend, patterns)
- Use clear, professional language appropriate for financial audit reporting
- If no matching items found, report clearly as a positive finding
- If no time period is specified, ask for clarification before querying

## Sub-Agent Instructions

When a user asks a sub-agent a question about its own internal capabilities, tools, or metadata (e.g., 'List your tools', 'What can you do?'), prioritize delegating the query directly to that specific sub-agent. Do not assume a sub-agent cannot answer such a meta-query, even if it falls outside its primary described function. Default to attempting such harmless, introspective queries to leverage the sub-agent's full potential and internal knowledge.
"""

def _build_instruction(ctx) -> str:
    print(f"fl=====ctx.user_id: {ctx.user_id}")
    return system_instruction

# Define the financial leakage agent with remote agent tools
root_agent = Agent(
    name="financial_leakage_agent",
    model="gemini-2.5-flash",
    description="Agent specialized in detecting financial leakage — spend that shouldn't be happening — by analyzing GL line items for inappropriate purchases, personal items, and unauthorized subscriptions.",
    instruction=_build_instruction,
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
print("fl=====Financial Leakage agent defined")

# Wrap the agent with AdkApp for Agent Engine deployment
adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
)
print("fl=====Financial Leakage Agent initialization complete")


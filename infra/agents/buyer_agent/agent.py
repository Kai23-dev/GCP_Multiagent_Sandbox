from __future__ import annotations
import vertexai
from vertexai.agent_engines import AdkApp
from vertexai.preview import reasoning_engines
from google.cloud.aiplatform_v1beta1 import types as aip_types
import os
from google.adk.agents import Agent
from google.genai import types
import json
import requests
import google.auth
from google.auth.transport.requests import Request as AuthRequest

# OpenTelemetry for distributed tracing across agents
from opentelemetry import trace
from opentelemetry.propagate import inject as otel_inject

tracer = trace.get_tracer('buyer_agent', '1.0.0')

print("bu======== BUYER AGENT ===")

# Initialize Vertex AI (must be done before using ReasoningEngine)
vertexai.init(
    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
)
print(f"bu=====Vertex AI initialized with project: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
print(f"bu=====Vertex AI initialized with location: {os.environ.get('GOOGLE_CLOUD_LOCATION')}")

###########################################
######### SUB-AGENTS VIA REASONING ENGINE ##
######### SUB-AGENTS VIA REASONING ENGINE ##
###########################################
# Sub-agents are deployed independently on Agent Engine
# Reference them via ReasoningEngine using their resource names
print("bu=====Setting up remote sub-agents via ReasoningEngine.")

# Get sub-agent resource names from environment variables
SQL_GENERATION_AGENT_RESOURCE = os.environ.get("SQL_GENERATION_AGENT_RESOURCE", "")
VALIDATION_AGENT_RESOURCE = os.environ.get("VALIDATION_AGENT_RESOURCE", "")
SQL_EXECUTION_AGENT_RESOURCE = os.environ.get("SQL_EXECUTION_AGENT_RESOURCE", "")
VISUALIZATION_AGENT_RESOURCE = os.environ.get("VISUALIZATION_AGENT_RESOURCE", "")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
print(f"bu=====SQL_GENERATION_AGENT_RESOURCE: {SQL_GENERATION_AGENT_RESOURCE}")
print(f"bu=====VALIDATION_AGENT_RESOURCE: {VALIDATION_AGENT_RESOURCE}")
print(f"bu=====SQL_EXECUTION_AGENT_RESOURCE: {SQL_EXECUTION_AGENT_RESOURCE}")
print(f"bu=====VISUALIZATION_AGENT_RESOURCE: {VISUALIZATION_AGENT_RESOURCE}")
print(f"bu=====GOOGLE_CLOUD_PROJECT: {GOOGLE_CLOUD_PROJECT}")

# Helper to call remote agents using lower-level API
def _call_remote_agent(resource_name: str, query: str) -> str:
    """Call a remote agent via ReasoningEngine using direct HTTP/REST API to avoid SDK parsing issues."""
    agent_name = resource_name.split("/")[-1] if resource_name else "unknown"
    with tracer.start_as_current_span(
        f"call_remote_agent/{agent_name}",
        attributes={
            "agent.name": agent_name,
            "agent.resource": resource_name,
            "agent.query_length": len(query) if query else 0,
        },
    ) as span:
      try:
        print(f"bu=====Resource name0: {resource_name}")
        
        # 1. Get Authentication Credentials
        creds, project = google.auth.default()
        auth_req = AuthRequest()
        creds.refresh(auth_req)
        token = creds.token
        
        # 2. Construct API URL
        parts = resource_name.split("/")
        location = "us-central1"
        if "locations" in parts:
             idx = parts.index("locations")
             if idx + 1 < len(parts):
                 location = parts[idx+1]

        # Inject W3C trace context so child agent joins the same trace
        trace_ctx = trace.get_current_span().get_span_context()
        trace_id = format(trace_ctx.trace_id, '032x') if trace_ctx.trace_id else ''

        base_url = os.environ.get("VERTEX_API_BASE", f"https://{location}-aiplatform.googleapis.com")
        api_endpoint = f"{base_url}/v1beta1/{resource_name}:streamQuery"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        otel_inject(headers)  # adds traceparent, tracestate
        
        payload = {
            "input": {
                "message": query,
                "user_id": "buyer",
            }
        }
        
        print(f"bu=====Calling API: {api_endpoint} [trace={trace_id}]")
        
        # 3. Execute Request
        response = requests.post(api_endpoint, json=payload, headers=headers, stream=True)
        
        if response.status_code != 200:
            error_text = response.text
            print(f"bu=====HTTP Error {response.status_code}: {error_text}")
            return f"Error calling remote agent (HTTP {response.status_code}): {error_text}"
            
        # 4. Process Stream
        responses = []
        print("bu=====Stream started")
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8').strip()
                if not decoded_line:
                    continue
                
                # Remove possible SSE prefix
                if decoded_line.startswith("data:"):
                    decoded_line = decoded_line[5:].strip()
                
                # Handle JSON Array markers if present
                if decoded_line == "[" or decoded_line == "]":
                    continue
                if decoded_line.endswith(","):
                    decoded_line = decoded_line[:-1]
                
                try:
                    data = json.loads(decoded_line)
                    print(f"bu=====Parsed Chunk: {data}")
                    
                    # Extract text content based on observation of SDK behavior
                    # Expected structure: {"content": {"parts": [{"text": "..."}]}}
                    if isinstance(data, dict):
                         content = data.get("content", {})
                         if isinstance(content, dict):
                             parts = content.get("parts", [])
                             for part in parts:
                                 if isinstance(part, dict) and "text" in part:
                                     responses.append(part["text"])
                                     print(f"bu=====Added text: {part['text']}")
                                 elif isinstance(part, str):
                                     responses.append(part)
                         elif isinstance(content, str):
                             responses.append(content)
                             
                except json.JSONDecodeError:
                    print(f"bu=====Skipping non-JSON line: {decoded_line}")
                    
        result = "".join(responses) if responses else "No response from agent"
        span.set_attribute("agent.http_status", 200)
        span.set_attribute("agent.response_length", len(result))
        return result

      except Exception as e:
        span.set_attribute("agent.error", str(e))
        span.record_exception(e)
        print(f"bu=====Exception in _call_remote_agent: {e}")
        return f"Error calling remote agent: {e}"


def sql_generation_agent(query: str) -> str:
    """Query the SQL Generation agent to determine which BigQuery tables to use.

    Args:
        query: Natural language query asking which tables to use for a question.

    Returns:
        Response from the SQL Generation agent with table recommendations.
    """
    if not SQL_GENERATION_AGENT_RESOURCE:
        return "SQL Generation agent is not configured"
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
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{SQL_EXECUTION_AGENT_RESOURCE}"
    return _call_remote_agent(resource, query)

def visualization_agent(query: str) -> str:
    """Query the Visualization agent to generate visualizations for a query.

    Args:
        query: Query to generate visualizations for.

    Returns:
        Response from the Visualization agent with visualization results.
    """
    if not VISUALIZATION_AGENT_RESOURCE:
        return "Visualization agent is not configured"
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{VISUALIZATION_AGENT_RESOURCE}"
    return _call_remote_agent(resource, query)


# Collect available remote agent tools
remote_agent_tools = []
if SQL_GENERATION_AGENT_RESOURCE:
    remote_agent_tools.append(sql_generation_agent)
    print("bu=====SQL Generation agent tool configured")
if VALIDATION_AGENT_RESOURCE:
    remote_agent_tools.append(validation_agent)
    print("bu=====Validation agent tool configured")
if SQL_EXECUTION_AGENT_RESOURCE:
    remote_agent_tools.append(sql_execution_agent)
    print("bu=====SQL Execution agent tool configured")
if VISUALIZATION_AGENT_RESOURCE:
    remote_agent_tools.append(visualization_agent)
    print("bu=====Visualization agent tool configured")
print(f"bu=====Total remote agent tools configured: {len(remote_agent_tools)}")

instruction = """
You are a specialized Buyer Agent responsible for procurement and purchasing data analysis. You orchestrate data queries by delegating to specialized sub-agents and provide expert procurement insights.
When delegating to sql_generation_agent - tell him to follow use case. You should delegate to sql_generation_agent with following defined SQL pattern (see examples in 1. section of workflow).
Only if you have enough information in history - eg. from any of previous result from SQL database - answer politely basing on it - do not hallucinate.
E.g. you have request about additional information about item - and you have these results from SQL database - only then you can answer.

## Available Sub-Agents

1. **sql_generation_agent** — Generates SQL queries from detailed natural language requests
2. **validation_agent** — Validates SQL syntax and structure before execution
3. **sql_execution_agent** — Executes validated SQL and returns results
4. **visualization_agent** — Generates visualizations for query results

**Important:** You CANNOT execute SQL directly. All execution must go through sql_execution_agent.

## Workflows

### Normal
For any data question:

1. **Call sql_generation_agent** with a DETAILED request. Do NOT ask vague questions like "which tables should I use?".
   Instead, describe exactly what data you need and what the SQL should do. Examples:
   - BAD: "Which tables should I use to check if invoice 10952157 is maverick?"
   - BAD: "Which tables should I use to get item description for invoice 10952157 and line 7?"
   - GOOD: "Generate SQL to classify invoice 10952157 as maverick or proper. Use your defined SQL pattern from Maverick Purchase Detection use case."
   - GOOD: "Generate SQL to get maverick vs proper spend summary. Use your defined SQL pattern from Maverick Purchase Detection use case."
   - GOOD: "Generate SQL to get item description for invoice 10952157 and line 7. Use your defined SQL pattern from Item Description use case."

2. **Call validation_agent** with the SQL returned by sql_generation_agent. If validation fails, call sql_generation_agent again with the feedback.

3. **Call sql_execution_agent** with the validated SQL.

4. **Analyze and respond** with procurement insights based on the results.

### Visualization
For any visualization requests:

1. Get needed data from sql_execution_agent response. If there are no data from response - tell it to user.

2. **Call visualization_agent** with DETAILED request.
   Describe exactly what should be visualized. Include:
   - what to visualize
   - form (type of chart)
   - title
   - should or should not be annotated values - add annotated values by default
   - x column name
   - y column name - always add units in [] brackets, e.g. Amount [$], if it is without units - use [-] e.g. Count [-]
   - with what data
   Examples:
   - BAD: "Visualize unmanaged and managed spent items"
   - BAD: "Visualize unmanaged and managed spent items from invoice 10952157"
   - BAD: "Visualize unmanaged and proper spent items from invoice 10952157 with annotated values on bar chart. Title: 'Unmanaged and Proper Spend Items for Invoice 10952157'"
   - GOOD: "Visualize unmanaged and proper spent items. It should be a bar chart with unmanaged and proper spent items on x-axis and count (of Proper vs Maverick) on y-axis.
   Add annotated values on the chart.
   Title: 'Unmanaged and Proper Spend Items for Invoice 10952157'
   x column name: Purchasing route
   y column name: Count [-]
   Data:
   | invoice_id | invoice_number | header_po_id | line_po_id | line_number | header_route | line_route |
   |:-----------|:---------------|:-------------|:-----------|:------------|:-------------|:-----------|
   | 10952157 | INV123456 | N/A | 1235910 | 1 | Maverick | Proper |
   | 10952157 | INV123456 | N/A | 1235910 | 10 | Maverick | Proper |
   | 10952157 | INV123456 | N/A | 1235910 | 2 | Maverick | Proper |
   | 10952157 | INV123456 | N/A | 1235910 | 3 | Maverick | Proper |
   | 10952157 | INV123456 | N/A | N/A | 4 | Maverick | Maverick |
   | 10952157 | INV123456 | N/A | 1235910 | 5 | Maverick | Proper |
   | 10952157 | INV123456 | N/A | 1235910 | 6 | Maverick | Proper |
   | 10952157 | INV123456 | N/A | 1235910 | 7 | Maverick | Proper |
   | 10952157 | INV123456 | N/A | 1235910 | 8 | Maverick | Proper |
   | 10952157 | INV123456 | N/A | 1235910 | 9 | Maverick | Proper |"

## Use cases to focus on:

### Maverick Purchase Detection

A **maverick** purchase is an invoice without a Purchase Order (AP → GL directly, bypassing procurement controls).
A **proper** purchase flows: Catalog → PO → AP → GL.

**Core detection:** `AP_INVOICES_ALL.po_header_id IS NULL or = 'N/A'` → Maverick.
**Line-level:** `AP_INVOICE_LINES_ALL.po_header_id IS NULL or = 'N/A'` → that line is maverick.

IMPORTANT RULE: If **Core detection** classifies an invoice as Maverick AND all items - lines from **Line-level** are classified as Maverick
-> then classify as **Maverick**. Else: classify as **Proper**
IMPORTANT RULE FOR sql_execution_agent output: If header_route and line_route is Maverick in ALL lines, then classify invoice as Maverick.
If header_route is Proper, then classify invoice as Proper, even if some lines are Maverick.
If header_route is Maverick but at least one line is Proper, then classify invoice as Proper.

When answering maverick questions:
- Classify an invoice as **Proper** (has PO) or **Maverick** (no PO)
- Report counts, dollar amounts, and maverick spend percentage
- For maverick invoices, recommend: vendor catalog onboarding, blanket PO investigation, procurement review for high-value items

## Maverick Purchase Detection — Response Format (MUST FOLLOW)

Your Maverick Purchase Detection responses must be concise, deterministic, and professional. Use the exact structure below.
Do not change provided note after 5) point. The note MUST be added in separate line in the response for this use case.

#### 1) Classification
- **Final classification:** `Maverick` or `Proper`
- **Rule applied:**
    - If `header_route` is `Proper` → Final is `Proper` (even if some lines are maverick)
    - If `header_route` is `Maverick` AND **all** `line_route` values are `Maverick` → Final is `Maverick`
    - If `header_route` is `Maverick` but **any** `line_route` is `Proper` → Final is `Proper`

#### 2) Evidence Summary
- **Header PO:** `header_po_id` (NULL/`N/A` implies Maverick at header)
- **Line PO coverage:** number of lines with `line_po_id` present vs missing (if available)

#### 3) Invoice Line Details (ADK Table)
Always include the following markdown table so ADK can render it. Populate one row per invoice line (sorted by `line_number`). If you only have one row (header-only result), still output a single-row table.

| Invoice ID | Invoice Number | Header PO ID | Line PO ID | Line Number |
|---|---|---|---|---|
| <invoice_id> | <invoice_number> | <header_po_id> | <line_po_id> | <line_number> |

**Column mapping (for parsing `sql_execution_agent` output):**
- `Invoice ID` → field `invoice_id`
- `Invoice Number` → field `invoice_number`
- `Header PO ID` → field `header_po_id`
- `Line PO ID` → field `line_po_id`
- `Line Number` → field `line_number`

**Validation:**
After you parse `sql_execution_agent` output - ensure that all fields are parsed correctly. If no - correct wrong ones. If sth is NULL or 'N/A' - write 'N/A' in a field.

#### 4) Procurement Interpretation
- 1–3 sentences explaining what the classification means operationally (e.g., “invoice bypassed PO controls” for Maverick).

#### 5) Recommended Next Action
- Provide 1–3 action bullets.
- If Maverick: prioritize catalog onboarding / blanket PO check / high-value review.

**Note:** *Discarded and cancelled lines are excluded from the response.*

### Item Description

Use case when user asks for an item:
- who bought it from PO perspective?
- for how much?
- who sold it?

If you prepare response from sql_execution_agent
- basing on SQL result list column values which you don't know, like on below examples (missing values are NULL or 'N/A').
- append unmodified Discarded-cancelled note only if discarded_flag or cancelled_flag is true / 'Y'
- tell for example 1:
"Item from line 7 from invoice of 10952157 number is from 1234 PO number. Cost: 56 USD.
Bought by 789 (buyer_id). Vendor ID: 090807 Vendor number: 5678. Supplier name: Example Top Supplier. The item description is: Controller1234e. Type of vendor is unknown."
- tell for example 2:
"Item from line 3 from invoice of 10952157 number. Cost: 120.
Bought by 789 (buyer_id). Vendor ID: 090807 Vendor number: 5678. Supplier name: Example Top Supplier. PO number, currency, type of vendor and item description are unknown."
- tell for example 3:
"Item from line 5 from invoice of 10952157 number is from 1234 PO number. Cost: 200 EUR.
Bought by 789 (buyer_id). Vendor ID: 090807. The item description is: PhoneABC. Vendor number, type of vendor and supplier name are unknown."
- tell for example 4:
"Item from line 7 from invoice of 10952157 number is from 1234 PO number. Cost: 56 USD.
Bought by 789 (buyer_id). Vendor ID: 090807 Vendor number: 5678, type: Example_vendor_type. Supplier name: Example Top Supplier. The item description is: ComputerXYZ."

#### Template version:
"Item from line --line_number-- from invoice of --invoice_number-- number is from --po_number-- PO number. Cost: --line_amount-- --currency_code--.
Bought by --buyer_id-- (buyer_id). Vendor ID: --vendor_id-- Vendor number: --vendor_number--, type: --vendor_type--. Supplier name: --supplier_name--. The item description is: --item_description--."

#### Discarded-cancelled note
Use only if discarded_flag or cancelled_flag is true / 'Y'. Never use if both of these flags are false / 'N'
Do not change format of this note when you are using it.
##### Examples:
*Please note that this item has been discarded.*
*Please note that this item has been discarded and cancelled.*
*Please note that this item has been cancelled.*

##### Example with rest of response - the note is separated with blank line, note is in italic font:
"Item from line 7 from invoice of 10952157 number is from 1234 PO number. Cost: 56 USD.
Bought by 789 (buyer_id). Vendor ID: 090807 Vendor number: 5678. Supplier name: Example Top Supplier. The item description is: Controller1234e. Type of vendor is unknown.

*Please note that this item has been discarded.*"

### Visualization
Follow visualization workflow from the beggining of this prompt.

## Response Guidelines

- Cite specific values from query results
- Focus on procurement insights (cost savings, vendor performance, spending patterns)
- Be concise and professional
"""

# Define the buyer agent with remote agent tools
root_agent = Agent(
    name="buyer_agent",
    model="gemini-2.5-flash",
    description="Agent specialized in procurement and purchasing queries using BigQuery tools for buyer data analysis.",
    instruction=instruction,
    tools=remote_agent_tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        http_options=types.HttpOptions(
            headers={
                "X-Vertex-AI-LLM-Request-Type": "shared",
                "X-Vertex-AI-LLM-Shared-Request-Type": "priority",
            }
        ),
    ),
)
print("bu=====Buyer agent defined")

# Wrap the agent with AdkApp for Agent Engine deployment
adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
)
print("bu=====Buyer Agent initialization complete")

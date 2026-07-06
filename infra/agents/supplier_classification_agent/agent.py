from __future__ import annotations
print("sc======== SUPPLIER CLASSIFICATION AGENT ===")
import vertexai
from vertexai.agent_engines import AdkApp
import os
import json
import requests
import time
import traceback
import google.auth
from google.adk.agents import Agent
from google.auth.transport.requests import Request as AuthRequest
from google.api_core import exceptions as gapi_exceptions
from google.cloud import bigquery
from google.genai import types

# OpenTelemetry for distributed tracing across agents
from opentelemetry import trace
from opentelemetry.propagate import inject as otel_inject

tracer = trace.get_tracer('supplier_classification_agent', '1.0.0')

# Initialize Vertex AI (required for both modes)
# Use REST transport to avoid local gRPC connection issues (fixes "socket is null" errors)
vertexai.init(
    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    api_transport="rest",
)
print(f"sc=====Vertex AI initialized with project: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
print(f"sc=====Vertex AI initialized with location: {os.environ.get('GOOGLE_CLOUD_LOCATION')}")

# Initialize BigQuery client for taxonomy lookup
bq_client = bigquery.Client(
    project=os.environ.get("SCO_KB_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
)
print("sc=====BigQuery client initialized for taxonomy lookup")

# Cache for taxonomy data to avoid repeated BigQuery queries
# Key: "all_taxonomy", Value: (timestamp, formatted_output)
_taxonomy_cache: dict[str, tuple[float, str]] = {}
_TAXONOMY_CACHE_TTL_SECONDS = 3600  # 1 hour

def get_taxonomy_categories() -> str:
    """Get the high-level taxonomy categories (L1/L2 groupings) with item counts.
    
    Returns a compact list of L1 and L2 category groupings from SPEND_TAXONOMY,
    showing how many PRISM Commodity Names exist under each L2 category.
    Use this FIRST to identify which L2 categories are relevant to the user's query,
    then call get_taxonomy_items with specific L2 category names.
    
    Results are cached for 1 hour.
    
    Returns:
        Formatted list of L1/L2 categories with item counts.
    """
    cache_key = "taxonomy_categories"
    if cache_key in _taxonomy_cache:
        cached_time, cached_output = _taxonomy_cache[cache_key]
        age_seconds = time.time() - cached_time
        if age_seconds < _TAXONOMY_CACHE_TTL_SECONDS:
            print(f"sc=====Returning cached taxonomy categories (age: {age_seconds:.1f}s)")
            return cached_output
        else:
            print(f"sc=====Cache expired (age: {age_seconds:.1f}s), refreshing taxonomy categories")
    
    try:
        query = f"""
        SELECT
            `PRISM Commodity Level 1` AS l1,
            `PRISM Commodity Level 2` AS l2,
            COUNT(DISTINCT `PRISM Commodity Name`) AS item_count
        FROM `sco_supplier_classification.SPEND_TAXONOMY`
        WHERE `PRISM Commodity Name` IS NOT NULL
        GROUP BY l1, l2
        ORDER BY l1, l2
        """
        
        print(f"sc=====Querying SPEND_TAXONOMY for L1/L2 category groupings")
        query_job = bq_client.query(query)
        results = query_job.result()
        
        output = "## Spend Taxonomy Categories\n\n"
        output += "Select one or more L2 categories below, then call `get_taxonomy_items` with the exact L2 name to retrieve all PRISM Commodity Names within it.\n\n"
        
        current_l1 = None
        for row in results:
            if row["l1"] != current_l1:
                current_l1 = row["l1"]
                output += f"\n### {current_l1}\n"
            output += f"- **{row['l2']}** ({row['item_count']} items)\n"
        
        print(f"sc=====Retrieved taxonomy category groupings")
        
        _taxonomy_cache[cache_key] = (time.time(), output)
        print(f"sc=====Cached taxonomy categories")
        
        return output
        
    except Exception as e:
        error_msg = f"Error querying SPEND_TAXONOMY categories: {str(e)}"
        print(f"sc====={error_msg}")
        return error_msg


def get_taxonomy_items(l2_category: str) -> str:
    """Get all PRISM Commodity Names under a specific L2 category.
    
    Call get_taxonomy_categories first to see available L2 categories, then call
    this tool with the exact L2 category name to retrieve all PRISM Commodity Names
    within it. These names can be used directly in line_item.category filters.
    
    Args:
        l2_category: The exact L2 category name (e.g., "Dialysis Equipment", 
                     "Dialysis Equipment Repair & Maintenance"). Must match exactly.
    
    Results are cached for 1 hour per L2 category.
    
    Returns:
        List of PRISM Commodity Names under the specified L2 category.
    """
    cache_key = f"taxonomy_items_{l2_category}"
    if cache_key in _taxonomy_cache:
        cached_time, cached_output = _taxonomy_cache[cache_key]
        age_seconds = time.time() - cached_time
        if age_seconds < _TAXONOMY_CACHE_TTL_SECONDS:
            print(f"sc=====Returning cached taxonomy items for '{l2_category}' (age: {age_seconds:.1f}s)")
            return cached_output
        else:
            print(f"sc=====Cache expired (age: {age_seconds:.1f}s), refreshing taxonomy items for '{l2_category}'")
    
    try:
        query = f"""
        SELECT DISTINCT
            `PRISM Commodity Name`,
            `PRISM Commodity Level 3`
        FROM `sco_supplier_classification.SPEND_TAXONOMY`
        WHERE `PRISM Commodity Name` IS NOT NULL
          AND `PRISM Commodity Level 2` = @l2_category
        ORDER BY `PRISM Commodity Level 3`, `PRISM Commodity Name`
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("l2_category", "STRING", l2_category),
            ]
        )
        
        print(f"sc=====Querying SPEND_TAXONOMY items for L2='{l2_category}'")
        query_job = bq_client.query(query, job_config=job_config)
        results = query_job.result()
        
        # Format results - keep original case from PRISM Commodity Name
        items = []
        for row in results:
            name = row["PRISM Commodity Name"]
            if name:
                items.append(name)
        
        if not items:
            return f"No PRISM Commodity Names found under L2 category '{l2_category}'. Check the exact name using get_taxonomy_categories."
        
        # Simple output: just the list and SQL IN clause
        output = f"**{l2_category}** ({len(items)} items):\n"
        output += ", ".join(f"'{item}'" for item in items)
        
        print(f"sc=====Retrieved {len(items)} taxonomy items for L2='{l2_category}'")
        
        _taxonomy_cache[cache_key] = (time.time(), output)
        print(f"sc=====Cached taxonomy items for '{l2_category}'")
        
        return output
        
    except Exception as e:
        error_msg = f"Error querying SPEND_TAXONOMY items for '{l2_category}': {str(e)}"
        print(f"sc====={error_msg}")
        return error_msg

###########################################
######### SUB-AGENTS VIA REASONING ENGINE ##
###########################################
# Sub-agents are deployed independently on Agent Engine
# Reference them via ReasoningEngine using their resource names
print("sc=====Setting up remote sub-agents via ReasoningEngine.")

# Get sub-agent resource names from environment variables
SQL_GENERATION_AGENT_RESOURCE = os.environ.get("SQL_GENERATION_AGENT_RESOURCE", "")
VALIDATION_AGENT_RESOURCE = os.environ.get("VALIDATION_AGENT_RESOURCE", "")
SQL_EXECUTION_AGENT_RESOURCE = os.environ.get("SQL_EXECUTION_AGENT_RESOURCE", "")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
print(f"sc=====SQL_GENERATION_AGENT_RESOURCE: {SQL_GENERATION_AGENT_RESOURCE}")
print(f"sc=====VALIDATION_AGENT_RESOURCE: {VALIDATION_AGENT_RESOURCE}")
print(f"sc=====SQL_EXECUTION_AGENT_RESOURCE: {SQL_EXECUTION_AGENT_RESOURCE}")
print(f"sc=====GOOGLE_CLOUD_PROJECT: {GOOGLE_CLOUD_PROJECT}")

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
            print(f"sc=====Resource name: {resource_name}")
            print(f"sc=====Query len: {len(query) if query is not None else 'None'}")
            try:
                print(f"sc=====Query preview (first 500): {query[:500]}")
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
                    "user_id": "supplier_classification",
                },
                "class_method": "stream_query",
            }
            print(f"sc=====POST {api_endpoint} [trace={trace_id}]")
            print(f"sc=====Payload user_id: 'supplier_classification'")

            resp = requests.post(api_endpoint, json=payload, headers=headers, stream=True)
            print(f"sc=====HTTP status: {resp.status_code}")
            if resp.status_code != 200:
                error_text = resp.text[:1000]
                print(f"sc=====HTTP error body: {error_text}")
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
                print(f"sc=====Line (first 300): {decoded_line[:300]}")
                try:
                    data = json.loads(decoded_line)
                except json.JSONDecodeError:
                    print(f"sc=====Skipping non-JSON line")
                    continue

                print(f"sc=====Parsed keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")

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
                                    print(f"sc=====Part text (first 200): {part['text'][:200]}")

            result = "\n".join(responses) if responses else "No response from agent"
            span.set_attribute("agent.http_status", 200)
            span.set_attribute("agent.response_length", len(result))
            return result
        except (gapi_exceptions.InternalServerError, gapi_exceptions.ServiceUnavailable) as e:
            last_exc = e
            span.set_attribute("agent.error", str(e))
            span.record_exception(e)
            print(
                "sc=====Transient error calling remote agent "
                f"(attempt {attempt}/{max_attempts}): {type(e).__name__}: {e}"
            )
            print("sc=====Traceback:\n" + traceback.format_exc())
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
                "sc=====Non-retryable error calling remote agent "
                f"(attempt {attempt}/{max_attempts}): {type(e).__name__}: {e}"
            )
            print("sc=====Traceback:\n" + traceback.format_exc())
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


# Collect available remote agent tools
agent_tools = [get_taxonomy_categories, get_taxonomy_items]
if SQL_GENERATION_AGENT_RESOURCE:
    agent_tools.append(sql_generation_agent)
    print("sc=====SQL Generation agent tool configured")
if VALIDATION_AGENT_RESOURCE:
    agent_tools.append(validation_agent)
    print("sc=====Validation agent tool configured")
if SQL_EXECUTION_AGENT_RESOURCE:
    agent_tools.append(sql_execution_agent)
    print("sc=====SQL Execution agent tool configured")
print(f"sc=====Total remote agent tools configured: {len(agent_tools)}")

instruction = """
You are a Supplier Classification Agent that analyzes spend data using a four-level product taxonomy (L1–L4). You orchestrate data queries via specialized sub-agents and provide spend analysis insights.

## Dataset Priority
**For Taxonomy Operations**: Always use `sco_supplier_classification` dataset for SPEND_TAXONOMY, INVOICE_ID_TO_FILE_NAME, IPRO_CATALOG_CATEGORIZATION, and COUPA_CATALOG_CATEGORIZATION tables.

**For Transaction Data**: Use `ai_financial_dlp` dataset for ERP tables (XXC_GL_SUMMARY, XXC_GL_DIV_REG_FAC, AP_INVOICES_ALL, AP_SUPPLIERS, etc.).

**For Invoice Extracts**: Use `sco_rage_invoice_extract_ds` dataset for invoice_extracts_prepared table.

## Data Quality Rules

**XXC_GL_SUMMARY Ledger Filter (MANDATORY)**: The XXC_GL_SUMMARY table contains duplicate rows for each transaction across multiple ledger IDs (primary, budget, forecast). Every query against XXC_GL_SUMMARY MUST include `AND TRIM(ledger_id) = '1'` in the WHERE clause to filter to the primary ledger only. Omitting this filter causes duplicate transaction counts and incorrect totals. The sql_generation_agent enforces this rule automatically, so if a query is rejected for "missing ledger_id filter," this is why.

## Tools

1. **get_taxonomy_categories** — Returns L1/L2 category groupings with item counts from `sco_supplier_classification.SPEND_TAXONOMY`. Call FIRST to identify relevant L2 categories.
2. **get_taxonomy_items(l2_category)** — Returns all PRISM Commodity Names under a specific L2 from `sco_supplier_classification.SPEND_TAXONOMY`, with a copy-paste ready SQL IN clause. Call once per relevant L2.
3. **sql_generation_agent** — Generates SQL from natural language. Provide exact category names for L4 queries and specify correct datasets.
4. **validation_agent** — Validates generated SQL before execution.
5. **sql_execution_agent** — Executes validated SQL against BigQuery. You CANNOT execute SQL directly.

## Terminology

- **"Cluster transactions"** → Aggregate/group by specified dimension
- **"Top suppliers" / "Preferred suppliers"** → Top 3 by total spend (unless specified otherwise)
- **"Palmer" / "Palmer VP"** → group_vp_desc in XXC_GL_DIV_REG_FAC
- **"Spend" / "Spending" / "Purchases"** → In XXC_GL_SUMMARY, "spend" refers ONLY to actual purchase and payment transactions, filtered by `journal_category IN ('Purchase Invoices', 'Payments')`. This excludes budget entries, accruals, reversals, and other non-spend journal entries. The sql_generation_agent applies this filter automatically for all spend-related queries. If user explicitly asks for ALL journal entries or non-spend data, this filter is omitted.

## Category Level Routing

- **L1/L2** (e.g., "Pharma", "Advertising"): Query `sco_supplier_classification.SPEND_TAXONOMY` joined to `ai_financial_dlp.XXC_GL_SUMMARY` via `Account`.
- **L3** (e.g., "R&M Dialysis Machine"): Use `ACCOUNT` in `ai_financial_dlp.XXC_GL_SUMMARY`.
- **L4** (default if unspecified): Use the **Taxonomy Matching Workflow** below with `sco_rage_invoice_extract_ds.invoice_extracts_prepared`.

## Standard Workflow

For all data questions: `sql_generation_agent` → `validation_agent` (re-generate on failure) → `sql_execution_agent` → analyze and respond with specific data points.

## Taxonomy Matching Workflow

For L4 / PRISM Commodity Name queries. Category values in `invoice_extracts_prepared.line_items.category` must match `PRISM Commodity Name` from `SPEND_TAXONOMY` exactly.

1. Call `get_taxonomy_categories` to browse L1/L2 groupings
2. Identify ALL relevant L2 categories for the user's query
   - Example: "dialysis chair and chair spare parts" → select both "Dialysis Equipment" and "Dialysis Equipment Repair & Maintenance"
3. Call get_taxonomy_items for each relevant L2 to retrieve all associated PRISM Commodity Names (L4s).
4. **Filter the retrieved L4 categories using context-aware semantic matching:**
   - **Parse user query structure**:
     - **Domain/context keywords**: Qualifiers that scope the search (e.g., "dialysis", "IT", "medical")
     - **Item keywords**: The actual product/service requested (e.g., "chairs", "cameras", "supplies")
     - **Modifier keywords**: Additional constraints (e.g., "spare parts", "maintenance", "accessories")

   - **Apply multi-keyword AND logic**:
     - **Primary rule**: L4 category must match BOTH domain context AND item keywords when user provides both
       - User: "dialysis chairs" → Must contain ("dialysis" OR be in dialysis-related L2) AND "chair"
       - ✅ "Dialysis Chairs" (dialysis ✓, chair ✓)
       - ✅ "Chair - Dialysis" (dialysis ✓, chair ✓)
       - ❌ "Maintenance Chairs" (dialysis ✗, chair ✓) - wrong domain
       - ❌ "Dialysis Machines" (dialysis ✓, chair ✗) - wrong item
     - **L2 category provides implicit domain context**: If you selected L2 "Dialysis Equipment", items within that L2 already have implicit "dialysis" context. Use this to:
       - Include items like "Chair Covers" from dialysis L2 (implicit dialysis context + partial chair match)
       - Exclude "Chair Covers" from non-dialysis L2s (wrong domain context)

   - **Matching strategies** (apply after context validation):
     - **Exact match**: Category contains the exact item keyword (e.g., "chair" → "Dialysis Chairs")
     - **Partial match**: Category contains root/variant of item keyword (e.g., "chair" → "Chair Covers", "Chair Accessories")
     - **Synonym match**: Category uses equivalent terms (e.g., "webcam" → "Web Cameras", "Video Cameras")
     - **Modifier expansion**: Include items with user's modifiers (e.g., "spare parts" → "Chair Spare Parts", "Replacement Parts")

   - **Bias toward inclusion within validated context**: When uncertain if an L4 category is relevant BUT it's within the correct domain context (L2), INCLUDE it. Better to overcount slightly within the right domain than miss spend.

   - **Cross-domain exclusion**: EXCLUDE items that match item keywords but are from wrong domain, even if the keyword matches:
     - User asks "dialysis chairs" from L2 "Dialysis Equipment" (50 items)
     - Don't include "Maintenance Chairs" from L2 "Facility Equipment" even though it has "chair"

   - **Minimum threshold**: If filtering would reduce to fewer than 3 L4 categories from a single L2, reconsider - you may be filtering too aggressively OR the user's query is very specific (both are valid).

   - **Document your reasoning**: Note which keywords drove the filter decisions and how domain context was applied.

   - **Example filtering**:
     - **User asks**: "dialysis chairs and spare parts"
     - **Parsed query**: domain="dialysis", items=["chairs", "spare parts"]
     - **L2 selected**: "Dialysis Equipment" (50 items), "Dialysis Equipment Repair & Maintenance" (23 items)
     - **From L2 "Dialysis Equipment"**:
       - ✅ "Dialysis Chairs" (domain: implicit from L2 ✓, item: "chair" ✓)
       - ✅ "Chair Covers" (domain: implicit from L2 ✓, item: "chair" partial ✓)
       - ✅ "Chair Accessories" (domain: implicit from L2 ✓, item: "chair" partial ✓)
       - ❌ "Dialysis Machines" (domain: ✓, item: "chair" ✗, "spare parts" ✗)
       - ❌ "Tubing" (domain: ✓, item: ✗)
     - **From L2 "Dialysis Equipment Repair & Maintenance"**:
       - ✅ "Chair Spare Parts" (domain: implicit from L2 ✓, item: "chair" + "spare parts" ✓)
       - ✅ "Chair Maintenance Kits" (domain: implicit from L2 ✓, item: "chair" partial ✓)
       - ❌ "Machine Repair Parts" (domain: ✓, item: ✗)
     - **Result**: 5 categories selected from 73 total
     - **Reasoning**: Domain scoped by L2 selection + keyword matching on "chair"/"spare parts"
5. Pass these filtered L4 categories (as a copy-paste ready IN clause) to sql_generation_agent. Ensure only L4 categories are used for supplier mapping.
6. Validate → execute → analyze results, noting which L2 categories and item count were included.

## Organizational Variance Analysis

When user asks to compare org unit spend against top/preferred suppliers:

1. Use Taxonomy Matching Workflow to identify category names
2. **Query 1 — Top Suppliers:** Identify top 3 suppliers by total spend. Validate → execute.
3. **Query 2 — Palmer Variance:** CTE query joining spend with org hierarchy (INVOICE_ID_TO_FILE_NAME → AP_INVOICES_ALL → XXC_GL_SUMMARY → XXC_GL_DIV_REG_FAC) to calculate percent spend outside preferred suppliers by org unit. Validate → execute.
4. Present combined results: top suppliers with totals, then org units ranked by non-preferred spend %.

Two queries are acceptable — results are combined in the final response.

## Tail Supplier Consolidation Workflow

When user asks to consolidate tail supplier items under top/preferred suppliers and identify savings:

1. **Taxonomy Matching:** Use get_taxonomy_categories → get_taxonomy_items to resolve L4 PRISM Commodity Names
   - Example: "dialysis chair and chair spare parts" → "Dialysis Equipment" + "Dialysis Equipment Repair & Maintenance" L2s
   - Apply intelligent filtering as defined in Taxonomy Matching Workflow

2. **Single Consolidated Query:** Ask sql_generation_agent to generate ONLY the main consolidation query using the Tail Supplier Consolidation Pattern:
   - CTE 1: Top 3 suppliers by spend
   - CTE 2: Tail supplier items (non-top-3) with pricing
   - CTE 3: IPRO catalog alternatives (uses catalog list price)
   - CTE 4: COUPA price proxy (avg unit_price from COUPA_INVOICES per supplier+commodity)
   - CTE 5: COUPA catalog alternatives (joined to price proxy)
   - CTE 6: Combined catalog alternatives from both sources
   - Final SELECT: JOIN on prism_category, calculate savings
   - **IMPORTANT:** Do NOT ask for separate summary statistics or unmatched items queries. You will compute those from the main query results.

3. **Validate & Execute:** Standard validation → execution flow

4. **Present Results:**
   - **Top Suppliers:** Name + total spend for each of top 3
   - **Matched Items Table:** Tail supplier item → catalog alternative → price delta → total savings → price_source
   - **Summary Stats:**
     - Total savings opportunity (sum of all matched items)
     - Number of items matched
     - Average price delta
     - Match confidence distribution (% high/medium/low confidence)
     - Price source breakdown (ipro_catalog vs coupa_invoice_proxy)
   - **Price Source Note:** Flag COUPA-sourced savings as approximate (derived from avg invoice prices, not catalog list prices). Include price_sample_count for transparency.
   - **Unmatched Items:** Tail supplier items with no catalog alternative (prism_category not in catalog or confidence < 0.7)

**Important:** All item matching is done via SQL JOIN on prism_commodity_name_predicted (lowercased). 
Catalog items are pre-categorized in separate tables (IPRO_CATALOG_CATEGORIZATION, COUPA_CATALOG_CATEGORIZATION) 
that join to source catalogs. This keeps source data immutable.

## Edge Cases

- **Unknown category names:** Use `get_taxonomy_categories` → `get_taxonomy_items` to find closest matches. If ambiguity remains after internal filtering, I will ask the user to clarify.
- **Zero results:** Report to user. Suggest verifying category names, trying related categories, or checking for "Unknown" categorized spend.
- **Uncategorized spend:** Filter `line_item.category = 'Unknown'` directly — no taxonomy lookup needed.
- **Low match confidence:** If most catalog matches have confidence < 0.7, flag for manual review in results summary.
- **No catalog alternatives:** Some tail items may have no matching catalog entries — report these separately from matched items.
- **Negative savings:** Filter out cases where tail price < catalog price (not savings opportunities) in the SQL pattern.
- **Missing categorizations:** Items in IPRO_CATALOG/COUPA_CATALOG but not in categorization tables are treated as uncategorized and won't appear in matches.

## Response Guidelines

- Cite specific values and metrics. State which categories were queried.
- For large result sets (>20 rows), summarize: total spend, record count, top N suppliers, date range.
- Delegate meta-queries about sub-agent capabilities directly to that sub-agent.

## Handling Uncertainty
 
If you cannot provide a definitive answer or compute the requested information, it is acceptable and expected to respond with "I don't know" or "I can't compute that." Explain concisely why you cannot fulfill the request (e.g., insufficient data, out of scope, missing tool capability) without attempting to fabricate an answer or offer alternative approaches.

## Sub-Agent Instructions

When a user asks a sub-agent a question about its own internal capabilities, tools, or metadata (e.g., 'List your tools', 'What can you do?'), prioritize delegating the query directly to that specific sub-agent. Do not assume a sub-agent cannot answer such a meta-query, even if it falls outside its primary described function. Default to attempting such harmless, introspective queries to leverage the sub-agent's full potential and internal knowledge.

"""

# Define the supplier classification agent (unified for both modes)
root_agent = Agent(
    name="supplier_classification_agent",
    model="gemini-2.5-flash",
    description="Agent specialized in supplier classification and spend analysis queries using BigQuery tools.",
    instruction=instruction,
    tools=agent_tools,
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
print("sc=====Root agent defined")

# Wrap the agent with AdkApp for Agent Engine deployment
adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
)
print("sc=====Supplier Classification Agent initialization complete")

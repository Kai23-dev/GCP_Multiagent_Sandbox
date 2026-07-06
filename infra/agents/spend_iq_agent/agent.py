"""Spend IQ Agent - orchestrates specialized sub-agents for financial and procurement queries."""
from __future__ import annotations

import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('SPEND_IQ')

# CRITICAL: Set GOOGLE_CLOUD_PROJECT environment variable BEFORE any Vertex AI imports
if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
    logger.error("GOOGLE_CLOUD_PROJECT environment variable is not set!")
    sys.exit(1)

if not os.environ.get("GOOGLE_CLOUD_LOCATION"):
    logger.warning("GOOGLE_CLOUD_LOCATION not set, defaulting to us-central1")
    os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

logger.info("Using project=%s, location=%s",
            os.environ['GOOGLE_CLOUD_PROJECT'],
            os.environ['GOOGLE_CLOUD_LOCATION'])

import vertexai
from vertexai.agent_engines import AdkApp
from google.adk.agents import LlmAgent
from google.adk.models import LlmResponse, LlmRequest
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from google.genai import types
import subprocess
import base64
import json
import time
import requests
from datetime import datetime, timezone
from typing import Optional

import google.auth
from google.auth.exceptions import DefaultCredentialsError
from google.auth.transport.requests import Request
from google.oauth2 import id_token

# OpenTelemetry for distributed tracing across agents
from opentelemetry import trace, context
from opentelemetry.propagate import inject as otel_inject

tracer = trace.get_tracer('spend_iq_agent', '1.0.0')


def get_id_token(audience: str) -> str:
    """Get Google Cloud ID token for authenticating to Cloud Run services."""
    try:
        request = Request()
        fetched_token = id_token.fetch_id_token(request, audience)

        # Check if token is expiring soon and re-mint if needed
        try:
            parts = fetched_token.split(".")
            if len(parts) == 3:
                payload_b64 = parts[1] + ("=" * (-len(parts[1]) % 4))
                payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
                exp = int(payload.get("exp", 0))
                now = int(time.time())
                if exp and exp - now <= 300:
                    logger.debug("Token expiring soon, re-minting via metadata service")
                    metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
                    params = {"audience": audience}
                    headers = {"Metadata-Flavor": "Google"}
                    response = requests.get(metadata_url, params=params, headers=headers)
                    fetched_token = response.text
        except Exception as exc:
            logger.debug("Token expiry re-mint check skipped: %s", exc)

        return fetched_token
    except DefaultCredentialsError:
        logger.debug("No default credentials, using gcloud CLI")
        if sys.platform == "win32":
            result = subprocess.run('gcloud auth print-identity-token', capture_output=True, text=True, check=False, shell=True)
        else:
            result = subprocess.run(["gcloud", "auth", "print-identity-token"], capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception as e:
        logger.warning("Failed to fetch ID token: %s", e)
        return ""


# Initialize Vertex AI
vertexai.init(
    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
)
logger.info("Vertex AI initialized")

# Sub-agent resource configuration
AUDITOR_AGENT_RESOURCE = os.environ.get("AUDITOR_AGENT_RESOURCE", "")
BUYER_AGENT_RESOURCE = os.environ.get("BUYER_AGENT_RESOURCE", "")
TREND_AGENT_RESOURCE = os.environ.get("TREND_AGENT_RESOURCE", "")
SUPPLIER_CLASSIFICATION_AGENT_RESOURCE = os.environ.get("SUPPLIER_CLASSIFICATION_AGENT_RESOURCE", "")
CONTRACT_INTELLIGENCE_AGENT_RESOURCE = os.environ.get("CONTRACT_INTELLIGENCE_AGENT_RESOURCE", "")
FINANCIAL_LEAKAGE_AGENT_RESOURCE = os.environ.get("FINANCIAL_LEAKAGE_AGENT_RESOURCE", "")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

logger.info("Sub-agents configured: auditor=%s, buyer=%s, trend=%s, supplier=%s, contract=%s, leakage=%s",
            bool(AUDITOR_AGENT_RESOURCE), bool(BUYER_AGENT_RESOURCE), bool(TREND_AGENT_RESOURCE),
            bool(SUPPLIER_CLASSIFICATION_AGENT_RESOURCE), bool(CONTRACT_INTELLIGENCE_AGENT_RESOURCE),
            bool(FINANCIAL_LEAKAGE_AGENT_RESOURCE))


def _get_auth_headers() -> dict:
    """Get authorization headers using Application Default Credentials."""
    creds, _ = google.auth.default()
    creds.refresh(Request())
    return {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }


def _create_remote_session(resource_name: str, user_id: str) -> str:
    """Create a new session on a remote agent and return its session ID."""
    api_endpoint = f"https://{GOOGLE_CLOUD_LOCATION}-aiplatform.googleapis.com/v1beta1/{resource_name}:query"
    payload = {
        "input": {"user_id": user_id},
        "class_method": "create_session",
    }
    resp = requests.post(api_endpoint, json=payload, headers=_get_auth_headers(), timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to create remote session: HTTP {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    session_id = data.get("output", {}).get("id", "")
    if not session_id:
        raise RuntimeError(f"Remote session creation returned no ID: {resp.text[:500]}")
    logger.info("Created remote session %s on %s", session_id, resource_name.split("/")[-1])
    return session_id


def _call_remote_agent(resource_name: str, query: str, session_id: str = "", user_id: str = "spend_iq") -> str:
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
                "agent.user_id": user_id,
            },
        ) as span:
          try:
            api_endpoint = f"https://{GOOGLE_CLOUD_LOCATION}-aiplatform.googleapis.com/v1beta1/{resource_name}:streamQuery"
            input_data = {"message": query, "user_id": user_id}
            if session_id:
                input_data["session_id"] = session_id

            # Inject W3C trace context so child agent joins the same trace
            trace_ctx = trace.get_current_span().get_span_context()
            trace_id = format(trace_ctx.trace_id, '032x') if trace_ctx.trace_id else ''
            payload = {
                "input": input_data,
                "class_method": "stream_query",
            }

            # Build headers with auth + OTel trace propagation
            headers = _get_auth_headers()
            otel_inject(headers)  # adds traceparent, tracestate

            logger.info("Calling remote agent (attempt %d/%d): %s [trace=%s]", attempt, max_attempts, agent_name, trace_id)
            resp = requests.post(api_endpoint, json=payload, headers=headers, timeout=300)

            if resp.status_code != 200:
                error_text = resp.text[:500]
                logger.error("HTTP error %d: %s", resp.status_code, error_text)
                span.set_attribute("agent.http_status", resp.status_code)
                span.set_attribute("agent.error", error_text)
                if resp.status_code in (500, 503):
                    from google.api_core import exceptions as gapi_exceptions
                    raise gapi_exceptions.InternalServerError(f"HTTP {resp.status_code}: {error_text}")
                raise RuntimeError(f"HTTP {resp.status_code}: {error_text}")

            # Parse JSON response lines (NDJSON format)
            responses = []
            for raw_line in resp.text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if isinstance(data, dict):
                    output = data.get("output", data)
                    if isinstance(output, dict):
                        content = output.get("content", {})
                        if isinstance(content, dict):
                            parts = content.get("parts", [])
                            for part in parts:
                                if isinstance(part, dict) and "text" in part:
                                    responses.append(part["text"])

            result = "\n".join(responses) if responses else "No response from agent"
            span.set_attribute("agent.http_status", 200)
            span.set_attribute("agent.response_length", len(result))
            logger.info("Response received from %s: %d chars [trace=%s]", agent_name, len(result), trace_id)
            return result
          except Exception as e:
            last_exc = e
            span.set_attribute("agent.error", str(e))
            span.record_exception(e)
            logger.warning("Error calling %s (attempt %d/%d): %s", agent_name, attempt, max_attempts, e)
            if attempt < max_attempts:
                sleep_s = base_sleep_s * (2 ** (attempt - 1))
                time.sleep(sleep_s)
                continue
            break

    return f"Error calling remote agent: {type(last_exc).__name__}: {last_exc}"


def _get_or_create_remote_session(resource_name: str, agent_key: str, tool_context: ToolContext) -> str:
    """Get an existing remote session ID from state, or create a new one."""
    state_key = f"remote_session_{agent_key}"
    session_id = tool_context.state.get(state_key, "")
    if not session_id:
        session_id = _create_remote_session(resource_name, tool_context.user_id)
        tool_context.state[state_key] = session_id
    return session_id


def query_auditor_agent(query: str, tool_context: ToolContext) -> str:
    """Query the Auditor agent for audit and compliance related queries."""
    if not AUDITOR_AGENT_RESOURCE:
        return "Auditor agent is not configured"
    logger.info("Delegating to auditor_agent")
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{AUDITOR_AGENT_RESOURCE}"
    session_id = _get_or_create_remote_session(resource, "auditor", tool_context)
    return _call_remote_agent(resource, query, session_id=session_id, user_id=tool_context.user_id)


def query_buyer_agent(query: str, tool_context: ToolContext) -> str:
    """Query the Buyer agent for procurement and purchasing related queries."""
    if not BUYER_AGENT_RESOURCE:
        return "Buyer agent is not configured"
    logger.info("Delegating to buyer_agent")
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{BUYER_AGENT_RESOURCE}"
    session_id = _get_or_create_remote_session(resource, "buyer", tool_context)
    return _call_remote_agent(resource, query, session_id=session_id, user_id=tool_context.user_id)


def query_trend_agent(query: str, tool_context: ToolContext) -> str:
    """Query the Trend agent for trend analysis related queries."""
    if not TREND_AGENT_RESOURCE:
        return "Trend agent is not configured"
    logger.info("Delegating to trend_agent")
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{TREND_AGENT_RESOURCE}"
    session_id = _get_or_create_remote_session(resource, "trend", tool_context)
    return _call_remote_agent(resource, query, session_id=session_id, user_id=tool_context.user_id)


def query_supplier_classification_agent(query: str, tool_context: ToolContext) -> str:
    """Query the Supplier Classification agent for supplier categorization and classification related queries."""
    if not SUPPLIER_CLASSIFICATION_AGENT_RESOURCE:
        return "Supplier Classification agent is not configured"
    logger.info("Delegating to supplier_classification_agent")
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{SUPPLIER_CLASSIFICATION_AGENT_RESOURCE}"
    session_id = _get_or_create_remote_session(resource, "supplier_classification", tool_context)
    return _call_remote_agent(resource, query, session_id=session_id, user_id=tool_context.user_id)


def query_contract_intelligence_agent(query: str, tool_context: ToolContext) -> str:
    """Query the Contract Intelligence agent for contract-to-invoice comparison, price discrepancy detection, and savings analysis."""
    if not CONTRACT_INTELLIGENCE_AGENT_RESOURCE:
        return "Contract Intelligence agent is not configured"
    logger.info("Delegating to contract_intelligence_agent")
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{CONTRACT_INTELLIGENCE_AGENT_RESOURCE}"
    session_id = _get_or_create_remote_session(resource, "contract_intelligence", tool_context)
    return _call_remote_agent(resource, query, session_id=session_id, user_id=tool_context.user_id)


def query_financial_leakage_agent(query: str, tool_context: ToolContext) -> str:
    """Query the Financial Leakage agent for detecting inappropriate spend, personal purchases, unauthorized subscriptions, and maverick buying patterns."""
    if not FINANCIAL_LEAKAGE_AGENT_RESOURCE:
        return "Financial Leakage agent is not configured"
    logger.info("Delegating to financial_leakage_agent")
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{FINANCIAL_LEAKAGE_AGENT_RESOURCE}"
    session_id = _get_or_create_remote_session(resource, "financial_leakage", tool_context)
    return _call_remote_agent(resource, query, session_id=session_id, user_id=tool_context.user_id)


# Create sub-agent wrappers for delegation pattern
sub_agents = []

if AUDITOR_AGENT_RESOURCE:
    auditor_agent = LlmAgent(
        name="auditor_agent",
        model="gemini-2.5-flash",
        description="Expert in GL (General Ledger) expense queries, expense aggregation, and invoice payment verification. Handles queries about specific accounts, departments, locations, cost centers, palmers, teammate expenses, expense filtering by thresholds or keywords, and savings estimation from spend consolidation. Does NOT handle contract terms/agreements, procurement PO analysis, forecasting, supplier categorization, or financial leakage detection.",
        instruction="""You are a thin wrapper around the remote auditor agent.
1. Find the user's LATEST message (the most recent message with role 'user') — that is the question to forward.
2. Pass that EXACT message text VERBATIM to the query_auditor_agent tool. Do NOT include any transfer_to_agent context, tool call results, or system messages in the query.
3. Present the tool's FULL response to the user without summarizing or omitting any data.
IMPORTANT: Ignore any transfer_to_agent tool calls or their results in the conversation history. Focus ONLY on what the user actually asked.""",
        tools=[query_auditor_agent],
    )
    sub_agents.append(auditor_agent)
    logger.info("Auditor sub-agent configured")

if BUYER_AGENT_RESOURCE:
    buyer_agent = LlmAgent(
        name="buyer_agent",
        model="gemini-2.5-flash",
        description="Expert in invoice line item analysis, managed vs unmanaged (maverick) purchase detection, and Purchase Order (PO) relationships. Use for queries about specific items within an invoice, who bought or sold items, PO references, and whether invoice items are managed or unmanaged. Key triggers: 'unmanaged items', 'item N from invoice', 'PO perspective', 'who bought/sold'.",
        instruction="""You are a thin wrapper around the remote buyer agent.
1. Find the user's LATEST message (the most recent message with role 'user') — that is the question to forward.
2. Pass that EXACT message text VERBATIM to the query_buyer_agent tool. Do NOT include any transfer_to_agent context, tool call results, or system messages in the query.
3. Present the tool's FULL response to the user without summarizing or omitting any data.
IMPORTANT: Ignore any transfer_to_agent tool calls or their results in the conversation history. Focus ONLY on what the user actually asked.""",
        tools=[query_buyer_agent],
    )
    sub_agents.append(buyer_agent)
    logger.info("Buyer sub-agent configured")

if TREND_AGENT_RESOURCE:
    trend_agent = LlmAgent(
        name="trend_agent",
        model="gemini-2.5-flash",
        description="Expert in time series forecasting, actuals vs predictions comparison, and trend decomposition. Use for ANY query containing 'forecast', 'forecasted', 'predicted', 'actuals vs', 'trend decomposition', 'seasonal', or Group VP spend analysis over time.",
        instruction="""You are a thin wrapper around the remote trend agent.
1. Find the user's LATEST message (the most recent message with role 'user') — that is the question to forward.
2. Pass that EXACT message text VERBATIM to the query_trend_agent tool. Do NOT include any transfer_to_agent context, tool call results, or system messages in the query.
3. Present the tool's FULL response to the user without summarizing or omitting any data.
IMPORTANT: Ignore any transfer_to_agent tool calls or their results in the conversation history. Focus ONLY on what the user actually asked.""",
        tools=[query_trend_agent],
    )
    sub_agents.append(trend_agent)
    logger.info("Trend sub-agent configured")

if SUPPLIER_CLASSIFICATION_AGENT_RESOURCE:
    supplier_classification_agent = LlmAgent(
        name="supplier_classification_agent",
        model="gemini-2.5-flash",
        description="Expert in product category clustering, supplier consolidation, tail spend identification, and uncategorized spend detection. Use for queries about clustering transactions into categories, identifying spend for specific product types (e.g. dialysis chairs, spare parts), finding suppliers or spend that don't fit existing categories, and identifying preferred vs tail suppliers with consolidation savings.",
        instruction="""You are a thin wrapper around the remote supplier classification agent.
1. Find the user's LATEST message (the most recent message with role 'user') — that is the question to forward.
2. Pass that EXACT message text VERBATIM to the query_supplier_classification_agent tool. Do NOT include any transfer_to_agent context, tool call results, or system messages in the query.
3. Present the tool's FULL response to the user without summarizing or omitting any data.
IMPORTANT: Ignore any transfer_to_agent tool calls or their results in the conversation history. Focus ONLY on what the user actually asked.""",
        tools=[query_supplier_classification_agent],
    )
    sub_agents.append(supplier_classification_agent)
    logger.info("Supplier Classification sub-agent configured")

if CONTRACT_INTELLIGENCE_AGENT_RESOURCE:
    contract_intelligence_agent = LlmAgent(
        name="contract_intelligence_agent",
        model="gemini-2.5-flash",
        description="Expert in contract analysis: contract terms, commitments, penalties, rebate thresholds, pricing comparisons between suppliers, SOW clause analysis, contracted rate compliance, and cost-efficient alternatives within agreement constraints. Use for ANY query mentioning 'contract', 'agreement', 'SOW', 'commitments', 'penalties', 'rebates', 'contracted rate', 'clauses', or a supplier name when asking about their contract/agreement terms.",
        instruction="""You are a thin wrapper around the remote contract intelligence agent.
1. Find the user's LATEST message (the most recent message with role 'user') — that is the question to forward.
2. Pass that EXACT message text VERBATIM to the query_contract_intelligence_agent tool. Do NOT include any transfer_to_agent context, tool call results, or system messages in the query.
3. Present the tool's FULL response to the user without summarizing or omitting any data.
IMPORTANT: Ignore any transfer_to_agent tool calls or their results in the conversation history. Focus ONLY on what the user actually asked.""",
        tools=[query_contract_intelligence_agent],
    )
    sub_agents.append(contract_intelligence_agent)
    logger.info("Contract Intelligence sub-agent configured")

if FINANCIAL_LEAKAGE_AGENT_RESOURCE:
    financial_leakage_agent = LlmAgent(
        name="financial_leakage_agent",
        model="gemini-2.5-flash",
        description="Expert in detecting inappropriate and personal spend on company accounts. Use for queries about scanning GL line items for suspicious product keywords (e.g. Airpod, iPad, espresso, gift card), detecting personal purchases, unauthorized subscriptions, maverick buying patterns, and leakage risk scoring. Key trigger: questions asking whether GL line descriptions contain specific product words or brands that shouldn't be on company accounts.",
        instruction="""You are a thin wrapper around the remote financial leakage agent.
1. Find the user's LATEST message (the most recent message with role 'user') — that is the question to forward.
2. Pass that EXACT message text VERBATIM to the query_financial_leakage_agent tool. Do NOT include any transfer_to_agent context, tool call results, or system messages in the query.
3. Present the tool's FULL response to the user without summarizing or omitting any data.
IMPORTANT: Ignore any transfer_to_agent tool calls or their results in the conversation history. Focus ONLY on what the user actually asked.""",
        tools=[query_financial_leakage_agent],
    )
    sub_agents.append(financial_leakage_agent)
    logger.info("Financial Leakage sub-agent configured")

logger.info("Total sub-agents configured: %d", len(sub_agents))


# Guardrail callbacks
def guardrail_before_model(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """Input guardrails - check for prohibited patterns before LLM processing."""
    try:
        if llm_request.contents and len(llm_request.contents) > 0:
            last_content = llm_request.contents[-1]
            if hasattr(last_content, 'role') and last_content.role == 'user':
                if hasattr(last_content, 'parts') and len(last_content.parts) > 0:
                    user_message = last_content.parts[0].text if hasattr(last_content.parts[0], 'text') else ""

                    prohibited_patterns = [
                        "DROP TABLE", "DELETE FROM", "TRUNCATE", "ALTER TABLE",
                        "DROP DATABASE", "EXEC(", "EXECUTE(",
                    ]

                    user_message_upper = user_message.upper()
                    for pattern in prohibited_patterns:
                        if pattern in user_message_upper:
                            logger.warning("[Guardrail] Request blocked: contains prohibited pattern '%s'", pattern)
                            return LlmResponse(
                                content=types.Content(
                                    role="model",
                                    parts=[types.Part(text="This request was blocked by security guardrails. Destructive database operations are not allowed.")]
                                )
                            )
    except Exception as e:
        logger.error("[Guardrail] Error in before_model_callback: %s", e)

    return None


def guardrail_after_model(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Output guardrails - validate LLM responses."""
    try:
        if llm_response.content and hasattr(llm_response.content, 'parts'):
            if len(llm_response.content.parts) > 0 and hasattr(llm_response.content.parts[0], 'text'):
                response_text = llm_response.content.parts[0].text

                max_length = 50000
                if response_text and len(response_text) > max_length:
                    logger.warning("[Guardrail] Response truncated: exceeded %d characters", max_length)
                    return LlmResponse(
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text="The response was too long and has been blocked. Please refine your query to be more specific.")]
                        )
                    )
    except Exception as e:
        logger.error("[Guardrail] Error in after_model_callback: %s", e)

    return None


instruction = f"""
You are Spend IQ, an intelligent financial assistant designed to help teams analyze financial and procurement data, identify cost-saving opportunities, and streamline overall spend management. Created through a collaboration between the finance and procurement technology teams, you bring clarity to complex spending patterns. By quickly synthesizing large volumes of financial data, you empower business leaders to make informed, data-driven decisions that align with the company's budgetary goals.

You operate with a highly analytical, precise, and helpful personality. Your tone is consistently professional, clear, and encouraging — always aiming to make complex financial concepts accessible rather than overwhelming.

While highly capable of analyzing trends and generating actionable insights, you have limitations: rely on historical data, cannot execute actual purchases, and do not have the authority to approve budgets or finalize financial decisions. For any technical issues, system access requests, or advanced support, users should reach out to the Finance Tech Support team.

You can access specialized sub-agents for analytics and data queries.
Your primary role is to **delegate** user questions to the appropriate sub-agent based on the query domain.

## Delegation Pattern

When a user asks a question:
1. **Analyze the query** using the routing guidelines below
2. **Delegate to the appropriate sub-agent** by transferring control to them
3. **The sub-agent will continue the conversation** with the user until their questions are fully answered
4. **The sub-agent will escalate back to you** if the conversation shifts to a different domain

You act as a smart router that delegates conversations to domain experts, who then take over the interaction.

**Available Sub-Agents:**

• **auditor_agent**: GL (General Ledger) expense queries, expense aggregation, invoice payment verification, and savings estimation from spend consolidation. Handles specific accounts, departments, locations, cost centers, palmers, teammate expenses, and expense filtering by thresholds or keywords. Does NOT handle contracts, PO/procurement analysis, forecasting, supplier categorization, or leakage detection.

• **buyer_agent**: Invoice line item analysis, managed vs unmanaged (maverick) purchase detection, and Purchase Order (PO) relationships. Use when queries mention "unmanaged items", "item N from invoice", "PO perspective", "who bought/sold".

• **trend_agent**: Time series forecasting, actuals vs predictions comparison, and trend decomposition. Use for ANY query with "forecast", "forecasted", "predicted", "actuals vs", "trend decomposition", "seasonal", or Group VP spend over time.

• **supplier_classification_agent**: Product category clustering, supplier consolidation, tail spend identification, and uncategorized spend detection. Use for queries about clustering transactions, identifying spend for specific product types (dialysis chairs, spare parts), finding uncategorized spend, and preferred vs tail supplier analysis.

• **contract_intelligence_agent**: Contract analysis including terms, commitments, penalties, rebate thresholds, pricing comparisons between suppliers, SOW clause analysis, contracted rate compliance, and cost-efficient alternatives within agreement constraints. Use for ANY query mentioning "contract", "agreement", "SOW", "commitments", "penalties", "rebates", "contracted rate", "clauses", or a supplier name when asking about their contract/agreement terms.

• **financial_leakage_agent**: Detecting inappropriate and personal spend on company accounts. Use for queries about scanning GL line items for suspicious product keywords (Airpod, iPad, espresso, gift card), detecting personal purchases, unauthorized subscriptions, and leakage risk scoring. Key trigger: questions asking whether line descriptions contain specific product words or brands.

**Routing Guidelines:**

### 1. Auditor Agent (`auditor_agent`)
Delegate detailed GL queries, invoice lookups, financial calculations, and savings estimation here.

**When to use:**
- Invoice lookup and verification (find specific invoices, confirm payment status)
- GL searches with complex filters (palmer, department, location, account, teammate names, date ranges)
- Expense aggregation and tallying (sum/count expenses for specific criteria)
- Financial calculations and savings estimation (calculate potential savings from scenarios)
- Line item filtering (expenses above/below thresholds, text search in descriptions)
- Account-specific queries (Travel & Entertainment, Field Office Supplies, Other Controllable Expenses, etc.)
- Top-N analysis (top teammates by expense type, top expenses in category, etc.)
- Cost center, department, and location queries

**Example queries:**
- "Calculate savings if we consolidate vendor spend from multiple suppliers to a single preferred vendor with X% discount"
- "Find invoice details in our P&L including location, account, time period, and payment status"
- "Search GL for travel expenses by specific teammate name in a given palmer and year"
- "Identify top employees with highest reimbursements for a specific expense type"
- "List all charges above a threshold within a category for a specific division and month"
- "Find expenses in a category that contain specific keywords in the description"
- "Aggregate expenses below a threshold for a specific category and time period"
- "Show all expenses for a specific cost center"
- "Total expenses for a given department and location"

**Key characteristics:**
- Uses 3-step workflow: SQL Generation → Validation → Execution
- Performs detailed financial calculations and aggregations
- Has special date handling protocol for accurate date parsing
- Cannot execute SQL directly (delegates to sub-agents)

---

### 2. Buyer Agent (`buyer_agent`)
Delegate invoice line item analysis and managed vs unmanaged (maverick) detection here.

**When to use (PRIORITY for "item N from invoice" patterns):**
- **Invoice line item lookup** - Questions asking about "item 5 from invoice X", "what exactly is item N", "line item details"
- **Managed vs Unmanaged detection** - Identify if invoice/items have POs
- **Item detail extraction** - "who bought it", "who sold it", pricing, PO reference for specific items
- **Purchase Order relationship analysis** - Trace items back to POs
- **Buyer identification** - Who authorized/placed the order for specific items
- **Vendor/Seller identification** - For specific items within invoices

**Example queries:**
- "Does this invoice have any unmanaged items?"
- "What is item N from invoice XYZ, who bought it, for how much, and who sold it?"
- "Show me items in this invoice without a PO"
- "Who bought a specific item from an invoice?"
- "What's the price and vendor for a specific line item?"
- "List unmanaged items across invoices for a time period"

**Key characteristics:**
- Specializes in invoice line-level analysis
- Managed vs Unmanaged detection: `po_header_id IS NULL` = unmanaged (no Purchase Order)
- Extracts buyer, seller, price, and PO relationships for specific items
- Uses 3-step workflow with DETAILED requests to sql_generation_agent
- Focuses on item-level procurement data (not GL-level aggregations or trend analysis)

**Managed vs Unmanaged Logic:**
- Managed = AP_INVOICE_LINES_ALL.po_header_id has a valid value (follows procurement process)
- Unmanaged = AP_INVOICE_LINES_ALL.po_header_id IS NULL or = 'N/A' (no Purchase Order, also called "maverick")

---

### 3. Trend Agent (`trend_agent`)
Delegate time series analysis, forecasting, and actuals vs predictions comparison here.

**When to use (HIGH PRIORITY for forecast keywords):**
- **FORECASTING** - Any question with "forecast", "forecasted", "prediction", "predicted"
- **Forecast decomposition** - Questions about trend/seasonal/holiday/residual components
- Forecast vs Actual comparison (compare historical spend to forecasted values)
- Time series decomposition (trend component, seasonal patterns, holiday effects)
- Group VP level forecast analysis (BQML pre-computed predictions)
- Confidence interval analysis (prediction bounds, model reliability)
- Unified timeline visualization (show actuals and forecasts together)
- Month-over-Month (MoM), Year-over-Month (YoY), or seasonality analysis
- Vendor/category/palmer spending patterns over time
- Cross-system validation (Coupa vs iProcurement vs GL)

**Example queries:**
- "Compare actual historical spend to forecasted spend for a Group VP, showing timeline"
- "Show forecast decomposition components (trend, seasonal, holiday, residual) for a Group VP"
- "What's the month-over-month spending trend for recent months?"
- "Show year-over-year growth in a specific category"
- "Which vendors show increasing or decreasing spend trends?"
- "Compare spending across divisions over a time period"
- "What are forecast confidence intervals for spend projections?"
- "Show seasonality patterns for an account or category"

**Key characteristics:**
- **ALWAYS defaults to GL tables** (XXC_GL_SUMMARY) unless user explicitly requests other sources
- Has access to forecast tables: `GROUP_FORECAST_MODEL_GROUP_VP_FORECAST_RESULTS`, `GROUP_FORECAST_MODEL_GROUP_VP_FORECAST_DATA`, `GROUP_FORECAST_MODEL_GROUP_VP_DECOMPOSITION`
- Performs trend analysis directly: calculates MoM, YoY, percentages, identifies patterns
- Analyzes forecast quality: confidence intervals, seasonal/holiday component availability, residuals
- Has consistency defaults: "top" = top 5, "top vendors per Palmer" = top 3 per Palmer
- Follows MANDATORY 5-step workflow: Understand → Generate SQL → Validate → Execute → Analyze
- Focuses on 8 analysis areas: MoM, YoY, Seasonality, Category Trends, Vendor Performance, Division/Palmer, Cross-System Validation, **Forecasting**

**Data Source Rules:**
- DEFAULT to XXC_GL_SUMMARY for spend/vendor/category analysis
- Use forecast tables (in `forecasting_us` dataset) for forecast-related queries
- Use COUPA_INVOICES only if: user says "Coupa", GL lacks multi-month data, or cross-validation requested
- Use IPRO_ORDERS only if: user says "iProcurement"/"iPro", GL lacks multi-month data, or cross-validation requested
- Use XXC_GL_DIV_REG_FAC for Palmer/division/region breakdowns (join with GL)

---

### 4. Supplier Classification Agent (`supplier_classification_agent`)
Delegate category clustering, supplier consolidation analysis, and tail spend identification here.

**When to use (HIGH PRIORITY for product category spend):**
- **PRODUCT CATEGORY SPEND** - Questions like "identify all [year] dialysis chair spend", "all office supplies spend", "spare parts spend" (PRIORITY OVER general GL spend queries)
- **CATEGORY CLUSTERING** - Any question about specific product categories or "cluster transactions"
- **UNCATEGORIZED SPEND** - Any question about "don't fit categories", "uncategorized", "doesn't fit existing categories"
- Category clustering (group transactions by product category)
- Supplier consolidation analysis (identify top preferred suppliers vs tail suppliers)
- Tail spend identification (find palmers/departments using non-preferred suppliers)
- Uncategorized spend detection (identify spend lines that don't fit existing categories)
- Savings opportunity highlighting (show potential savings from supplier consolidation)
- Product category spend identification (all spend for specific categories like "dialysis chairs", "spare parts")
- Palmer/department spending breakdown by supplier type (preferred vs tail)
- Percentage calculations (% of spend outside preferred suppliers)

**Example queries:**
- "Cluster transactions for a product category, list top suppliers, and show palmers spending outside preferred suppliers"
- "Identify suppliers or spend lines that don't fit existing categories"
- "Identify all spend for a specific product category in a given year"
- "For a category, identify preferred suppliers and show savings opportunity from consolidating tail spend"
- "Show spend for a category and identify which palmers are using non-preferred suppliers"
- "What's the uncategorized spend for a time period?"
- "Which departments have highest percentage of spend with tail suppliers for a category?"

**Key characteristics:**
- Clusters/classifies transactions into product categories using line_item_category (L4 taxonomy)
- Identifies top suppliers (preferred) and tail suppliers (non-preferred, lower volume)
- Breaks down by palmer/department to show consolidation opportunities
- Calculates savings potential from moving tail spend to preferred suppliers
- Uses 3-step workflow: SQL Generation → Validation → Execution
- Results depend on upstream LLM parser classification accuracy for categories

---

### 5. Contract Intelligence Agent (`contract_intelligence_agent`)
Delegate contract-to-invoice comparison, price discrepancy detection, and savings analysis here.

**When to use (HIGH PRIORITY for contract/pricing keywords):**
- **CONTRACT PRICING** - Any question with "contract price", "contracted rate", "price discrepancy", "pricing variance"
- **INVOICE RECONCILIATION** - Matching invoices to contracts and POs, three-way match
- **CONTRACT GAP ANALYSIS** - Suppliers with spend but no contracts
- Contract-to-invoice price comparison and discrepancy detection
- Savings opportunity identification from pricing variances
- Three-way match analysis (Contract → PO → Invoice)
- Both INDIRECT spend (COUPA) and DIRECT spend (IPRO) analysis
- Supplier contract coverage assessment

**Example queries:**
- "Compare contract prices vs actual invoice charges for a supplier"
- "Which suppliers have spend but no contracts?"
- "Show price discrepancies between contracts and invoices for a category"
- "Run a three-way match analysis for Contract → PO → Invoice"
- "What savings could we capture by enforcing contract pricing?"
- "Identify invoices charged above the contracted rate"
- "Reconcile invoices against contract terms for a specific vendor"

**Key characteristics:**
- Compares contract pricing against actual invoice charges
- Detects pricing variances and overcharges
- Identifies suppliers without contract coverage (contract gaps)
- Performs three-way match: Contract → PO → Invoice
- Analyzes both indirect (Coupa) and direct (iProcurement) spend
- Quantifies savings from enforcing contracted rates

---

### 6. Financial Leakage Agent (`financial_leakage_agent`)
Delegate detection of inappropriate spend, personal purchases, unauthorized subscriptions, and leakage risk scoring here.

**When to use (HIGH PRIORITY for leakage/inappropriate spend keywords):**
- **FINANCIAL LEAKAGE** - Any question with "leakage", "inappropriate spend", "shouldn't be spending", "wasteful spend"
- **PERSONAL PURCHASES** - Detection of personal electronics, luxury items, gift cards on company accounts
- **UNAUTHORIZED SUBSCRIPTIONS** - Detecting unauthorized memberships, streaming services, subscriptions
- **MAVERICK BUYING PATTERNS** - Purchases without POs that suggest policy violations
- GL line item scanning for trigger words indicating personal/inappropriate spend
- Category mismatch detection (items booked under wrong account categories)
- Leakage risk scoring and classification (High/Medium/Low)

**Example queries:**
- "Scan GL for potential financial leakage this quarter"
- "Find any personal electronics purchases on company accounts"
- "Detect unauthorized subscriptions or memberships in our spend"
- "Which line items look like personal purchases without POs?"
- "Score and classify leakage risk for flagged items"
- "Find gift card purchases or luxury items in the GL"
- "Identify maverick purchases that could be financial leakage"
- "What inappropriate spend has been detected this year?"

**Key characteristics:**
- Scans GL line items for trigger words (personal electronics, luxury items, gift cards, subscriptions)
- Identifies maverick/unmanaged purchases (no PO) as higher leakage risk
- Scores each finding using leakage likelihood factors (0.0–1.0)
- Classifies risk: High (0.7–1.0), Medium (0.4–0.69), Low (0.0–0.39)
- Reports flagged items with amounts, vendors, categories, and risk levels
- Detects category mismatches (items booked under wrong account categories)

---

### 7. Multi-Domain Delegation Scenarios

**Note:** With the delegation pattern, each sub-agent handles the full conversation. If a question spans multiple domains, delegate to the primary domain agent first. They can escalate back to you if needed.

**Scenario A: Savings Estimation (Auditor)**
- Query: "Estimate the potential annual savings for a specific GL account category if the spend is moved from tail spend suppliers to a preferred supplier, assuming a negotiated discount on the consolidated spend."
- Delegate to: `auditor_agent` (detailed financial calculation with specific GL account, discount percentage)

**Scenario B: Category Consolidation + Savings (Supplier Classification)**
- Query: "For dialysis chairs category, identify the top preferred suppliers and consolidate matching items from tail suppliers highlighting the savings opportunity"
- Delegate to: `supplier_classification_agent` (clustering, preferred vs tail identification, savings opportunity highlighting)

**Scenario C: Invoice Line Item Details (Buyer)**
- Query: "Tell me what exactly is a specific item from a given invoice, who bought it from a PO perspective, for how much, and who sold it?"
- Delegate to: `buyer_agent` (specific line item lookup with buyer/seller/price details)

**Scenario D: Forecast Analysis (Trend)**
- Query: "Compare the actual historical daily spend to the forecasted spend for a Group VP code. Show both actuals and forecasts on a unified timeline."
- Delegate to: `trend_agent` (forecast vs actuals comparison)

**Scenario E: GL Search with Filters (Auditor)**
- Query: "Search the GL in a specific palmer for a given year YTD for all line items in Travel and Entertainment accounts with a specific teammate name"
- Delegate to: `auditor_agent` (complex GL query with palmer, account, teammate, date filters)

**Scenario F: Uncategorized Spend (Supplier Classification)**
- Query: "Identify suppliers or spend lines that don't fit into any existing product categories"
- Delegate to: `supplier_classification_agent` (uncategorized spend detection)

**Scenario G: Contract Price Discrepancy (Contract Intelligence)**
- Query: "Compare contract prices vs actual invoice charges for our top medical supply vendors and identify overcharges"
- Delegate to: `contract_intelligence_agent` (contract-to-invoice price comparison)

**Scenario H: Financial Leakage Detection (Financial Leakage)**
- Query: "Scan our GL for any personal electronics or luxury item purchases that shouldn't be on company accounts"
- Delegate to: `financial_leakage_agent` (inappropriate spend detection with leakage scoring)

---

### 8. Delegation Decision Tree

Use this decision tree for ALL queries (check in strict priority order — use the FIRST match):

1.  **Does it mention "forecast", "forecasted", "predicted", "actuals vs", "trend decomposition", "seasonal", or Group VP forecasts?** → `trend_agent`
2.  **Does it ask to scan GL line descriptions for specific product words/brands (e.g., Airpod, iPad, espresso) or ask about inappropriate/personal spend, leakage, or unauthorized subscriptions?** → `financial_leakage_agent`
3.  **Does it mention "contract", "agreement", "SOW", "commitments", "penalties", "rebates", "contracted rate", "clauses", pricing comparisons between suppliers, or a supplier name when asking about their contract/agreement terms?** → `contract_intelligence_agent`
4.  **Does it ask about clustering transactions, product category spend (e.g., "dialysis chairs", "spare parts"), uncategorized spend, "don't fit categories", supplier consolidation, or preferred vs tail suppliers?** → `supplier_classification_agent`
5.  **Does it ask about "unmanaged items", "item N from invoice", "PO perspective", "who bought/sold", managed vs unmanaged detection, or Purchase Order relationships?** → `buyer_agent`
6.  **Is it about GL queries, invoice lookups (find invoice, confirm payment), expense filtering, financial calculations, or savings estimation from spend consolidation?** → `auditor_agent`
7.  **Is it about trends over time (MoM, YoY) or spending patterns?** → `trend_agent`

### 9. Critical Disambiguation Rules

- **"unmanaged items" on an invoice** → `buyer_agent` (NOT auditor — buyer handles PO/managed vs unmanaged)
- **"compare pricing between suppliers" or "rebates in agreement"** → `contract_intelligence_agent` (NOT auditor)
- **"GL line descriptions contain words like Airpod, iPad, espresso"** → `financial_leakage_agent` (NOT auditor — this is personal spend detection)
- **"cluster transactions" or "don't fit categories"** → `supplier_classification_agent` (NOT auditor)
- **"forecasted spend" or "actuals vs forecast"** → `trend_agent` (NOT auditor)
- **A bare supplier name (e.g., "Corporate Relocation International")** → `contract_intelligence_agent` (asking about the supplier's contract/agreement)
- **"cost efficient alternative without violating agreement terms"** → `contract_intelligence_agent` (contract constraint analysis)
- **"SOW", "clauses", "commitments and penalties"** → `contract_intelligence_agent`

---

### 10. Special Delegation Notes

**Invoice Questions:**
- Invoice **line item** details ("item 5 from invoice X", "what exactly is item N", who bought/sold specific items) → Delegate to `buyer_agent` (CHECK THIS FIRST)
- General invoice lookup (find invoice X, confirm payment status, invoice totals) → Delegate to `auditor_agent`

**Spending Questions:**
- **Product category spend** ("dialysis chairs", "spare parts", "office supplies") → Delegate to `supplier_classification_agent` (CHECK THIS FIRST)
- Spend with category clustering/consolidation → Delegate to `supplier_classification_agent`
- GL account/department/location spend queries (without product category) → Delegate to `auditor_agent`
- Spend trends over time (MoM, YoY) → Delegate to `trend_agent`
- General spend questions without context → Delegate to `trend_agent`

**Savings Questions:**
- Detailed savings estimation with financial calculations → Delegate to `auditor_agent`
- Savings from supplier consolidation (tail → preferred) → Delegate to `supplier_classification_agent`
- Savings from contract pricing variances or rebate optimization → Delegate to `contract_intelligence_agent`

**Vendor/Supplier Questions:**
- Top suppliers for a category, preferred vs tail → Delegate to `supplier_classification_agent`
- Vendor trends over time → Delegate to `trend_agent`
- Vendor details for specific invoice items → Delegate to `buyer_agent`
- Vendor contract pricing or savings → Delegate to `contract_intelligence_agent`

**Contract Questions:**
- Contract pricing vs invoice comparison → Delegate to `contract_intelligence_agent`
- Suppliers without contracts (gap analysis) → Delegate to `contract_intelligence_agent`
- Contract terms, rebates, clauses → Delegate to `contract_intelligence_agent`
- Invoice reconciliation against contracts/POs → Delegate to `contract_intelligence_agent`

**Division/Palmer/Region Questions:**
- Palmer spending outside preferred suppliers → Delegate to `supplier_classification_agent`
- Palmer spending trends over time → Delegate to `trend_agent`
- Palmer GL queries (specific accounts, teammates) → Delegate to `auditor_agent`

**Forecasting Questions:**
- Forecast vs actuals, decomposition, confidence intervals → Delegate to `trend_agent`

**Uncategorized/Clustering Questions:**
- Identify uncategorized spend, cluster by category → Delegate to `supplier_classification_agent`

**Managed vs Unmanaged (Maverick) Questions:**
- Check if invoice has unmanaged items → Delegate to `buyer_agent`
- Maverick purchases as potential financial leakage → Delegate to `financial_leakage_agent`

**Contract/Pricing Questions:**
- Contract-to-invoice price comparison, price discrepancies → Delegate to `contract_intelligence_agent`
- Suppliers with spend but no contracts (contract gaps) → Delegate to `contract_intelligence_agent`
- Three-way match (Contract → PO → Invoice) → Delegate to `contract_intelligence_agent`
- Savings from enforcing contract pricing → Delegate to `contract_intelligence_agent`

**Financial Leakage Questions:**
- Inappropriate spend, personal purchases, luxury items → Delegate to `financial_leakage_agent`
- Unauthorized subscriptions, memberships, streaming → Delegate to `financial_leakage_agent`
- Leakage risk scoring and classification → Delegate to `financial_leakage_agent`
- GL scanning for trigger words (electronics, gift cards, etc.) → Delegate to `financial_leakage_agent`

**Response Guidelines:**
- When greeting the user or answering general questions, respond directly
- For domain-specific queries, **delegate immediately** to the appropriate sub-agent
- Once delegated, the sub-agent will continue the conversation
- If a sub-agent escalates back to you (e.g., domain shift), re-analyze and route accordingly

**CRITICAL: NEVER answer data or analytics queries yourself.**
- You do NOT have access to any databases, SQL tools, or query execution capabilities.
- You MUST NOT fabricate, hallucinate, or guess query results (e.g., "the query returned 0 rows").
- If the query involves looking up data, running SQL, checking expenses, invoices, vendors, accounts, or any financial records, you MUST delegate to the appropriate sub-agent.
- If no sub-agent is available or configured for the query, tell the user that the required agent is not available — do NOT attempt to answer the data question yourself.

**Handling Uncertainty:**
If you cannot provide a definitive answer, route to an appropriate sub-agent, or compute the requested information, it is acceptable and expected to respond with "I don't know" or "I can't compute that." Explain concisely why you cannot fulfill the request (e.g., no suitable sub-agent available, query is out of scope, insufficient context) without attempting to fabricate an answer or offer alternative approaches.

**Conversation Context:**
- Use conversation history from earlier turns when it helps with routing decisions
- After delegation, the sub-agent maintains the conversation context
- If you receive control back from a sub-agent, understand why they escalated and route accordingly
"""

# Define the Spend IQ agent with sub-agents and guardrails
root_agent = LlmAgent(
    name="spend_iq_agent",
    model="gemini-2.5-pro",
    description="Spend IQ agent that delegates to specialized sub-agents based on query domain.",
    instruction=instruction,
    sub_agents=sub_agents if sub_agents else [],
    before_model_callback=guardrail_before_model,
    after_model_callback=guardrail_after_model,
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

logger.info("Spend IQ Agent initialization complete")

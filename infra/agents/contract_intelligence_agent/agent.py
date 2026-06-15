"""Contract Intelligence Agent - AI-powered contract-to-invoice comparison and savings detection.

Architecture: Root agent with DIRECT tool access + 4 specialized sub-agents.
The root agent uses direct tools for supplier disambiguation and quick lookups,
then delegates to sub-agents for heavy-lift contract retrieval, reconciliation,
comparison, and recommendation work.
"""

from __future__ import annotations

import logging
import os
import pathlib
import re
import threading
import time
import uuid
from typing import Any, Optional

import vertexai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.adk.tools import agent_tool
from google.genai import types as genai_types
from vertexai.agent_engines import AdkApp

try:
    from opentelemetry import trace as otel_trace
    _tracer = otel_trace.get_tracer("cia.agent")
    _HAS_OTEL = True
except ImportError:
    _tracer = None
    _HAS_OTEL = False

try:
    from .utils import get_mcp_toolset, get_genai_tools, rate_limit_before_model_callback
    from .sql_validation import validate_sql_columns as _validate_sql_columns, validate_sql_safety as _validate_sql_safety
    from .multi_region_model import MultiRegionRetryGemini
    from .dedup_cache import check_cache as _dedup_check, store_result as _dedup_store
except ImportError:
    from utils import get_mcp_toolset, get_genai_tools, rate_limit_before_model_callback
    from sql_validation import validate_sql_columns as _validate_sql_columns, validate_sql_safety as _validate_sql_safety
    from multi_region_model import MultiRegionRetryGemini
    from dedup_cache import check_cache as _dedup_check, store_result as _dedup_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cia.agent")

logger.info("Initializing Contract Intelligence Agent")

_AGENT_LOAD_TIME = time.time()

logger.info("Loading sub-agent modules")

# Import CIA-specific agents (all agents are now local to CIA)
try:
    from .cia_retriever_agent import cia_retriever_agent
    from .cia_reconciliation_agent import cia_reconciliation_agent
    from .cia_recommendation_agent import cia_recommendation_agent
    from .comparison_agent import comparison_agent
except ImportError:
    from cia_retriever_agent import cia_retriever_agent
    from cia_reconciliation_agent import cia_reconciliation_agent
    from cia_recommendation_agent import cia_recommendation_agent
    from comparison_agent import comparison_agent


###########################################
######### BEFORE-TOOL CALLBACK ############
###########################################

# Track sub-agent call start times for latency logging (thread-safe).
# Key includes thread ID to prevent concurrent requests from overwriting
# each other's start times (Cloud Run containerConcurrency=5).
_tool_start_times: dict[str, float] = {}
_tool_start_times_lock = threading.Lock()

# Sub-agent tool names for latency tracking and Cloud Trace spans
_SUB_AGENT_TOOLS = frozenset(
    ["cia_retriever_agent", "cia_reconciliation_agent",
     "contract_comparison_agent", "cia_recommendation_agent"]
)

# Deduplication is handled by the shared dedup_cache module.
# Covers sub-agent tools + RAG tools (rag_search, rag_search_batch).
# The same cache instance is shared with sub-agents (retriever,
# recommendation) so cross-agent duplicate RAG calls are also caught.

# Track whether the first tool call per thread has been logged for
# orchestrator-to-first-tool latency measurement.
_first_tool_logged: set[int] = set()
_first_tool_logged_lock = threading.Lock()

# Query-level latency telemetry — tracks query_id and wall-clock per thread.
# Key = thread ID, Value = (query_id, start_time, tool_count).
_query_tracking: dict[int, tuple[str, float, int]] = {}
_query_tracking_lock = threading.Lock()

# --- Supplier-name sanitisation for BigQuery tools ---
# The LLM sometimes passes full counterparty strings from RAG output
# (e.g. "Pivium, Inc., f/k/a D&L Communication Systems, Inc.") as the
# supplier_name arg to ssi_get_* tools.  The SQL uses LIKE '%…%' so
# including DBA/FKA text guarantees zero rows.  We strip these here.
_DBA_STRIP_RE = re.compile(
    r"\s*\b(?:d/?b/?a|doing\s+business\s+as|on\s+behalf\s+of"
    r"|f/?k/?a|formerly\s+known\s+as)\b.*",
    re.IGNORECASE,
)
_QUALIFIER_STRIP_RE = re.compile(
    r",?\s+(?:specifically|including|especially|particularly)\b.*",
    re.IGNORECASE,
)
_PAREN_STRIP_RE = re.compile(r"\s*\([^)]*\)")
_LEGAL_SUFFIX_RE = re.compile(
    r",?\s+(?:Inc\.?|LLC|LP|LLP|Corp\.?|Corporation|Company|Co\.?|Ltd\.?|Limited)\s*$",
    re.IGNORECASE,
)


def _clean_supplier_name(raw: str) -> str:
    """Extract core supplier name from a full counterparty string."""
    cleaned = _DBA_STRIP_RE.sub("", raw).strip().rstrip(",").strip()
    cleaned = _QUALIFIER_STRIP_RE.sub("", cleaned).strip()
    cleaned = _PAREN_STRIP_RE.sub("", cleaned).strip()
    cleaned = _LEGAL_SUFFIX_RE.sub("", cleaned).strip().rstrip(",").strip()
    return cleaned or raw


_SSI_SUPPLIER_TOOLS = frozenset([
    "ssi_get_supplier_invoices",
    "ssi_get_supplier_invoices_paginated",
    "ssi_get_invoice_pricing",
    "ssi_get_invoice_pricing_paginated",
    "ssi_get_supplier_spend",
    "ssi_get_catalog_prices",
    "ssi_get_po_prices",
    "ssi_get_contract_linked_invoices",
    "ssi_get_contract_linked_invoices_paginated",
    "ssi_get_contract_dates",
    "ssi_get_supplier_invoice_count",
    "ssi_find_suppliers_without_contracts",
])


def before_tool_callback(
    tool: Any,
    args: dict[str, Any],
    tool_context: Any,
) -> Optional[dict]:
    """Validate tool inputs before execution.

    Blocks destructive SQL operations (only SELECT allowed).
    Enforces dataset whitelist to prevent data exfiltration.
    Logs every tool invocation for audit trail.
    Tracks sub-agent call start times for latency monitoring.

    Signature: (BaseTool, dict, ToolContext) -> Optional[dict]
    per google.adk.agents.llm_agent._SingleBeforeToolCallback
    """
    tool_name = getattr(tool, "name", str(tool))
    logger.info(
        "before_tool_callback: tool=%s | input_keys=%s",
        tool_name,
        list(args.keys()),
    )

    # Log time from module load to first tool call per thread.
    # This captures the orchestrator routing + session setup overhead
    # that precedes any actual tool work.
    tid = threading.get_ident()
    with _first_tool_logged_lock:
        is_first = tid not in _first_tool_logged
        if is_first:
            _first_tool_logged.add(tid)
    if is_first:
        elapsed = time.time() - _AGENT_LOAD_TIME
        logger.info(
            "FIRST_TOOL_CALL thread=%d | tool=%s | time_since_agent_load=%.1fs",
            tid, tool_name, elapsed,
        )

    # Query-level telemetry — assign query_id on first tool call per thread.
    with _query_tracking_lock:
        if tid not in _query_tracking:
            qid = uuid.uuid4().hex[:12]
            _query_tracking[tid] = (qid, time.time(), 0)
            logger.info("QUERY_START query_id=%s thread=%d first_tool=%s", qid, tid, tool_name)
        qid, q_start, tool_count = _query_tracking[tid]
        _query_tracking[tid] = (qid, q_start, tool_count + 1)
    logger.info(
        "TOOL_CALL query_id=%s tool=%s tool_seq=%d wall_clock=%.1fs",
        qid, tool_name, tool_count + 1, time.time() - q_start,
    )

    # ------------------------------------------------------------------
    # Sub-agent arg-key repair (observed bug 2026-04-23).
    # ------------------------------------------------------------------
    # The root model occasionally emits a sub-agent function_call with the
    # SUPPLIER NAME used as the parameter key instead of the correct
    # `request` key, e.g.:
    #     function_call(
    #         name="cia_recommendation_agent",
    #         args={"The Parnassus Group": "<task text>"},
    #     )
    # Gemini's server-side schema validator rejects this with the phrase
    # "<supplier> is not a valid argument for tool <tool>. The following
    # parameters are valid: request." — and that phrase can then leak
    # into the model's final markdown response as a degenerate runaway
    # repetition (seen in a multi-supplier comparison output where a
    # table cell was filled with 200+ copies of the validation error).
    #
    # All ADK `AgentTool` wrappers take exactly one parameter (`request`),
    # so whenever we see a call into _SUB_AGENT_TOOLS with the wrong
    # shape we coerce it to `{"request": "<joined text>"}` in-place.
    # This is safe: the callback signature lets us mutate `args` and
    # ADK will pass the repaired dict to the tool.
    if tool_name in _SUB_AGENT_TOOLS and "request" not in args and args:
        # Join all string-valued args into a single request body so we
        # don't silently drop the supplier name or the task text.
        repaired = " ".join(
            f"{k}: {v}" if k else str(v)
            for k, v in args.items()
            if isinstance(v, (str, int, float))
        ).strip()
        # Fallback if nothing stringy was found — use first value as-is.
        if not repaired and args:
            first_val = next(iter(args.values()))
            repaired = str(first_val)
        logger.warning(
            "REPAIRED malformed sub-agent call: tool=%s | bad_keys=%s | "
            "folded into request (first 200 chars): %r",
            tool_name, list(args.keys()), repaired[:200],
        )
        # Mutate args in place — clear old keys, set `request`.
        args.clear()
        args["request"] = repaired

    # ------------------------------------------------------------------
    # Sanitise supplier_name for BigQuery tools.
    # ------------------------------------------------------------------
    if tool_name in _SSI_SUPPLIER_TOOLS and "supplier_name" in args:
        raw = str(args["supplier_name"])
        cleaned = _clean_supplier_name(raw)
        if cleaned != raw:
            logger.info(
                "Cleaned supplier_name for %s: %r -> %r",
                tool_name, raw, cleaned,
            )
            args["supplier_name"] = cleaned

    # Deduplication — block identical re-calls and return cached result.
    # Uses the shared dedup_cache module (same cache as sub-agents).
    cached = _dedup_check(tool_name, args, tool_context)
    if cached is not None:
        return cached

    # Track sub-agent call start times for latency logging
    if tool_name in _SUB_AGENT_TOOLS:
        key = f"{tool_name}_{threading.get_ident()}"
        with _tool_start_times_lock:
            _tool_start_times[key] = time.time()
        logger.info("Sub-agent call started: %s", tool_name)

    # Validate SQL in any tool that accepts SQL (shared with sub-agents)
    if tool_name in ("ssi_execute_sql", "execute_sql_tool"):
        sql = str(
            args.get("sql", "")
            or args.get("statement", "")
            or ""
        )
        logger.info(
            "SQL query submitted: tool=%s | sql=%s",
            tool_name,
            sql[:500],
        )

        safety_error = _validate_sql_safety(sql)
        if safety_error:
            logger.warning("BLOCKED: %s | sql=%s", safety_error, sql[:200])
            return {"error": safety_error}

        col_error = _validate_sql_columns(sql)
        if col_error:
            logger.warning(
                "BLOCKED invalid column reference: %s | sql=%s",
                col_error, sql[:300],
            )
            return {"error": col_error}

    return None  # Proceed with tool execution


# --- Supplier mismatch detection (context-aware) ---
# Keywords that signal a FULL mismatch when they appear as the overall
# Match Status (not merely describing individual excluded documents).
_FULL_MISMATCH_KEYWORDS = frozenset(
    ["WRONG SUPPLIER", "DOES NOT BELONG", "WRONG_SUPPLIER"]
)

# Regex to extract the "Match Status:" structured field from the
# retriever's response.  Handles markdown formatting variants:
#   - **Match Status**: CONFIRMED
#   - - **Match Status**: CONFIRMED (for X), excluded others
#   - Match Status: MISMATCH
_MATCH_STATUS_RE = re.compile(
    r"\*{0,2}Match\s+Status\*{0,2}\s*:?\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)


_FILTER_KEPT_RE = re.compile(
    r"Contracts included from",
    re.IGNORECASE,
)

_SUPPLIER_FROM_REQUEST_RE2 = re.compile(
    r"(?:for\s+)?supplier:\s*(.+?)(?:\.\s|$)", re.IGNORECASE,
)


def _supplier_filter_kept_docs(response_text: str) -> bool:
    """Check if the retriever's supplier filter kept any documents.

    The supplier filter appends a summary with "Contracts included from"
    when it kept documents for matching counterparties.  If this line
    exists, the filter's alias logic confirmed the documents belong to
    the requested supplier — even if the counterparty name differs
    (e.g., Baxter docs kept for a Vantive query via alias).
    """
    return bool(_FILTER_KEPT_RE.search(response_text))


def _request_has_manual_alias(request_text: str) -> bool:
    """Check if the request is for a supplier with a curated cross-name alias.

    Only checks the _MANUAL_ALIASES dict (e.g., Vantive <-> Baxter),
    NOT the full f/k/a alias map.  The full map contains 700+ entries
    with generic words ("city", "health", "pro") that would disable
    the MISMATCH safety net too broadly.

    Manual aliases are for corporate renames where the names are
    completely different and the LLM cannot recognise the relationship.
    """
    try:
        try:
            from .cia_retriever_agent import _MANUAL_ALIASES
        except ImportError:
            from cia_retriever_agent import _MANUAL_ALIASES
    except Exception:
        return False

    m = _SUPPLIER_FROM_REQUEST_RE2.search(request_text)
    if not m:
        return False
    supplier = m.group(1).strip().lower()
    if supplier in _MANUAL_ALIASES:
        return True
    for word in re.split(r"\s+(?:and|or)\s+|\s*[,(]\s*", supplier):
        word = word.strip().lower()
        if word and word in _MANUAL_ALIASES:
            return True
    return False


def _classify_retriever_match(response_text: str) -> str:
    """Classify the overall supplier match from the retriever response.

    Parses the structured ``Match Status`` field and cross-checks with
    the presence of verified result sections to decide whether the
    retriever found the correct supplier's contracts.

    Returns one of:
        ``"CONFIRMED"`` — correct supplier found; safe to use.
        ``"MISMATCH"``  — wrong supplier only; must hard-block.
        ``"PARTIAL"``   — ambiguous match; should block.
        ``"UNKNOWN"``   — could not parse; allow through and let the
                          root agent's own verification handle it.
    """
    response_upper = response_text.upper()

    filter_kept = _supplier_filter_kept_docs(response_text)

    # ── 1. Parse the structured "Match Status:" field ──────────────
    match = _MATCH_STATUS_RE.search(response_text)
    if match:
        status_line = match.group(1).upper()
        # CONFIRMED anywhere on the status line means the retriever
        # verified at least one correct supplier document.  It may
        # also mention excluded/discarded docs for other suppliers —
        # that is expected and should NOT trigger a hard block.
        if "CONFIRMED" in status_line:
            return "CONFIRMED"
        if "PARTIAL" in status_line or "MISMATCH" in status_line:
            if filter_kept:
                logger.info(
                    "Retriever LLM said %s but supplier filter kept "
                    "documents (alias match) — overriding to CONFIRMED",
                    status_line.strip(),
                )
                return "CONFIRMED"
            if "PARTIAL" in status_line:
                return "PARTIAL"
            return "MISMATCH"

    # ── 2. No Match Status line — use structural heuristics ────────
    # Look for verified result sections that indicate confirmed data.
    has_verified_results = bool(re.search(
        r"(?:Source Document|Supplier/Party|Extracted Content"
        r"|Contract Status|Pricing Terms)",
        response_text,
        re.IGNORECASE,
    ))

    # Check for unambiguous full-mismatch signals (these keywords
    # are NOT used in "excluded documents" descriptions).
    has_hard_mismatch = any(
        kw in response_upper for kw in _FULL_MISMATCH_KEYWORDS
    )

    if has_verified_results and not has_hard_mismatch:
        return "CONFIRMED"
    if has_hard_mismatch and not has_verified_results:
        if filter_kept:
            logger.info(
                "Hard mismatch keywords found but supplier filter "
                "kept documents — overriding to CONFIRMED",
            )
            return "CONFIRMED"
        return "MISMATCH"
    if has_verified_results and has_hard_mismatch:
        # Mixed signals — verified results exist alongside a mismatch
        # keyword.  Trust the structured results; the root agent's own
        # verification (system.md §2b) provides a second safety net.
        return "CONFIRMED"

    # ── 3. Cannot determine — safer to allow than to false-block ───
    return "UNKNOWN"

# --- 2.1: Response sanitization — strip internal agent/tool names ---
_INTERNAL_NAME_REPLACEMENTS = {
    # Sub-agent internal names (underscore format)
    "cia_retriever_agent": "contract document search",
    "cia_recommendation_agent": "recommendation analysis",
    "cia_reconciliation_agent": "data reconciliation",
    "contract_comparison_agent": "price comparison analysis",
    # Sub-agent natural-language references (model sometimes uses these)
    "retriever agent": "contract document search",
    "recommendation agent": "recommendation analysis",
    "reconciliation agent": "data reconciliation",
    "comparison agent": "price comparison analysis",
    "retriever sub-agent": "contract document search",
    "recommendation sub-agent": "recommendation analysis",
    "reconciliation sub-agent": "data reconciliation",
    "comparison sub-agent": "price comparison analysis",
    # MCP / RAG tool names
    "graphrag_query": "contract database search",
    "rag_search": "document search",
    "aggregate_answer": "multi-source search",
    "execute_sql_tool": "data query",
    # GenAI Toolbox tool names
    "ssi_execute_sql": "data query",
    "ssi_get_supplier_invoices": "invoice lookup",
    "ssi_get_supplier_invoices_paginated": "invoice lookup",
    "ssi_get_invoice_pricing": "pricing lookup",
    "ssi_get_invoice_pricing_paginated": "pricing lookup",
    "ssi_find_suppliers_without_contracts": "contract gap analysis",
    "ssi_get_supplier_spend": "spend analysis",
    "ssi_get_catalog_prices": "catalog pricing lookup",
    "ssi_get_po_prices": "purchase order pricing lookup",
    "ssi_get_contract_linked_invoices": "contract-linked invoice lookup",
    "ssi_get_contract_dates": "contract metadata lookup",
    "ssi_get_supplier_invoice_count": "invoice count lookup",
}


_TOOL_VALIDATION_ERROR_RE = re.compile(
    r"[\w\s'\"]*?\s*is not a valid argument for tool \w+\."
    r"(?:\s*The following parameters are valid: request\.)*",
    re.DOTALL,
)

# Strip internal prompt/step routing numbers that leak into the response.
# Matches patterns like "#2 #3 #4", "STEP 1 STEP 2", "#1, #3", etc.
# at the very start of the response (before any real content).
_LEADING_STEP_NUMBERS_RE = re.compile(
    r"^\s*(?:(?:#\d+[\s,;]*)+|(?:STEP\s+\d+[\s,;]*)+)\s*",
    re.IGNORECASE,
)


def sanitize_response_text(text: str) -> str:
    """Strip internal agent/tool names and leaked error messages from response.

    1. Removes tool-validation error traces that Gemini's schema validator
       injects into the text stream on malformed function_call attempts.
    2. Strips leading prompt/step routing numbers (e.g. "#2 #3 #4").
    3. Replaces internal agent/tool names with business-friendly labels.
    """
    text = _TOOL_VALIDATION_ERROR_RE.sub("", text)
    text = _LEADING_STEP_NUMBERS_RE.sub("", text)
    for internal_name, friendly_name in _INTERNAL_NAME_REPLACEMENTS.items():
        text = text.replace(f"`{internal_name}`", friendly_name)
        text = re.sub(re.escape(internal_name), friendly_name, text, flags=re.IGNORECASE)
    return text

# --- 3.2: Sub-agent timeout threshold (seconds) ---
_SUB_AGENT_TIMEOUT_WARN_S = 90


def after_tool_callback(
    tool: Any,
    args: dict[str, Any],
    tool_context: Any,
    tool_response: dict,
) -> Optional[dict]:
    """Post-process tool responses for quality checks.

    - Logs sub-agent call latency for performance monitoring.
    - Records Cloud Trace spans for sub-agent calls (when OpenTelemetry available).
    - Detects supplier name mismatches in retriever responses and injects
      a structured warning so the root agent doesn't use wrong-contract data.

    Signature: (BaseTool, dict, ToolContext, dict) -> Optional[dict]
    per google.adk.agents.llm_agent._SingleAfterToolCallback
    """
    tool_name = getattr(tool, "name", str(tool))

    # Dedup caching — store result in the shared cache
    _dedup_store(tool_name, args, tool_response, tool_context)

    # Query-level telemetry — log tool completion with wall clock.
    tid = threading.get_ident()
    with _query_tracking_lock:
        tracking = _query_tracking.get(tid)
    if tracking:
        qid, q_start, _ = tracking
        logger.info(
            "TOOL_DONE query_id=%s tool=%s wall_clock=%.1fs",
            qid, tool_name, time.time() - q_start,
        )

    # Sub-agent latency logging and Cloud Trace spans.
    # Wrapped in RuntimeError guard: MCP cancel-scope errors can propagate
    # through sub-agent returns during ADK task transitions. Suppressing
    # them here prevents the parent session from crashing.
    if tool_name in _SUB_AGENT_TOOLS:
        try:
            key = f"{tool_name}_{threading.get_ident()}"
            with _tool_start_times_lock:
                start_time = _tool_start_times.pop(key, None)
            if start_time is not None:
                elapsed_s = time.time() - start_time
                logger.info(
                    "Sub-agent call completed: %s | latency=%.1fs",
                    tool_name,
                    elapsed_s,
                )
                if elapsed_s > 60:
                    logger.warning(
                        "SLOW sub-agent call: %s took %.1fs (>60s threshold)",
                        tool_name,
                        elapsed_s,
                    )

                # Record Cloud Trace span if OpenTelemetry is available
                if _HAS_OTEL and _tracer is not None:
                    try:
                        with _tracer.start_as_current_span(
                            f"sub_agent.{tool_name}",
                        ) as span:
                            span.set_attribute("sub_agent.name", tool_name)
                            span.set_attribute("sub_agent.latency_s", elapsed_s)
                            span.set_attribute(
                                "sub_agent.slow", elapsed_s > 60
                            )
                            request_text = str(args.get("request", ""))[:200]
                            span.set_attribute(
                                "sub_agent.request_summary", request_text
                            )
                    except Exception:
                        pass  # Tracing should never break the agent
        except RuntimeError as e:
            if "cancel scope" in str(e).lower():
                logger.warning(
                    "MCP cancel-scope RuntimeError in after_tool_callback "
                    "for %s (suppressed — session preserved): %s",
                    tool_name, e,
                )
            else:
                raise

    # Supplier mismatch detection for retriever agent — context-aware.
    # Uses structured Match Status parsing instead of naive keyword scan
    # to avoid false-positive blocking when the retriever correctly
    # discards *some* documents while confirming the requested supplier.
    if tool_name == "cia_retriever_agent":
        if isinstance(tool_response, dict):
            response_text = str(tool_response.get("retrieval_result", ""))
        else:
            response_text = str(tool_response)

        match_class = _classify_retriever_match(response_text)
        request_text = str(args.get("request", ""))[:200]

        if match_class in ("MISMATCH", "PARTIAL"):
            if _request_has_manual_alias(request_text):
                logger.info(
                    "Retriever LLM said %s but supplier has known "
                    "aliases — overriding to CONFIRMED. Request: %s",
                    match_class,
                    request_text,
                )
            else:
                logger.warning(
                    "SUPPLIER %s in retriever response — stripping data. "
                    "Request: %s",
                    match_class,
                    request_text,
                )
                return {
                    "retrieval_result": (
                        "--- SUPPLIER MISMATCH DETECTED ---\n"
                        "NO CONTRACT DATA AVAILABLE for the requested supplier. "
                        "Documents found belong to a different supplier and have "
                        "been discarded. Do NOT use any contract data from this "
                        "response. Proceed with invoice-only analysis at MEDIUM "
                        "confidence using the CORRECT supplier name only."
                    ),
                    "mismatch": True,
                }

        if match_class == "CONFIRMED":
            logger.info(
                "Supplier CONFIRMED in retriever response — passing "
                "contract data through. Request: %s",
                request_text,
            )
        else:
            logger.info(
                "Retriever match status UNKNOWN — allowing response "
                "through for root agent verification. Request: %s",
                request_text,
            )

    return None  # No modification


###########################################
######### DIRECT TOOLS (ROOT AGENT) #######
###########################################
logger.info("Loading direct tools for root agent")
mcp_toolset = get_mcp_toolset()
genai_mcp_tools = get_genai_tools("ssi-toolset")
logger.info(
    "Direct tools loaded: MCP=%s, GenAI=%d",
    bool(mcp_toolset),
    len(genai_mcp_tools),
)


###########################################
######### SUB-AGENT TOOLS #################
###########################################
logger.info("Creating sub-agent tools")
retriever_tool = agent_tool.AgentTool(agent=cia_retriever_agent)
reconciliation_tool = agent_tool.AgentTool(agent=cia_reconciliation_agent)
recommendation_tool = agent_tool.AgentTool(agent=cia_recommendation_agent)
comparison_tool = agent_tool.AgentTool(agent=comparison_agent)
logger.info(
    "Sub-agents configured: cia_retriever, cia_reconciliation, "
    "cia_recommendation, comparison"
)


###########################################
######### LOAD INSTRUCTION FROM FILE ######
###########################################
_instruction_path = (
    pathlib.Path(__file__).parent / "instruction" / "system.md"
)
try:
    instruction = _instruction_path.read_text(encoding="utf-8")
    logger.info(
        "Loaded instruction from %s (%d chars)",
        _instruction_path.name,
        len(instruction),
    )
except FileNotFoundError:
    logger.error("Instruction file not found: %s", _instruction_path)
    instruction = (
        "You are the Contract Intelligence Agent. "
        "Delegate to sub-agents for contract and invoice analysis."
    )


###########################################
######### AFTER-MODEL CALLBACK ############
###########################################
# finish_reason values that indicate a healthy, non-truncated response.
# Anything else (MAX_TOKENS, SAFETY, RECITATION, OTHER, LANGUAGE, BLOCKLIST,
# PROHIBITED_CONTENT, SPII, MALFORMED_FUNCTION_CALL) means the model was
# cut off or aborted and the user will see an incomplete result.
_HEALTHY_FINISH_REASONS = frozenset({"STOP", "TOOL_USE", "MODEL_ROUTER"})


# ---------------------------------------------------------------------------
# Runaway-repetition detector (observed bug 2026-04-23).
# ---------------------------------------------------------------------------
# After a sub-agent function_call was rejected with a "X is not a valid
# argument for tool ..." validation error, the root model got stuck in an
# attention-collapse loop and emitted the rejection phrase 200+ times inside
# a markdown table cell of its final response.  The Parnassus Group report
# reached the user with a table column filled by repeated error text.
#
# We defend against this class of degeneration post-hoc: scan the assembled
# text, and if any non-trivial phrase repeats beyond a threshold, collapse
# the run to a single instance + marker.  Detection is phrase-level
# (~40–160 chars) so natural boilerplate (common bullets, "The following")
# isn't touched.
_REPETITION_MIN_PHRASE_CHARS = 40
_REPETITION_MAX_PHRASE_CHARS = 200
_REPETITION_THRESHOLD = 5  # allow up to 4 legit repeats (e.g. table rows)


def _collapse_runaway_repetition(text: str) -> tuple[str, int]:
    """Collapse immediately-adjacent repeated phrases in ``text``.

    Returns ``(cleaned_text, collapsed_count)``.  A phrase is any
    substring between 40 and 200 chars that appears ≥ 5 times back-to-back
    (separated only by whitespace/punctuation).  Only touches contiguous
    runs — scattered duplicates elsewhere in the response are left alone.
    """
    if not text or len(text) < _REPETITION_MIN_PHRASE_CHARS * _REPETITION_THRESHOLD:
        return text, 0

    # Greedy regex: capture a phrase then require it to repeat ≥ threshold
    # times (allowing optional whitespace/punctuation separators between
    # repetitions).  Non-greedy on phrase length to prefer the shortest
    # repeating unit — avoids eating legitimate surrounding context.
    pattern = re.compile(
        r"(.{%d,%d}?)(?:[\s\.\|,;:\-]*\1){%d,}"
        % (
            _REPETITION_MIN_PHRASE_CHARS,
            _REPETITION_MAX_PHRASE_CHARS,
            _REPETITION_THRESHOLD - 1,
        ),
        re.DOTALL,
    )
    collapsed = 0

    def _replace(m: re.Match) -> str:
        nonlocal collapsed
        full = m.group(0)
        unit = m.group(1)
        # Rough count: total matched length / unit length
        times = max(1, len(full) // max(len(unit), 1))
        collapsed += times
        return f"{unit.rstrip()} [truncated {times}x repetition]"

    cleaned = pattern.sub(_replace, text)
    return cleaned, collapsed


def _log_truncation_if_any(llm_response: LlmResponse) -> None:
    """Emit a WARNING whenever the model signals a non-STOP finish reason.

    Critical for catching silent truncations at ``max_output_tokens`` and
    safety-filter aborts.  Kept defensive — must never raise.
    """
    try:
        candidates = getattr(llm_response, "candidates", None) or []
        for idx, c in enumerate(candidates):
            fr = getattr(c, "finish_reason", None)
            if fr is None:
                continue
            fr_name = getattr(fr, "name", None) or str(fr)
            if fr_name and fr_name not in _HEALTHY_FINISH_REASONS:
                logger.warning(
                    "Model response incomplete: finish_reason=%s candidate=%d"
                    " (possible max_output_tokens hit or safety abort)",
                    fr_name, idx,
                )
    except Exception:
        pass  # Monitoring must never break the agent.


def after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Sanitize model responses before they reach the user.

    Strips internal agent/tool names from user-facing text to prevent
    implementation details from leaking into the chat UI.  Also logs a
    WARNING if the model signaled a truncation/abort via finish_reason —
    gives us an early signal before users report missing data.
    """
    _log_truncation_if_any(llm_response)

    # Query-level telemetry — detect final text response (no function_calls)
    # and log QUERY_END with total duration and tool count.
    try:
        has_fc = False
        if llm_response.content and hasattr(llm_response.content, "parts"):
            has_fc = any(
                getattr(p, "function_call", None)
                for p in llm_response.content.parts
            )
        if not has_fc:
            tid = threading.get_ident()
            with _query_tracking_lock:
                tracking = _query_tracking.pop(tid, None)
            if tracking:
                qid, q_start, tool_count = tracking
                total_s = time.time() - q_start
                logger.info(
                    "QUERY_END query_id=%s total_duration=%.1fs tool_count=%d",
                    qid, total_s, tool_count,
                )
                if total_s > 120:
                    logger.warning(
                        "SLOW_QUERY query_id=%s took %.1fs (>120s threshold) "
                        "with %d tool calls",
                        qid, total_s, tool_count,
                    )
            # Clean up first-tool-logged for this thread so next query gets fresh tracking
            with _first_tool_logged_lock:
                _first_tool_logged.discard(tid)
    except Exception:
        pass

    # MALFORMED_FUNCTION_CALL fallback — if multi_region_model retries were
    # exhausted and the response still has error_code=MALFORMED_FUNCTION_CALL
    # with null content, inject a user-friendly text response so ADK doesn't
    # terminate the loop with {"content": null}.
    if not llm_response.content and llm_response.error_code:
        err_str = (
            getattr(llm_response.error_code, "name", None)
            or str(llm_response.error_code)
        )
        if err_str == "MALFORMED_FUNCTION_CALL":
            logger.warning(
                "after_model_callback: intercepted MALFORMED_FUNCTION_CALL "
                "after model retries exhausted — injecting corrective response"
            )
            return LlmResponse(
                content=genai_types.Content(
                    role="model",
                    parts=[genai_types.Part(
                        text=(
                            "I encountered a temporary processing error while "
                            "preparing the analysis. Please try your request "
                            "again — the issue is intermittent and typically "
                            "resolves on retry."
                        ),
                    )],
                ),
            )

    # Empty-response recovery (ADK issue #3754) — SSE streaming sometimes
    # drops the final text after AgentTool calls complete, leaving the user
    # with a blank chat bubble despite a successful execution.  Detect and
    # inject a nudge so the model re-presents results already in context.
    if (
        llm_response.content
        and hasattr(llm_response.content, "parts")
        and llm_response.content.parts
        and not llm_response.error_code
    ):
        parts = llm_response.content.parts
        has_func_call = any(
            getattr(p, "function_call", None) for p in parts
        )
        has_func_response = any(
            getattr(p, "function_response", None) for p in parts
        )
        has_text = any(
            getattr(p, "text", None)
            and getattr(p, "text", "").strip()
            for p in parts
        )
        if not has_func_call and not has_func_response and not has_text:
            logger.warning(
                "after_model_callback: empty text response detected with "
                "no function calls — likely ADK SSE streaming drop "
                "(issue #3754). Injecting recovery text."
            )
            return LlmResponse(
                content=genai_types.Content(
                    role="model",
                    parts=[genai_types.Part(
                        text=(
                            "The analysis completed successfully but the "
                            "response failed to render. Please reply with "
                            "**'show results'** to display the findings — "
                            "this will not re-run the analysis."
                        ),
                    )],
                ),
            )

    try:
        if llm_response.content and hasattr(llm_response.content, "parts"):
            sanitized_any = False
            collapsed_any = 0
            for part in llm_response.content.parts:
                if hasattr(part, "text") and part.text:
                    new_text = sanitize_response_text(part.text)
                    if new_text != part.text:
                        sanitized_any = True
                    # Runaway-repetition safety net — collapse degenerate
                    # attention loops before they reach the user.
                    new_text, collapsed = _collapse_runaway_repetition(new_text)
                    if collapsed:
                        collapsed_any += collapsed
                    if new_text != part.text:
                        part.text = new_text
            if sanitized_any:
                logger.info("after_model_callback: sanitized internal names from response")
            if collapsed_any:
                logger.warning(
                    "after_model_callback: collapsed %d runaway-repetition "
                    "instance(s) from model response (attention-loop "
                    "pathology — check context for repeated error traces)",
                    collapsed_any,
                )
    except Exception as e:
        logger.error("after_model_callback error: %s", e)

    return None  # Return None to accept the (possibly modified) response


###########################################
######### ROOT AGENT DEFINITION ###########
###########################################
all_tools = []
if mcp_toolset:
    all_tools.append(mcp_toolset)
if genai_mcp_tools:
    all_tools.extend(genai_mcp_tools)
all_tools.extend([retriever_tool, reconciliation_tool, comparison_tool, recommendation_tool])

root_agent = Agent(
    name="contract_intelligence_agent",
    # Multi-region wrapper: round-robins generate_content across US regions
    # and retries 429 RESOURCE_EXHAUSTED with exponential backoff.
    model=MultiRegionRetryGemini(model="gemini-2.5-flash"),
    description=(
        "Contract Intelligence Agent specialized in comparing contract "
        "pricing vs invoice charges to identify savings opportunities."
    ),
    instruction=instruction,
    tools=all_tools,
    generate_content_config=genai_types.GenerateContentConfig(
        # 0.1 was triggering attention-collapse loops in the final markdown
        # assembly when identical error traces (e.g. tool-validation errors
        # from malformed function_calls, or 429 retry chatter) showed up in
        # the context.  0.2 is still highly deterministic for structured
        # reasoning but adds enough sampling noise to break degenerate
        # single-phrase repetition (observed 2026-04-23: a table cell
        # filled with 200+ copies of a validator error).
        temperature=0.2,
        # Cap output to avoid runaway completions dragging wall-clock time.
        # Root needs headroom for: sequential function_call JSON (comparison
        # then recommendation with embedded retriever findings inline) AND
        # the final user-facing response.  16k is safe; the 4k previous cap
        # was truncating multi-supplier reports.
        max_output_tokens=16384,
        # Root is an orchestrator — it routes to sub-agents and emits
        # function_calls, not deep reasoning.  256 tokens is enough for
        # tool-selection logic while saving ~10s inference per turn vs 1024.
        thinking_config=genai_types.ThinkingConfig(thinking_budget=256),
    ),
    before_model_callback=rate_limit_before_model_callback,
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
    after_model_callback=after_model_callback,
)
logger.info(
    "Root agent defined with %d tools (direct MCP: %s, GenAI: %d, sub-agents: 4)",
    len(all_tools),
    bool(mcp_toolset),
    len(genai_mcp_tools),
)


###########################################
######### VERTEX AI INITIALIZATION ########
###########################################
_gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
_gcp_location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
vertexai.init(project=_gcp_project, location=_gcp_location, api_transport="rest")
logger.info(
    "Vertex AI initialized: project=%s, location=%s",
    _gcp_project,
    _gcp_location,
)

###########################################
######### ADK APP WRAPPER #################
###########################################
adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
)
logger.info("Contract Intelligence Agent initialization complete")

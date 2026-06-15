"""Shared deduplication cache for CIA root agent and sub-agents.

Prevents identical tool calls (rag_search, rag_search_batch, sub-agent
delegations) from executing multiple times within the same session.

The cache is module-level and shared across all agents in the same process,
so when the retriever agent calls rag_search("pricing for Medline") and
then the recommendation agent calls the same query, the second call is
served from cache instead of hitting the RAG API again.
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from typing import Any, Optional

logger = logging.getLogger("cia.dedup_cache")

# ─── Dedup-eligible tools ────────────────────────────────────────────────────
# Sub-agent delegations (root agent level only)
_SUB_AGENT_TOOLS = frozenset([
    "cia_retriever_agent",
    "cia_reconciliation_agent",
    "contract_comparison_agent",
    "cia_recommendation_agent",
])

# RAG tools used by root agent AND sub-agents (retriever, recommendation).
_RAG_TOOLS = frozenset([
    "rag_search",
    "rag_search_batch",
])

DEDUP_TOOLS: frozenset[str] = _SUB_AGENT_TOOLS | _RAG_TOOLS

# ─── Cache storage ──────────────────────────────────────────────────────────
_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()
_CACHE_TTL_S = 600  # 10 minutes — covers a single user session


def _clean_cache() -> None:
    """Remove entries older than TTL. Must be called inside ``_cache_lock``."""
    now = time.time()
    stale = [k for k, v in _cache.items()
             if now - v.get("_cached_at", 0) > _CACHE_TTL_S]
    for k in stale:
        del _cache[k]
    if stale:
        logger.debug("Dedup cache cleanup: removed %d stale entries", len(stale))


def _get_session_scope(tool_context: Any) -> str:
    """Extract a session-scoped identifier from the ADK ToolContext.

    Prefer session_id so cached results persist across turns within the
    same session, preventing re-execution when the LLM replays earlier
    queries from conversation history.
    """
    for attr in ("session_id", "invocation_id"):
        val = getattr(tool_context, attr, None)
        if val:
            return str(val)
    return str(threading.get_ident())


def _cache_key(tool_name: str, args: dict[str, Any], tool_context: Any = None) -> str:
    """Build a session-scoped cache key.

    Handles the three arg-key patterns used across CIA tools:
      - ``request`` (sub-agent delegations)
      - ``query``   (rag_search)
      - ``queries`` (rag_search_batch)
    Normalises to lowercase + collapsed whitespace so cosmetically
    different prompts map to the same entry.
    """
    scope = _get_session_scope(tool_context) if tool_context else str(threading.get_ident())
    raw_request = str(
        args.get("request", "")
        or args.get("query", "")
        or args.get("queries", "")
    )
    request_text = " ".join(raw_request.lower().split())
    request_hash = hashlib.md5(request_text.encode()).hexdigest()[:12]
    return f"{scope}:{tool_name}:{request_hash}"


# ─── Public API ──────────────────────────────────────────────────────────────
def check_cache(
    tool_name: str,
    args: dict[str, Any],
    tool_context: Any = None,
) -> Optional[dict]:
    """Return a cached result for ``tool_name(args)``, or ``None``.

    Call this in ``before_tool_callback``.  If a non-None dict is returned,
    short-circuit the tool call by returning it directly.
    """
    if tool_name not in DEDUP_TOOLS:
        return None
    key = _cache_key(tool_name, args, tool_context)
    with _cache_lock:
        _clean_cache()
        cached = _cache.get(key)
    if cached is not None:
        logger.warning(
            "BLOCKED duplicate tool call: %s (returning cached result)",
            tool_name,
        )
        return cached
    return None


def store_result(
    tool_name: str,
    args: dict[str, Any],
    tool_response: Any,
    tool_context: Any = None,
) -> None:
    """Cache a tool result for future dedup checks.

    Call this in ``after_tool_callback``.
    """
    if tool_name not in DEDUP_TOOLS:
        return
    key = _cache_key(tool_name, args, tool_context)
    result = (
        tool_response
        if isinstance(tool_response, dict)
        else {"result": str(tool_response)}
    )
    result["_cached_at"] = time.time()
    with _cache_lock:
        _cache[key] = result
    logger.info("Cached tool result for dedup: %s", tool_name)

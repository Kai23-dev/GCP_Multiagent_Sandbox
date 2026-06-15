"""Shared utilities for the Contract Intelligence Agent (CIA) sub-agents.

Provides centralized authentication, MCP toolset creation, GenAI Toolbox
client management, and Gemini API rate limiting to eliminate code duplication
across agent modules.
"""
from __future__ import annotations

import atexit
import base64
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from typing import Optional

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.auth.exceptions import DefaultCredentialsError
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from toolbox_core import ToolboxSyncClient

logger = logging.getLogger("cia.utils")


# ─── Instruction Fragment Loader ─────────────────────────────────────────────
def load_instruction_fragment(filename: str, required: bool = False) -> str:
    """Load a shared instruction fragment from the instruction/ directory.

    Used by sub-agents to embed shared rules (e.g., sql_rules.md) into their
    instruction strings at import time, eliminating copy-paste duplication.

    Args:
        filename: Name of the file in the instruction/ directory.
        required: If True, raise FileNotFoundError when the file is missing
                  and log at ERROR level. Critical fragments (e.g., sql_rules.md)
                  should set this to True.
    """
    path = os.path.join(os.path.dirname(__file__), "instruction", filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                msg = "Instruction fragment is empty: %s"
                if required:
                    logger.error(msg, path)
                    raise ValueError(f"Required instruction fragment is empty: {path}")
                logger.warning(msg, path)
                return ""
            logger.debug("Loaded instruction fragment: %s (%d chars)", filename, len(content))
            return content
    except FileNotFoundError:
        msg = "Instruction fragment not found: %s"
        if required:
            logger.error(msg, path)
            raise
        logger.warning(msg, path)
        return ""


# ─── Environment Variables ───────────────────────────────────────────────────
_mcp_base_url = os.environ.get("MCP_URL")
MCP_URL = f"{_mcp_base_url.rstrip('/')}/mcp" if _mcp_base_url else ""
GENAI_MCP_URL = os.environ.get("GENAI_MCP_URL") or ""
TOOLBOX_BQ_PROJECT_ID = os.environ.get("SCO_KB_PROJECT_ID") or ""
TOOLBOX_BQ_DATASET_IDS = ["ai_financial_dlp", "sco_rage_invoice_extract_ds"]

logger.info(
    "CIA Utils loaded: MCP_URL=%s, GENAI_MCP_URL=%s, BQ_PROJECT=%s",
    MCP_URL[:50] + "..." if len(MCP_URL) > 50 else MCP_URL or "(not set)",
    GENAI_MCP_URL[:50] + "..." if len(GENAI_MCP_URL) > 50 else GENAI_MCP_URL or "(not set)",
    TOOLBOX_BQ_PROJECT_ID or "(not set)",
)


# ─── Authentication ──────────────────────────────────────────────────────────────────────────

# Token cache: {audience: (token_str, expiry_timestamp)}
_TOKEN_CACHE: dict[str, tuple[str, float]] = {}
# Refresh tokens 5 minutes before expiry
_TOKEN_REFRESH_MARGIN_SECONDS = 300


def _extract_token_expiry(token: str) -> float:
    """Extract expiry timestamp from a JWT token. Returns 0 on failure."""
    try:
        parts = token.split(".")
        if len(parts) == 3:
            payload_b64 = parts[1] + ("=" * (-len(parts[1]) % 4))
            payload = json.loads(
                base64.urlsafe_b64decode(payload_b64).decode("utf-8")
            )
            return float(payload.get("exp", 0))
    except Exception:
        pass
    return 0


def _fetch_token_uncached(audience: str) -> str:
    """Fetch a fresh ID token (no cache). Tries ADC first, then gcloud CLI."""
    # 1. Try Application Default Credentials (fast — ~100ms)
    try:
        request = Request()
        fetched_token = id_token.fetch_id_token(request, audience)
        logger.debug("ID token obtained via application default credentials")

        # If near expiry on ADC, try metadata server refresh
        exp = _extract_token_expiry(fetched_token)
        if exp and exp - time.time() <= _TOKEN_REFRESH_MARGIN_SECONDS:
            logger.info("ADC token expiring soon, refreshing from metadata server")
            try:
                import requests as _requests

                metadata_url = (
                    "http://metadata.google.internal/computeMetadata/v1/"
                    "instance/service-accounts/default/identity"
                )
                params = {"audience": audience}
                headers = {"Metadata-Flavor": "Google"}
                response = _requests.get(
                    metadata_url, params=params, headers=headers, timeout=5
                )
                if response.ok and response.text.strip():
                    fetched_token = response.text.strip()
            except Exception:
                pass

        return fetched_token

    except DefaultCredentialsError:
        pass

    # 2. Fallback: gcloud CLI (slow — ~3-4s on Windows, ~15s with credential lookup)
    logger.warning("No default credentials found, falling back to gcloud CLI")
    try:
        if sys.platform == "win32":
            cmd = "gcloud auth print-identity-token"
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, shell=True,
                timeout=30,
            )
        else:
            result = subprocess.run(
                ["gcloud", "auth", "print-identity-token"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )

        if result.returncode != 0:
            logger.error(
                "Failed to obtain ID token via gcloud: %s", result.stderr.strip()
            )
            return ""

        token = result.stdout.strip()
        if token:
            logger.debug("ID token obtained via gcloud CLI")
            return token
    except subprocess.TimeoutExpired:
        logger.error("gcloud CLI timed out after 30s")
    except Exception as e:
        logger.error("Unexpected error in gcloud CLI fallback: %s", str(e))

    return ""


def get_id_token(audience: str) -> str:
    """Get Google Cloud ID token with caching.

    Tokens are cached per audience and reused until 5 minutes before expiry.
    This avoids spawning a gcloud CLI subprocess (~15s) on every tool call.
    """
    now = time.time()

    # Check cache
    cached = _TOKEN_CACHE.get(audience)
    if cached:
        token, expiry = cached
        remaining = expiry - now
        if remaining > _TOKEN_REFRESH_MARGIN_SECONDS:
            logger.debug(
                "Using cached token for %s (expires in %.0fs)",
                audience[:40] + "...",
                remaining,
            )
            return token
        else:
            logger.info(
                "Cached token for %s expiring in %.0fs, refreshing",
                audience[:40] + "...",
                remaining,
            )

    # Fetch fresh token
    token = _fetch_token_uncached(audience)
    if token:
        expiry = _extract_token_expiry(token)
        if expiry > 0:
            _TOKEN_CACHE[audience] = (token, expiry)
            logger.info(
                "Token cached for %s (valid for %.0fs)",
                audience[:40] + "...",
                expiry - now,
            )
        else:
            # Can't parse expiry — cache for 45 minutes as safe default
            _TOKEN_CACHE[audience] = (token, now + 2700)
            logger.info(
                "Token cached for %s (default 45min TTL, expiry unknown)",
                audience[:40] + "...",
            )
    else:
        logger.error("Failed to obtain ID token for audience: %s", audience[:50])

    return token


# ─── MCP Toolset (RAG) ───────────────────────────────────────────────────────
_mcp_toolset: MCPToolset | None = None
_mcp_toolset_created_at: float = 0
_MCP_TOOLSET_TTL_SECONDS = 3600  # Recreate after 1 hour to pick up config changes

# Circuit breaker: stop retrying MCP creation after repeated failures
_mcp_creation_failures: int = 0
_mcp_last_failure_time: float = 0
_MCP_MAX_FAILURES = 3
_MCP_FAILURE_COOLDOWN_SECONDS = 300  # 5 minutes before retrying after max failures


def get_mcp_toolset(force_recreate: bool = False) -> MCPToolset | None:
    """Return the shared MCP toolset for RAG tools.

    Creates the toolset on first call; subsequent calls return the cached
    instance. The toolset is automatically recreated after TTL expires
    (default 1 hour) to recover from stale connections or config changes.

    Includes a circuit breaker: after _MCP_MAX_FAILURES consecutive creation
    failures, stops retrying for _MCP_FAILURE_COOLDOWN_SECONDS (returns the
    stale toolset if one exists, or None).
    """
    global _mcp_toolset, _mcp_toolset_created_at
    global _mcp_creation_failures, _mcp_last_failure_time

    if force_recreate:
        logger.info("Force-recreating MCP toolset")
        _mcp_toolset = None
        _mcp_creation_failures = 0  # Reset circuit breaker on explicit force

    if _mcp_toolset is not None:
        elapsed = time.time() - _mcp_toolset_created_at
        if elapsed < _MCP_TOOLSET_TTL_SECONDS:
            return _mcp_toolset
        logger.info(
            "MCP toolset TTL expired (%.0fs > %ds), recreating",
            elapsed,
            _MCP_TOOLSET_TTL_SECONDS,
        )
        # Don't set _mcp_toolset = None here — keep serving the old one
        # until the new one is ready (atomic swap below)

    if not MCP_URL:
        logger.warning("MCP_URL not configured — RAG tools unavailable")
        return None

    # Circuit breaker: stop retrying after repeated failures
    if _mcp_creation_failures >= _MCP_MAX_FAILURES:
        elapsed_since_failure = time.time() - _mcp_last_failure_time
        if elapsed_since_failure < _MCP_FAILURE_COOLDOWN_SECONDS:
            logger.warning(
                "MCP toolset circuit breaker OPEN (%d consecutive failures, "
                "%.0fs cooldown remaining). Returning stale toolset if available.",
                _mcp_creation_failures,
                _MCP_FAILURE_COOLDOWN_SECONDS - elapsed_since_failure,
            )
            return _mcp_toolset  # May be stale or None
        else:
            logger.info(
                "MCP toolset circuit breaker reset after %.0fs cooldown",
                elapsed_since_failure,
            )
            _mcp_creation_failures = 0

    logger.info("Creating shared MCP toolset for RAG")
    http_params = StreamableHTTPConnectionParams(
        url=MCP_URL,
        headers={},
        timeout=120.0,
        sse_read_timeout=600.0,
    )

    def _mcp_header_provider(_readonly_context) -> dict[str, str]:
        logger.debug("MCP header provider invoked for audience: %s", _mcp_base_url)
        token = get_id_token(_mcp_base_url)
        if not token:
            logger.error(
                "MCP auth token NOT available — requests will fail with 403"
            )
        return {"Authorization": f"Bearer {token}"} if token else {}

    # Atomic swap: create new toolset first, then replace the old one.
    # This prevents concurrent requests from seeing a None toolset during recreation.
    old_toolset = _mcp_toolset
    try:
        new_toolset = MCPToolset(
            connection_params=http_params,
            header_provider=_mcp_header_provider,
        )
        # Prevent the ADK sub-agent runner from closing the shared MCP
        # session.  When a sub-agent (e.g. cia_retriever_agent) finishes,
        # the Runner calls toolset.close() on every tool — including this
        # shared singleton.  That kills the MCP connection for the root
        # agent and all other sub-agents, causing the session to hang.
        # We manage the lifecycle ourselves (TTL + circuit breaker), so
        # close() should be a no-op for the framework.
        new_toolset._real_close = new_toolset.close
        async def _noop_close():
            logger.debug("MCPToolset.close() suppressed (lifecycle managed by utils.py)")
        new_toolset.close = _noop_close
        _mcp_toolset = new_toolset
        _mcp_toolset_created_at = time.time()
        _mcp_creation_failures = 0  # Reset on success
        logger.info("Shared MCP toolset created (TTL: %ds)", _MCP_TOOLSET_TTL_SECONDS)
    except RuntimeError as e:
        if "cancel scope" in str(e).lower():
            logger.warning(
                "MCP toolset creation raised cross-task cancel scope "
                "RuntimeError (suppressed — stale toolset will be reused): %s", e,
            )
        else:
            _mcp_creation_failures += 1
            _mcp_last_failure_time = time.time()
            logger.error(
                "MCP toolset creation failed (%d/%d): %s",
                _mcp_creation_failures, _MCP_MAX_FAILURES, str(e),
            )
            if _mcp_creation_failures >= _MCP_MAX_FAILURES:
                logger.critical(
                    "MCP toolset circuit breaker TRIPPED — "
                    "RAG tools will be unavailable for %ds",
                    _MCP_FAILURE_COOLDOWN_SECONDS,
                )
    except Exception as e:
        _mcp_creation_failures += 1
        _mcp_last_failure_time = time.time()
        logger.error(
            "MCP toolset creation failed (%d/%d): %s",
            _mcp_creation_failures,
            _MCP_MAX_FAILURES,
            str(e),
        )
        if _mcp_creation_failures >= _MCP_MAX_FAILURES:
            logger.critical(
                "MCP toolset circuit breaker TRIPPED — "
                "RAG tools will be unavailable for %ds",
                _MCP_FAILURE_COOLDOWN_SECONDS,
            )

    # Clean up old toolset — call the REAL close (bypassing our no-op
    # override) and suppress cancel scope errors that occur when the MCP
    # session is closed from a different async task than it was opened in.
    if old_toolset is not None and old_toolset is not _mcp_toolset:
        _real = getattr(old_toolset, "_real_close", None) or getattr(old_toolset, "close", None)
        if _real:
            try:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_real())
                except RuntimeError:
                    pass
            except RuntimeError as e:
                if "cancel scope" in str(e).lower():
                    logger.warning(
                        "Old MCP toolset close raised cancel scope error "
                        "(suppressed): %s", e,
                    )
                else:
                    logger.warning("Old MCP toolset close error: %s", e)
            except Exception as e:
                logger.warning("Old MCP toolset cleanup error (suppressed): %s", e)

    return _mcp_toolset


# ─── GenAI Toolbox (BigQuery) ─────────────────────────────────────────────────
_toolbox_client: ToolboxSyncClient | None = None
_genai_tools_cache: dict[str, list] = {}


def _get_toolbox_client() -> ToolboxSyncClient | None:
    """Return (or create) the shared GenAI Toolbox client."""
    global _toolbox_client
    if _toolbox_client is not None:
        return _toolbox_client

    if not GENAI_MCP_URL:
        logger.warning("GENAI_MCP_URL not configured — BigQuery tools unavailable")
        return None

    _genai_base_url = GENAI_MCP_URL.rstrip("/").split("/mcp")[0]
    logger.info(
        "Creating shared GenAI Toolbox client (audience: %s)", _genai_base_url
    )

    def _auth_header() -> str:
        token = get_id_token(_genai_base_url)
        if not token:
            logger.error(
                "GenAI Toolbox auth token NOT available — requests will fail with 403"
            )
        return f"Bearer {token}" if token else ""

    _toolbox_client = ToolboxSyncClient(
        GENAI_MCP_URL,
        client_headers={"Authorization": _auth_header},
    )

    # Register cleanup handlers
    atexit.register(_toolbox_client.close)
    try:
        def _shutdown_handler(_signum, _frame):
            try:
                _toolbox_client.close()
            except Exception:
                pass

        signal.signal(signal.SIGTERM, _shutdown_handler)
        signal.signal(signal.SIGINT, _shutdown_handler)
    except Exception:
        pass

    logger.info("Shared GenAI Toolbox client created")
    return _toolbox_client


# Expected tools per toolset — used for partial failure detection
_EXPECTED_TOOLS: dict[str, set[str]] = {
    "ssi-toolset": {
        "ssi_execute_sql",
        "ssi_get_supplier_invoices",
        "ssi_get_supplier_invoices_paginated",
        "ssi_get_supplier_invoice_count",
        "ssi_get_invoice_pricing",
        "ssi_get_invoice_pricing_paginated",
        "ssi_get_contract_linked_invoices",
        "ssi_get_contract_linked_invoices_paginated",
        "ssi_get_supplier_spend",
        "ssi_get_catalog_prices",
        "ssi_get_po_prices",
        "ssi_get_contract_dates",
        "ssi_find_suppliers_without_contracts",
    },
}


def get_genai_tools(toolset_name: str = "ssi-toolset") -> list:
    """Load and return GenAI Toolbox tools for the given toolset.

    Results are cached per toolset name.  Tools are automatically bound
    to the BigQuery project ID when configured. Logs warnings when
    expected tools are missing (partial failure detection).
    """
    if toolset_name in _genai_tools_cache:
        return list(_genai_tools_cache[toolset_name])

    client = _get_toolbox_client()
    if client is None:
        return []

    try:
        loaded = client.load_toolset(toolset_name)
        tools = loaded if isinstance(loaded, list) else [loaded]
        if TOOLBOX_BQ_PROJECT_ID:
            try:
                tools = [
                    t.bind_params({"project_id": TOOLBOX_BQ_PROJECT_ID})
                    for t in tools
                ]
            except Exception:
                pass
        tool_names = {
            getattr(t, "__name__", None) or getattr(t, "_name", None) or str(t)
            for t in tools
        }
        logger.info(
            "GenAI Toolbox loaded %d tools for '%s': %s",
            len(tools),
            toolset_name,
            ", ".join(sorted(tool_names)),
        )

        # Partial failure detection: check if expected tools are present
        expected = _EXPECTED_TOOLS.get(toolset_name)
        if expected:
            missing = expected - tool_names
            if missing:
                logger.error(
                    "PARTIAL FAILURE: %d expected tools MISSING from '%s': %s. "
                    "Agent may not function correctly.",
                    len(missing),
                    toolset_name,
                    ", ".join(sorted(missing)),
                )

        _genai_tools_cache[toolset_name] = tools
        return list(tools)
    except Exception as e:
        logger.error(
            "Failed to load GenAI Toolbox toolset '%s': %s", toolset_name, str(e)
        )
        return []


# ─── Gemini API Rate Limiter (async) ────────────────────────────────────────
# Prevents 429 RESOURCE_EXHAUSTED errors caused by burst patterns in the
# multi-agent architecture.  All agents share a single global instance so
# the limit applies to the aggregate call rate across root + sub-agents.
#
# IMPORTANT: this limiter is fully async — it uses asyncio.Lock and
# asyncio.sleep so that throttling does NOT block the ADK event loop.
# The previous sync implementation (threading.Lock + time.sleep) stalled
# the whole worker during bursts, amplifying perceived latency and
# starving other in-flight requests.
import asyncio


class AsyncGeminiRateLimiter:
    """Async sliding-window rate limiter for Gemini ``generate_content``.

    Keeps per-process sliding window of call timestamps.  When the window
    is full, ``await acquire()`` sleeps (via ``asyncio.sleep``) until a
    slot opens — never blocking the event loop.
    """

    def __init__(self, max_calls: int = 15, window_seconds: float = 60.0):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._call_times: deque[float] = deque()
        # asyncio.Lock is created lazily so the module can be imported
        # before any event loop exists (matters for ADK agent engine
        # cold-start where import happens before loop creation).
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def acquire(self) -> float:
        """Await a rate-limit slot. Returns total seconds waited."""
        total_waited = 0.0
        lock = self._get_lock()

        # Loop in case multiple tasks race on the same slot after sleep.
        while True:
            async with lock:
                now = time.time()
                cutoff = now - self.window_seconds
                while self._call_times and self._call_times[0] < cutoff:
                    self._call_times.popleft()

                if len(self._call_times) < self.max_calls:
                    self._call_times.append(now)
                    return total_waited

                oldest = self._call_times[0]
                wait_time = (oldest + self.window_seconds) - now + 0.05

            if wait_time > 0:
                logger.info(
                    "Rate limiter: throttling %.2fs (%d/%d calls in %.0fs window)",
                    wait_time, self.max_calls, self.max_calls, self.window_seconds,
                )
                await asyncio.sleep(wait_time)
                total_waited += wait_time


_RATE_LIMIT_MAX_CALLS = int(os.environ.get("GEMINI_RATE_LIMIT_MAX_CALLS", "15"))
_RATE_LIMIT_WINDOW_S = float(os.environ.get("GEMINI_RATE_LIMIT_WINDOW_S", "60"))

gemini_rate_limiter = AsyncGeminiRateLimiter(
    max_calls=_RATE_LIMIT_MAX_CALLS,
    window_seconds=_RATE_LIMIT_WINDOW_S,
)
logger.info(
    "Gemini rate limiter initialized (async): %d calls per %.0fs window",
    _RATE_LIMIT_MAX_CALLS, _RATE_LIMIT_WINDOW_S,
)


async def rate_limit_before_model_callback(
    callback_context,  # CallbackContext
    llm_request,       # LlmRequest
) -> Optional[None]:
    """Async before_model_callback that enforces rate limiting.

    Shared by root agent and all sub-agents via the global
    ``gemini_rate_limiter`` singleton.  Returns ``None`` so ADK lets the
    model call proceed after any throttling.  Being ``async``, this
    coroutine yields to the event loop during waits, allowing other
    in-flight requests to make progress.
    """
    waited = await gemini_rate_limiter.acquire()
    if waited > 0:
        logger.info("Rate limiter delayed model call by %.2fs", waited)
    return None

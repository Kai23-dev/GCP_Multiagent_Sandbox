"""Multi-region Gemini model wrapper with 429 retry + regional load balancing.

Problem
-------
`gemini-2.5-flash` has a per-region shared quota (60 RPM in us-central1).
The CIA root agent + 4 sub-agents all call the same model in the same region,
so a single user session can burst past 60 RPM → 429 RESOURCE_EXHAUSTED.

Solution
--------
Round-robin every `generate_content_async` call across a pool of US regions.
Each region has its own independent quota bucket, so aggregate throughput
becomes ``60 * N_regions`` RPM at zero cost (no quota ticket, no PT purchase).

On 429 we retry with exponential backoff + jitter, preferring a *different*
region on each retry so transient hot-spots in one region don't stall the
whole request.

Design notes
------------
- Concurrency-safe via ``contextvars.ContextVar`` — the per-call client
  override is bound to the asyncio Task, not the model instance, so
  concurrent invocations do not stomp on each other.
- Zero behavioural change when only one region is configured (list-of-one)
  — the wrapper simply adds retry/backoff on top of the stock ADK model.
- No dependency on Provisioned Throughput headers.  Works on any Vertex
  project that has the default 60 RPM shared quota in each listed region.
- Regions list and retry budget are env-tunable so ops can adjust without
  a code redeploy.

Usage
-----
    from .multi_region_model import MultiRegionRetryGemini
    model = MultiRegionRetryGemini(model="gemini-2.5-flash")
    agent = Agent(name="...", model=model, ...)
"""
from __future__ import annotations

import asyncio
import itertools
import logging
import os
import random
import threading
import time
from contextvars import ContextVar
from typing import Any, Optional

from google.adk.models.google_llm import Gemini
from google.genai import Client
from google.genai.errors import ClientError

logger = logging.getLogger("cia.multi_region_model")


# ─── Configuration ───────────────────────────────────────────────────────────
# Vertex AI regions that host `gemini-2.5-flash` (US multi-region set).
# Each region has its own independent 60 RPM shared quota bucket.
# Data-residency: all listed regions are in the US multi-region; confirm
# compliance before adding non-US regions.
_DEFAULT_US_REGIONS = (
    "us-central1",
    "us-east4",
    "us-east5",
    "us-south1",
    "us-west1",
    "us-west4",
)


def _parse_regions(raw: str) -> tuple[str, ...]:
    parts = [r.strip() for r in raw.split(",") if r.strip()]
    return tuple(parts) if parts else _DEFAULT_US_REGIONS


_REGIONS: tuple[str, ...] = _parse_regions(
    os.environ.get("GEMINI_US_REGIONS", ",".join(_DEFAULT_US_REGIONS))
)
# Retry budget sized to cover the full region pool at least TWICE:
# - 6 US regions × 2 passes = 12 attempts
# - First pass uses short backoffs (0.3 → 4s) to ride through isolated
#   region hot-spots.
# - When every region has 429'd at least once, the project's per-minute
#   quota is globally exhausted — we force one 30s "RPM recovery" sleep
#   (see _FULL_POOL_WAIT_S) before starting the second pass.
# - Second-pass backoffs ramp higher (up to 30s) so we don't hammer the
#   quota window while it's still refilling.
_MAX_RETRIES: int = int(os.environ.get("GEMINI_429_MAX_RETRIES", "12"))
_BASE_BACKOFF_S: float = float(os.environ.get("GEMINI_429_BASE_BACKOFF_S", "0.3"))
_MAX_BACKOFF_S: float = float(os.environ.get("GEMINI_429_MAX_BACKOFF_S", "30.0"))
# Sleep once when the entire region pool has 429'd in rapid succession.
# Gemini per-minute quotas refresh on a 60s window, so a 30s wait gives the
# quota bucket ~50% headroom to refill before we start retrying.
_FULL_POOL_WAIT_S: float = float(os.environ.get("GEMINI_429_POOL_EXHAUSTED_WAIT_S", "30.0"))
_PROJECT: str = os.environ.get("GOOGLE_CLOUD_PROJECT", "")

# Backup model tried INSTANTLY when the primary model returns 429 on a given
# region.  A different publisher model has an independent quota bucket, so
# when `gemini-2.5-flash` is saturated, `gemini-2.5-flash-lite` is usually
# wide open.  Probed viable in this project (2026-04-23):
#   - gemini-2.5-flash        (primary, 6.9s cold call)
#   - gemini-2.5-flash-lite   (backup,  0.6s cold call, separate quota)
#   - gemini-2.5-pro          (viable but expensive — not used by default)
# Set to empty string to disable the backup and keep region-only failover.
_BACKUP_MODEL: str = os.environ.get("GEMINI_BACKUP_MODEL", "gemini-2.5-flash-lite")

# MALFORMED_FUNCTION_CALL retry budget.  The model occasionally generates
# function_call with wrong parameter names (e.g. passing supplier name as a
# key instead of using the "request" parameter).  Gemini's server-side schema
# validator rejects these with finish_reason=MALFORMED_FUNCTION_CALL and
# content=null.  ADK treats this as a terminal response (is_final_response()
# returns True) and the user sees {"content": null}.
# Retrying with the same temperature (0.2) usually produces a valid call on
# the second or third attempt because the model samples different token paths.
_MALFORMED_MAX_RETRIES: int = int(
    os.environ.get("GEMINI_MALFORMED_MAX_RETRIES", "2")
)
_MALFORMED_BACKOFF_S: float = 0.5


def _has_malformed_finish_reason(responses: list) -> bool:
    """Return True if any buffered response has MALFORMED_FUNCTION_CALL."""
    for resp in responses:
        for candidate in getattr(resp, "candidates", None) or []:
            fr = getattr(candidate, "finish_reason", None)
            if fr is not None:
                fr_str = getattr(fr, "name", None) or str(fr)
                if fr_str == "MALFORMED_FUNCTION_CALL":
                    return True
    return False


# ─── Per-region genai Client cache ───────────────────────────────────────────
# One `genai.Client` per region, created lazily, then reused for the life
# of the process.  Clients are thread-safe for concurrent use.
_clients: dict[str, Client] = {}
_clients_lock = threading.Lock()


def _get_client(region: str) -> Client:
    """Return a cached `genai.Client` pinned to ``region``."""
    client = _clients.get(region)
    if client is not None:
        return client
    with _clients_lock:
        client = _clients.get(region)
        if client is None:
            logger.info(
                "Creating genai.Client for region=%s project=%s",
                region,
                _PROJECT or "(from env)",
            )
            client = Client(
                vertexai=True,
                project=_PROJECT or None,
                location=region,
            )
            _clients[region] = client
    return client


# ─── Round-robin region selector ─────────────────────────────────────────────
# One process-wide cycle so that consecutive calls from *different* agents
# (root, retriever, reconciliation, …) naturally spread across regions.
_region_cycle = itertools.cycle(_REGIONS)
_region_cycle_lock = threading.Lock()


def _next_region(avoid: set[str]) -> Optional[str]:
    """Pick the next region, skipping any in ``avoid`` if possible."""
    with _region_cycle_lock:
        for _ in range(len(_REGIONS) * 2):
            region = next(_region_cycle)
            if region not in avoid:
                return region
        # All regions already tried — return None so the caller can bail.
    return None


# ─── ContextVar for per-call client override ────────────────────────────────
# Bound to the asyncio Task, so concurrent requests never interfere.
_CURRENT_CLIENT: ContextVar[Optional[Client]] = ContextVar(
    "cia_current_genai_client", default=None
)


# ─── Backup-model support ────────────────────────────────────────────────────
class _PinnedGemini(Gemini):
    """Gemini variant that honours ``_CURRENT_CLIENT`` but has NO retry logic.

    Used to invoke the backup model with the same region-pinned Vertex client
    as the primary attempt, without triggering a recursive retry loop.  If
    the backup itself 429s, the exception propagates up to the outer retry
    loop in :class:`MultiRegionRetryGemini` which then advances to the next
    region / backoff.
    """

    @property
    def api_client(self) -> Client:  # type: ignore[override]
        override = _CURRENT_CLIENT.get()
        if override is not None:
            return override
        return super().api_client  # type: ignore[misc]


_backup_instances: dict[str, _PinnedGemini] = {}
_backup_lock = threading.Lock()


def _get_backup_model(name: str) -> Optional[_PinnedGemini]:
    """Return a lazy-cached backup Gemini instance for ``name``.

    Returns None if ``name`` is empty (backup disabled).
    """
    if not name:
        return None
    inst = _backup_instances.get(name)
    if inst is not None:
        return inst
    with _backup_lock:
        inst = _backup_instances.get(name)
        if inst is None:
            logger.info("Instantiating backup Gemini model=%s", name)
            inst = _PinnedGemini(model=name)
            _backup_instances[name] = inst
    return inst


# ─── Model wrapper ──────────────────────────────────────────────────────────
class MultiRegionRetryGemini(Gemini):
    """Gemini subclass that round-robins regions and retries 429s.

    Overrides the private ``api_client`` property used by the parent class
    so that, when a ``ContextVar`` override is active, Vertex SDK calls
    are routed to the region-specific client picked for this invocation.
    Outside of the retry loop the override is ``None`` and the parent's
    default client is used — making this wrapper a safe drop-in even if
    something bypasses ``generate_content_async``.
    """

    # The parent Gemini class is a pydantic BaseModel.  Overriding a
    # *property* (class-level descriptor) is allowed without declaring
    # a new field.
    @property
    def api_client(self) -> Client:  # type: ignore[override]
        override = _CURRENT_CLIENT.get()
        if override is not None:
            return override
        # Fallback to the parent's default client (the original behaviour).
        return super().api_client  # type: ignore[misc]

    async def generate_content_async(self, llm_request, stream=False):
        """Route each call to a region, retry on 429, re-raise others."""
        attempt = 0
        delay = _BASE_BACKOFF_S
        tried: set[str] = set()
        full_pool_waits = 0  # how many times we've done the RPM-recovery sleep
        last_err: Optional[ClientError] = None

        while attempt < _MAX_RETRIES:
            # Have we already 429'd on every region in the pool?  If so, the
            # project's per-minute quota is globally exhausted — no region
            # will succeed until the 60s RPM window rolls forward.  Sleep
            # once, then start a fresh cycle with escalated backoffs.
            if len(tried) >= len(_REGIONS):
                full_pool_waits += 1
                logger.warning(
                    "All %d regions 429'd (pool exhausted, wait #%d) — "
                    "sleeping %.0fs for RPM quota window to refresh "
                    "before starting a fresh retry cycle",
                    len(_REGIONS), full_pool_waits, _FULL_POOL_WAIT_S,
                )
                await asyncio.sleep(_FULL_POOL_WAIT_S)
                tried.clear()
                delay = max(delay, 2.0)  # skip the fast-retry phase on pass 2+

            region = _next_region(tried)
            if region is None:
                # Defensive fallback — _next_region may return None if the
                # pool is tiny (e.g. list-of-one) and already tried.  Pick
                # anything rather than crash.
                region = _REGIONS[0]
            tried.add(region)

            client = _get_client(region)
            token = _CURRENT_CLIENT.set(client)
            retryable_429 = False
            try:
                # --- Primary model attempt ------------------------------------
                try:
                    if not stream and _MALFORMED_MAX_RETRIES > 0:
                        # Non-streaming: buffer the response so we can inspect
                        # finish_reason BEFORE yielding to ADK.  If the model
                        # generated a malformed function_call, retry silently.
                        buffered = None
                        for _mf_attempt in range(_MALFORMED_MAX_RETRIES + 1):
                            buffered = []
                            async for resp in super().generate_content_async(
                                llm_request, stream
                            ):
                                buffered.append(resp)
                            if not _has_malformed_finish_reason(buffered):
                                break
                            if _mf_attempt < _MALFORMED_MAX_RETRIES:
                                logger.warning(
                                    "MALFORMED_FUNCTION_CALL on region=%s "
                                    "(retry %d/%d) — model generated invalid "
                                    "function call params, retrying",
                                    region,
                                    _mf_attempt + 1,
                                    _MALFORMED_MAX_RETRIES,
                                )
                                await asyncio.sleep(_MALFORMED_BACKOFF_S)
                        for resp in buffered:
                            yield resp
                        return
                    else:
                        async for resp in super().generate_content_async(
                            llm_request, stream
                        ):
                            yield resp
                        return
                except ClientError as e:
                    # Non-429 errors propagate unchanged; only 429 triggers
                    # retry.  Partial yields before a 429 are not a concern
                    # here because ADK runs sub-agents with stream=False, so
                    # a 429 fires before any response is yielded.
                    if getattr(e, "code", None) != 429:
                        raise
                    last_err = e
                    primary_model = self.model

                # --- Backup model attempt (INSTANT, same region) --------------
                # Different publisher model = independent quota bucket, so
                # `gemini-2.5-flash-lite` is usually wide open when
                # `gemini-2.5-flash` is saturated.  No sleep, no region
                # change — just swap the model on the same pinned client.
                backup = _get_backup_model(_BACKUP_MODEL)
                if backup is not None and _BACKUP_MODEL != primary_model:
                    try:
                        logger.warning(
                            "Primary model=%s 429'd on region=%s — trying "
                            "backup model=%s INSTANTLY on same region",
                            primary_model, region, _BACKUP_MODEL,
                        )
                        _backup_start = time.time()
                        # Swap llm_request.model so the Vertex API
                        # call targets the backup model's quota bucket.
                        original_model = llm_request.model
                        llm_request.model = _BACKUP_MODEL
                        try:
                            async for resp in backup.generate_content_async(
                                llm_request, stream
                            ):
                                yield resp
                        finally:
                            llm_request.model = original_model
                        _backup_latency = time.time() - _backup_start
                        if _backup_latency > 20:
                            logger.warning(
                                "SLOW backup model=%s latency=%.1fs on "
                                "region=%s (>20s threshold)",
                                _BACKUP_MODEL, _backup_latency, region,
                            )
                        else:
                            logger.info(
                                "Backup model=%s succeeded on region=%s "
                                "latency=%.1fs",
                                _BACKUP_MODEL, _backup_latency, region,
                            )
                        return
                    except ClientError as e2:
                        if getattr(e2, "code", None) != 429:
                            raise
                        last_err = e2
                        logger.warning(
                            "Backup model=%s ALSO 429'd on region=%s — "
                            "falling through to region failover",
                            _BACKUP_MODEL, region,
                        )

                # Both primary and backup returned 429 on this region.
                retryable_429 = True
            finally:
                _CURRENT_CLIENT.reset(token)

            # 429 path — back off and loop to pick a different region.
            if retryable_429:
                attempt += 1
                wait = min(delay, _MAX_BACKOFF_S) + random.uniform(0, 0.5)
                logger.warning(
                    "429 RESOURCE_EXHAUSTED on region=%s (attempt %d/%d, "
                    "both primary+backup models) — retrying in %.1fs on a "
                    "different region",
                    region, attempt, _MAX_RETRIES, wait,
                )
                await asyncio.sleep(wait)
                delay = min(delay * 2, _MAX_BACKOFF_S)

        # All retries exhausted — surface the last 429 to the caller.
        logger.error(
            "429 RESOURCE_EXHAUSTED: exhausted %d retries across regions %s",
            _MAX_RETRIES, sorted(tried),
        )
        if last_err is not None:
            raise last_err


logger.info(
    "MultiRegionRetryGemini configured: regions=%s max_retries=%d "
    "base_backoff=%.1fs max_backoff=%.1fs pool_exhausted_wait=%.0fs "
    "backup_model=%s",
    list(_REGIONS), _MAX_RETRIES, _BASE_BACKOFF_S, _MAX_BACKOFF_S,
    _FULL_POOL_WAIT_S, _BACKUP_MODEL or "(disabled)",
)

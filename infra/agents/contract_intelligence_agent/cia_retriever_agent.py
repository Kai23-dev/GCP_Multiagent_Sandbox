"""CIA Retriever Agent - Semantic search on unstructured documents using RAG.

This agent is specific to the Contract Intelligence Agent (CIA) and provides document
retrieval capabilities for contract-to-invoice price comparison and savings detection.

Reference: SSI_Agents_Analysis.csv - Retriever Agent
"""

import json
import logging
import os
import re
from collections import defaultdict

from google.adk.agents import Agent
from google.adk.models import LlmResponse
from google.genai import types as genai_types

try:
    from .utils import get_mcp_toolset, get_genai_tools, gemini_rate_limiter
    from .multi_region_model import MultiRegionRetryGemini
    from .dedup_cache import check_cache as _dedup_check, store_result as _dedup_store
except ImportError:
    from utils import get_mcp_toolset, get_genai_tools, gemini_rate_limiter
    from multi_region_model import MultiRegionRetryGemini
    from dedup_cache import check_cache as _dedup_check, store_result as _dedup_store

logger = logging.getLogger("cia.retriever_agent")
logger.info("Initializing CIA Retriever Agent")

mcp_toolset = get_mcp_toolset()

# ---------------------------------------------------------------------------
# Document-to-supplier mapping (Ironclad metadata from BigQuery)
# Maps D1.LF.XXXXX.pdf filenames to their Ironclad counterparty names.
# Used for post-retrieval filtering to remove wrong-supplier chunks.
# ---------------------------------------------------------------------------
_DOC_SUPPLIER_MAP: dict = {}


def _load_supplier_map_from_toolbox() -> dict:
    """Load document-to-supplier mapping via GenAI Toolbox (ssi_execute_sql).

    Primary source — reads live CONTRACT_METADATA from BigQuery.
    Requires bigquery-source maxQueryResultRows >= 20000 (default is 50).
    """
    try:
        tools = get_genai_tools("ssi-toolset")
        sql_tool = None
        for t in tools:
            name = getattr(t, "__name__", None) or getattr(t, "_name", "")
            if name == "ssi_execute_sql":
                sql_tool = t
                break
        if sql_tool is None:
            logger.warning("ssi_execute_sql tool not found in ssi-toolset")
            return {}

        result = sql_tool(
            sql="SELECT signed_copy_filename, counterparty_name "
                "FROM ai_financial_dlp.CONTRACT_METADATA "
                "WHERE signed_copy_filename IS NOT NULL "
                "AND counterparty_name IS NOT NULL"
        )
        if not result:
            return {}

        rows = result
        if isinstance(result, str):
            rows = json.loads(result)
        if isinstance(rows, dict):
            rows = rows.get("rows", rows.get("results", [rows]))

        mapping = {}
        for row in rows:
            if isinstance(row, dict):
                fn = row.get("signed_copy_filename", "")
                cp = row.get("counterparty_name", "")
                if fn and cp:
                    mapping[fn] = cp

        if mapping:
            logger.info("Loaded %d document-to-supplier mappings via ssi_execute_sql", len(mapping))
        else:
            logger.warning("ssi_execute_sql returned 0 mappings for CONTRACT_METADATA")
        return mapping
    except Exception as exc:
        logger.error("Failed to load supplier mapping from GenAI Toolbox: %s", exc)
        return {}


def _load_supplier_map_from_json() -> dict:
    """Fallback: load from bundled JSON when BigQuery is unavailable or truncated."""
    map_path = os.path.join(os.path.dirname(__file__), "doc_supplier_mapping.json")
    try:
        with open(map_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        logger.info("Loaded %d document-to-supplier mappings from JSON fallback", len(mapping))
        return mapping
    except FileNotFoundError:
        return {}
    except Exception:
        logger.exception("Failed to load doc_supplier_mapping.json")
        return {}


def _load_supplier_map() -> dict:
    """Load supplier map: toolbox primary (live BQ data), JSON fallback.

    If toolbox returns fewer than 100 rows, it's likely still truncated
    (pre-maxQueryResultRows fix), so fall through to JSON.
    """
    toolbox_map = _load_supplier_map_from_toolbox()
    if len(toolbox_map) >= 100:
        return toolbox_map
    if toolbox_map:
        logger.warning(
            "Toolbox returned only %d mappings (likely truncated), falling back to JSON",
            len(toolbox_map),
        )
    return _load_supplier_map_from_json() or toolbox_map


_DOC_SUPPLIER_MAP = _load_supplier_map()

_SUPPLIER_FROM_REQUEST_RE = re.compile(
    r"(?:for\s+)?supplier:\s*(.+?)(?:\.\s|$)", re.IGNORECASE,
)

_STATE_KEY_SUPPLIER = "_cia_supplier_for_filter"
_STATE_KEY_CANDIDATES = "_cia_matched_counterparties"


def _extract_supplier_from_request(text):
    """Extract supplier name from the retriever's input request.

    The parent agent sends requests like:
      "Retrieve all pricing terms ... for supplier: AT&T. Extract EVERY ..."
    This is the authoritative source for the supplier name.
    """
    if not text:
        return None
    m = _SUPPLIER_FROM_REQUEST_RE.search(text)
    return m.group(1).strip() if m else None


_DBA_RE = re.compile(
    r"\b(?:d/?b/?a|doing\s+business\s+as|on\s+behalf\s+of"
    r"|f/?k/?a|formerly\s+known\s+as)\b",
    re.IGNORECASE,
)
_PUNCT_RE = re.compile(r"[.,;:()'\"\/]+")
_LEGAL_SUFFIX_RE = re.compile(
    r",?\s*\b(?:inc\.?|incorporated|llc|llp|lp|l\.?p\.?|ltd\.?|limited"
    r"|corp\.?|corporation|company|co\.?|p\.?c\.?|plc|gmbh|sa|s\.?a\.?"
    r"|n\.?a\.?|ag)\s*$",
    re.IGNORECASE,
)
_AND_SPLIT_RE = re.compile(r"\s+(?:and|or)\s+", re.IGNORECASE)
_ALIAS_STOPWORDS = frozenset([
    "the", "and", "its", "for", "all", "any", "affiliates",
    "identified", "in", "this", "or", "as", "by", "an",
    "individually", "collectively", "agreement", "services",
    "service", "company", "corporation", "partners", "group",
    "online", "price", "guide", "publication",
])


_MANUAL_ALIASES = {
    "vantive": {"baxter"},
    "baxter": {"vantive"},
}


def _build_alias_index(doc_supplier_map):
    """Auto-build supplier alias map from d/b/a and f/k/a patterns.

    Scans counterparty names for "d/b/a", "f/k/a", "doing business as",
    "formerly known as", and "on behalf of" patterns, then links the
    first significant word of each part bidirectionally.  Also merges
    ``_MANUAL_ALIASES`` for rebrands that can't be auto-detected
    (e.g. Vantive ↔ Baxter).
    """
    aliases = defaultdict(set)
    for counterparty in set(doc_supplier_map.values()):
        if not _DBA_RE.search(counterparty):
            continue
        parts = _DBA_RE.split(counterparty)
        first_words = set()
        for part in parts:
            part = part.strip()
            if not part:
                continue
            for word in part.split():
                clean = word.strip(".,;:()'\"").lower()
                if len(clean) >= 2 and clean not in _ALIAS_STOPWORDS:
                    first_words.add(clean)
                    break
        if len(first_words) >= 2:
            for fw in first_words:
                aliases[fw] |= first_words - {fw}

    for key, vals in _MANUAL_ALIASES.items():
        aliases[key] |= vals

    return dict(aliases)


_SUPPLIER_ALIASES = _build_alias_index(_DOC_SUPPLIER_MAP)
logger.info("Built supplier alias index: %d entries", len(_SUPPLIER_ALIASES))


def _supplier_name_matches(counterparty, supplier_keywords):
    """Check if a counterparty name matches any of the supplier keywords.

    Uses bidirectional substring matching with a punctuation-normalized
    fallback.  A counterparty matches if any keyword is found inside its
    name (forward) OR if the counterparty name is found inside the full
    supplier name (reverse).

    The punctuation-normalized fallback strips commas, periods, and other
    punctuation before matching so that "Medline Industries, Inc" matches
    "Medline Industries Inc" despite the comma difference.
    """
    if not counterparty:
        return False
    cp_lower = counterparty.lower()
    full_name = supplier_keywords[0]
    idx = full_name.find(cp_lower)
    if idx >= 0 and (idx == 0 or not full_name[idx - 1].isalnum()):
        return True
    if any(kw in cp_lower for kw in supplier_keywords):
        return True
    cp_norm = _PUNCT_RE.sub("", cp_lower)
    full_norm = _PUNCT_RE.sub("", full_name)
    idx = full_norm.find(cp_norm)
    if idx >= 0 and (idx == 0 or not full_norm[idx - 1].isalnum()):
        return True
    for kw in supplier_keywords:
        kw_norm = _PUNCT_RE.sub("", kw)
        if len(kw_norm) >= 3 and kw_norm in cp_norm:
            return True
    cp_base = _LEGAL_SUFFIX_RE.sub("", cp_lower).strip()
    full_base = _LEGAL_SUFFIX_RE.sub("", full_name).strip()
    if cp_base and full_base and len(cp_base) >= 5:
        if cp_base == full_base or cp_base in full_base or full_base in cp_base:
            return True
        cp_base_norm = _PUNCT_RE.sub("", cp_base)
        full_base_norm = _PUNCT_RE.sub("", full_base)
        if cp_base_norm == full_base_norm:
            return True
        for kw in supplier_keywords:
            kw_base = _LEGAL_SUFFIX_RE.sub("", kw).strip()
            kw_base_norm = _PUNCT_RE.sub("", kw_base)
            if len(kw_base_norm) >= 5 and (kw_base_norm in cp_base_norm or cp_base_norm in kw_base_norm):
                return True
    return False


def _build_supplier_keywords(supplier_name):
    """Build a list of matching keywords from the supplier name.

    Returns the full (lowercased) supplier name, any sub-parts split on
    " and " (for composite names the parent agent builds, e.g.
    "MEDLINE INDUSTRIES INC and Medline Industries, LP"), and known aliases.

    Short-word heuristics were removed because common English words caused
    massive false-positive rates.  Bidirectional matching with punctuation
    normalization in ``_supplier_name_matches`` handles name variants.
    """
    if not supplier_name:
        return []
    keywords = [supplier_name.lower()]
    and_parts = _AND_SPLIT_RE.split(supplier_name)
    if len(and_parts) >= 2:
        for part in and_parts:
            part = part.strip()
            if part:
                kw = part.lower()
                if kw not in keywords:
                    keywords.append(kw)
    for kw in list(keywords):
        for alias in _SUPPLIER_ALIASES.get(kw, []):
            if alias not in keywords:
                keywords.append(alias)
    return keywords


def _find_candidate_counterparties(supplier_name):
    """Find all counterparties in the supplier map that match the given name.

    Returns a sorted list of unique counterparty names that pass bidirectional
    substring matching.  Used to show the user which suppliers the filter will
    keep, and to surface near-matches when no exact match exists.
    """
    if not supplier_name or not _DOC_SUPPLIER_MAP:
        return []
    keywords = _build_supplier_keywords(supplier_name)
    matched = set()
    for counterparty in set(_DOC_SUPPLIER_MAP.values()):
        if counterparty and _supplier_name_matches(counterparty, keywords):
            matched.add(counterparty)
    return sorted(matched)


MAX_CLUSTERS_FOR_DISAMBIGUATION = 5
_ARTICLES = frozenset(["the", "a", "an"])


def _first_significant_word(name):
    """Extract the first non-article word (>=2 chars), punct-normalized."""
    for w in name.lower().split():
        clean = _PUNCT_RE.sub("", w)
        if clean and clean not in _ARTICLES and len(clean) >= 2:
            return clean
    return _PUNCT_RE.sub("", name.lower())


def _cluster_counterparties(counterparties):
    """Group counterparties into clusters of related entities using union-find.

    Two counterparties are merged if either:
    - One name is a substring of the other (e.g. "Medline" in "Medline Industries")
    - They share the same first significant word (e.g. "3M Company" and "3M Cogent")

    Returns a sorted list of clusters (each cluster is a sorted list of names).
    """
    n = len(counterparties)
    if n <= 1:
        return [counterparties[:]]

    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    norm_cps = [_PUNCT_RE.sub("", cp.lower()) for cp in counterparties]
    first_words = [_first_significant_word(cp) for cp in counterparties]

    for i in range(n):
        for j in range(i + 1, n):
            if norm_cps[i] in norm_cps[j] or norm_cps[j] in norm_cps[i]:
                union(i, j)
                continue
            if first_words[i] == first_words[j]:
                union(i, j)

    clusters = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(counterparties[i])

    return sorted([sorted(c) for c in clusters.values()], key=lambda c: c[0])


def _auto_select_cluster(supplier_name, clusters):
    """Return the index of the single best-matching cluster, or None."""
    target = supplier_name.lower()
    target_norm = _PUNCT_RE.sub("", target)
    matched = set()
    for idx, cluster in enumerate(clusters):
        for entry in cluster:
            entry_norm = _PUNCT_RE.sub("", entry.lower())
            if target_norm in entry_norm or entry_norm in target_norm:
                matched.add(idx)
                break
            if target in entry.lower():
                matched.add(idx)
                break
    if len(matched) == 1:
        return matched.pop()
    return None


def _build_filter_summary(supplier_name, kept_counterparties, removed_map):
    """Build a compact text summary of what the supplier filter did."""
    lines = [f"\n\n---\n**Supplier Filter Summary** (for supplier: {supplier_name})"]
    if kept_counterparties:
        unique_kept = sorted(set(kept_counterparties))
        lines.append(f"- **Contracts included from**: {', '.join(unique_kept)}")
    if removed_map:
        unique_removed = sorted(set(removed_map.values()))
        lines.append(f"- **Contracts excluded (wrong supplier)**: {', '.join(unique_removed)}")
    if not kept_counterparties and not removed_map:
        lines.append("- No supplier mapping available for retrieved documents")
    return "\n".join(lines)


_SOURCE_HEADER_RE = re.compile(r"\[Source:\s*([^\]]+)\]")


def _filter_content_text_by_supplier(tool_response, supplier_name):
    """Filter [Source: ...] sections in the ADK MCPToolset response format.

    ADK's MCPToolset wraps MCP tool results into:
      {"content": [{"text": "{\\"results\\":\\"[Source: file.pdf]\\\\n...\\"}"}]}
    This parses the inner results string, removes sections from
    wrong-supplier documents, and reassembles in-place.
    """
    content = tool_response.get("content")
    if not content or not isinstance(content, list):
        return

    keywords = _build_supplier_keywords(supplier_name)
    modified = False

    for item in content:
        if not isinstance(item, dict):
            continue
        text_val = item.get("text")
        if not isinstance(text_val, str):
            continue

        try:
            inner = json.loads(text_val)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(inner, dict):
            continue
        results_str = inner.get("results")
        if not isinstance(results_str, str) or "[Source:" not in results_str:
            continue

        sections = re.split(r"(?=\[Source:\s*[^\]]+\])", results_str)
        kept = []
        removed_sources = {}
        kept_counterparties = []

        for section in sections:
            section = section.strip()
            if not section:
                continue
            m = _SOURCE_HEADER_RE.match(section)
            if not m:
                kept.append(section)
                continue
            src = m.group(1).strip()
            counterparty = _DOC_SUPPLIER_MAP.get(src)
            if counterparty is not None and not _supplier_name_matches(counterparty, keywords):
                removed_sources[src] = counterparty
            else:
                kept.append(section)
                if counterparty:
                    kept_counterparties.append(counterparty)

        summary = _build_filter_summary(supplier_name, kept_counterparties, removed_sources)

        if removed_sources:
            inner["results"] = "\n\n---\n\n".join(kept) + summary
            item["text"] = json.dumps(inner)
            modified = True
            logger.info(
                "Supplier filter for '%s': removed %d wrong-supplier sections: %s",
                supplier_name,
                len(removed_sources),
                ", ".join(f"{s} ({c})" for s, c in removed_sources.items()),
            )
        elif kept_counterparties:
            inner["results"] = results_str + summary
            item["text"] = json.dumps(inner)
            modified = True

    return modified


def _filter_chunks_by_supplier(tool_response, supplier_name):
    """Filter RAG chunks to remove documents belonging to wrong suppliers.

    Uses the Ironclad metadata mapping (D1.LF filename -> counterparty) to
    identify and remove chunks from wrong-supplier documents. Chunks not in
    the mapping are kept (conservative approach).

    Handles two response formats:
      1. Raw MCP: dict with "chunks" list (structured chunk objects)
      2. ADK MCPToolset: dict with "content" list containing wrapped JSON text
         with [Source: filename] section markers
    """
    if not supplier_name or not _DOC_SUPPLIER_MAP:
        return tool_response

    if not isinstance(tool_response, dict):
        return tool_response

    # --- Path 1: structured chunks (raw MCP format) -------------------------
    chunks = tool_response.get("chunks", [])
    if chunks:
        keywords = _build_supplier_keywords(supplier_name)
        filtered = []
        removed_sources = []
        kept_counterparties = []

        for chunk in chunks:
            src = chunk.get("source_display_name", "")
            counterparty = _DOC_SUPPLIER_MAP.get(src)

            if counterparty is not None:
                if _supplier_name_matches(counterparty, keywords):
                    filtered.append(chunk)
                    kept_counterparties.append(counterparty)
                else:
                    removed_sources.append((src, counterparty))
                    continue
            else:
                filtered.append(chunk)

        unique_removed = {}
        for src, cp in removed_sources:
            unique_removed[src] = cp
        summary = _build_filter_summary(supplier_name, kept_counterparties, unique_removed)

        if removed_sources:
            tool_response["chunks"] = filtered
            tool_response["chunk_count"] = len(filtered)
            tool_response["sources"] = sorted(
                {c.get("source_display_name", "") for c in filtered} - {""}
            )
            context_parts = []
            for c in filtered:
                text = c.get("text", "")
                src = c.get("source_display_name", "")
                if text:
                    header = f"[Source: {src}]" if src else "[Source: unknown]"
                    context_parts.append(f"{header}\n{text}")
            tool_response["results"] = "\n\n---\n\n".join(context_parts) + summary

            logger.info(
                "Supplier filter for '%s': removed %d chunks from %d wrong-supplier docs: %s",
                supplier_name,
                len(removed_sources),
                len(unique_removed),
                ", ".join(f"{s} ({c})" for s, c in unique_removed.items()),
            )
        return tool_response

    # --- Path 2: ADK MCPToolset format (content[].text with [Source:] markers)
    content = tool_response.get("content")
    if content and isinstance(content, list):
        _filter_content_text_by_supplier(tool_response, supplier_name)
        return tool_response

    logger.warning(
        "Supplier filter for '%s': response has neither 'chunks' nor 'content' — "
        "cannot filter. Keys present: %s",
        supplier_name,
        list(tool_response.keys()),
    )
    return tool_response

retriever_instruction = """
You are a Retriever Agent specialized in semantic search on unstructured contract documents using RAG.

**Your Role:**
Retrieve relevant contract content to support analytical queries. You serve the Contract Intelligence Agent by finding contract pricing, terms, and clauses.

---

## RAG SEARCH MODE (MANDATORY)

Use **rag_search_batch** (preferred) or **rag_search** for comprehensive contract retrieval.

### Multi-Query Strategy (3 Targeted Queries — ONE Batch Call)

Instead of one broad query, use 3 targeted queries to maximize coverage.
**ALWAYS use `corpus_type="all"`** for contract retrieval — this searches all available corpora to ensure contract documents are found regardless of which corpus they are indexed in.

**PREFERRED — Single batch call (deduplicates overlapping chunks automatically):**
```
rag_search_batch(
  queries=[
    "[SUPPLIER] contract pricing rates fees discounts rebates credits volume tiers schedule",
    "[SUPPLIER] contract effective date expiration date renewal terms signatories",
    "[SUPPLIER] contract commitments obligations penalties damages MFN exclusivity termination"
  ],
  max_results_per_query=15,
  corpus_type="all"
)
→ Returns deduplicated chunks from all 3 queries in a single response.
→ Extract: dollar amounts, unit prices, rebate schedules, volume tiers,
  start/end dates, renewal terms, contract parties, MFN clauses, penalty terms.
```

### Query Keyword Expansion (improves recall)

When constructing the 3 queries, use SYNONYM VARIATIONS for key concepts — contracts may use different terminology:

| Concept | Primary Keywords | Also Include |
|---------|-----------------|-------------|
| Rebates | rebates | discounts, credits, incentives, price reductions |
| Penalties | penalties | liquidated damages, service credits, late fees |
| Pricing | pricing, unit prices | rates, fees, cost schedule, exhibit A |
| Commitments | commitments | obligations, minimum spend, volume requirements |

Do NOT add more queries — enrich the existing 3 queries with these synonyms for broader recall.

**FALLBACK — Only if rag_search_batch is unavailable:**
```
QUERY 1 — Pricing & Terms:
  rag_search("[SUPPLIER] contract pricing rates fees discounts rebates credits volume tiers schedule", corpus_type="all")
QUERY 2 — Dates & Parties:
  rag_search("[SUPPLIER] contract effective date expiration date renewal terms signatories", corpus_type="all")
QUERY 3 — Clauses & Commitments:
  rag_search("[SUPPLIER] contract commitments obligations penalties damages MFN exclusivity termination", corpus_type="all")
```

Combine results and return to parent agent.
If no data from any query: report "no contract data found" and return immediately.

### OPTIONAL QUERY 4 — P8 Invoice Evidence (only when parent requests it)

If the parent agent explicitly asks for invoice evidence from RAG (e.g., when BigQuery has incomplete data), search the invoices corpus:

```
QUERY 4 (OPTIONAL — only when parent says "also retrieve invoice evidence"):
  rag_search("[SUPPLIER] invoice pricing amounts payment", max_results=20, corpus_type="invoices")
  → Extract: invoice amounts, line items, payment details from P8 documents
```

**Rules for QUERY 4:**
- Only execute when parent explicitly requests it — do NOT run by default
- Use `max_results=20` since invoice data is supplementary
- Label results clearly as "P8 Invoice Evidence (RAG)" to distinguish from BigQuery data
- This supplements BigQuery — it does NOT replace structured invoice queries

### Targeted Query Construction

When the parent agent passes **confirmed contract identifiers** (e.g., "contract identifiers confirmed in invoice data: AUS 218"), use them to construct targeted queries:
- rag_search: "pricing terms, unit prices for contract [CONTRACT_ID] [SUPPLIER]"
- rag_search: "effective date expiration date renewal for contract [CONTRACT_ID] [SUPPLIER]"

This produces much better results than generic supplier-only queries.

### When No Contract Identifiers Are Provided (BigQuery found nothing)

The parent agent may call you with ONLY a supplier name and no contract identifiers. This happens when BigQuery had no invoice data for the supplier. **You MUST still search** — contract documents may exist even without invoice data.

Use broad supplier-name queries as shown in the Multi-Query Strategy above.

**Try name variations** for well-known companies:
- Short names: "AT&T" → also try "AT&T Inc", "AT&T Corp"
- Brand names: "Verizon" → also try "Verizon Communications", "Verizon Business"
- Parent companies: "Medline" → also try "Medline Industries"

**NEVER return "no data" without having executed at least 2 rag_search queries with different angles.**

### Pricing Extraction Rules

When extracting pricing from contract documents, ALWAYS capture:
1. **The price amount** (e.g., $25.00)
2. **The unit of measure** (e.g., per hour, per unit, per month, fixed fee)
3. **The service/item description** (e.g., "security guard services")
4. **Effective dates AND expiration dates** — ALWAYS extract both if available
5. **ALL tiered pricing/rebates** — if the contract has multiple pricing tiers (e.g., "23% at $1.1M, 25% at $2M"), extract EVERY tier, not just the first
6. **Percentage-based fees** — if pricing is expressed as a percentage (e.g., "33% of candidate's first-year salary", "10% rebate on annual spend"), ALWAYS extract the exact percentage AND the base it applies to
7. **Volume thresholds and commitment levels** — extract the spend/volume thresholds that trigger different pricing tiers
8. **Exclusivity clauses** — note if the contract grants exclusive rights for certain services

This unit-of-measure information is critical for the comparison agent to detect mismatches between contract pricing units and invoice pricing units.

### HTML Table Content

RAG chunks may contain pricing data inside HTML table tags (`<table><tr><td>`). When you see HTML in chunk text:
1. Parse the HTML table structure to extract row/column data
2. Map columns to: item description, unit price, quantity, total
3. Do NOT skip chunks just because they contain HTML

### Contract Staleness Detection

**When contract documents include expiration dates, check for staleness:**
- If the expiration date is in the past, flag: `**Contract Status:** NOT ACTIVE (expired [DATE])`
- If the contract is current: `**Contract Status:** ACTIVE (expires [DATE])`
- If no expiration date is found: `**Contract Status:** UNKNOWN (no expiration date in document)` — still return all terms from this contract
- Expired contracts should NOT be treated as authoritative for current terms, but include them labeled as historical context if relevant

### Multiple Contracts for Same Supplier — LATEST GOVERNS

When RAG returns chunks from **different contracts for the same supplier** (different DocuSign IDs, different effective dates, or different document filenames):
- **Rank contracts by effective_date DESC** (newest first). The contract with the latest effective_date is the **governing contract**.
- **Flag the governing contract** in your output: "**Governing Contract:** [contract_name] (effective [DATE])"
- **Amendment chain**: Amendments supersede the parent contract for overlapping items. If you find an amendment with a later effective_date than the original, its terms override the original — flag this clearly.
- **Multiple contracts can be active simultaneously** for different product lines — include terms from ALL but clearly label which is newest.
- **If terms conflict between contracts for the same item**, present the term from the **most recent contract** as the current/governing term and note the older contract's term as superseded.
- **If dates are unavailable**, still return all retrieved content — label each term with its source document name. Do NOT refuse to answer due to missing dates.

### Rules

1. **Use rag_search_batch** with all 3 queries in ONE call (preferred). Fall back to 3 individual rag_search calls only if batch tool is unavailable.
2. **Use max_results_per_query=15** (max_results=15 for single rag_search) — 15 chunks per query focuses on the highest-ranked matches and reduces noise from wrong-supplier documents. A post-retrieval supplier filter removes any remaining wrong-supplier chunks automatically.
3. **Always use corpus_type="all"** — searches all corpora to find contract documents.
4. **Return immediately** after queries complete. Parent decides fallback.
5. **DO NOT ask questions** — search and return results.
6. **Filter by source document, not by score** — verify chunks come from the target supplier's contract via source_display_name. Score alone is not a reliable relevance filter.
7. **READ ALL RETRIEVED CHUNKS, THEN SYNTHESIZE COMPACTLY** — a post-retrieval supplier filter automatically removes wrong-supplier chunks before you see them.  MERGE findings from ALL remaining chunks into one bullet list per category (see Output Format).  NEVER emit per-chunk summaries or verbatim chunk dumps.  Target ≤ 1500 words total in your response.

---

## Available Tools

- **rag_search_batch** (PREFERRED): Run multiple RAG queries in ONE call with automatic deduplication.
  - **Parameters:**
    - `queries`: List of search query strings (1-10 queries)
    - `max_results_per_query`: Max chunks per query — **always pass 15** (focuses on top-ranked chunks; post-retrieval supplier filter handles noise removal)
    - `corpus_type`: `"all"` (default) | `"contracts"` | `"invoices"`
  - Returns merged, deduplicated chunks from all queries in a single response.
  - Includes `chunks_before_dedup` and `per_query_chunks` for observability.
  - **Use this instead of calling rag_search 3 times.**

- **rag_search** (FALLBACK): Semantic search on documents.
  - **Parameters:**
    - `query`: Search text
    - `max_results`: Number of chunks — **always pass 15** (focuses on top-ranked chunks)
    - `corpus_type`: `"all"` (default) | `"contracts"` | `"invoices"`
  - Returns RAW document chunks with source citations — NOT a pre-synthesized answer.
  - You receive the actual document text from matching chunks.
  - Each chunk includes source file name and relevance score.
  - Also returns `sources` (list of source file names) and `chunk_count`.
  - Extract pricing terms, clause text, effective dates directly from the chunk text.
  - Use only if rag_search_batch is unavailable.

## Document Corpora

1. **Contracts (Ironclad)** — Agreements, amendments, SOWs, MSAs — pricing (Exhibit A), rebates, volume commitments, MFN clauses, payment terms
2. **Invoices (P8 FileNet)** — `corpus_type="invoices"`: Invoice PDFs (supplementary to BigQuery structured data)
3. **Policies**: Internal policies and procedures

## Query Patterns

**BEST — single batch call with 3 keyword-enriched queries:**
```
rag_search_batch(
  queries=[
    "pricing rates fees discounts rebates credits volume tiers schedule for [SUPPLIER_NAME]",
    "contract effective date expiration date renewal terms signatories for [SUPPLIER_NAME]",
    "commitments obligations penalties damages MFN exclusivity termination for [SUPPLIER_NAME]"
  ],
  max_results_per_query=15,
  corpus_type="all"
)
```

**ALSO CORRECT — 3 individual rag_search calls (fallback only):**
- rag_search("pricing rates fees discounts rebates credits volume tiers for [SUPPLIER_NAME]", corpus_type="all")
- rag_search("contract effective date expiration date renewal terms for [SUPPLIER_NAME]", corpus_type="all")
- rag_search("commitments obligations penalties damages MFN exclusivity for [SUPPLIER_NAME]", corpus_type="all")

**WRONG — one overly broad query:**
- "What are all contracts, pricing terms, unit prices, rebates, and clauses for [SUPPLIER_NAME]?"

**WRONG — repeating the same query multiple times:**
- rag_search("pricing for [SUPPLIER]") called 3 times

## SUPPLIER NAME VERIFICATION (CRITICAL)

**RAG returns semantically similar documents — it may return contracts for the WRONG supplier** if two suppliers are in the same industry (e.g., Allied Universal vs Securitas, Verizon vs AT&T).

**After EVERY retrieval, verify results belong to the requested supplier:**
1. **Source document file name** — does it contain the requested supplier's name? (e.g., `Allied_Universal_MSA.pdf`)
2. **Contract text** — is the requested supplier named as a party?

**IMPORTANT — Supplier aliases and corporate renames:** Some suppliers operate under different legal names (DBA, FKA, corporate renames). The pre-retrieval supplier filter uses an alias database to identify these relationships. **If the Supplier Filter Summary shows documents were KEPT (not listed under "Contracts excluded"), those documents ARE for the correct supplier** even if the counterparty name differs from the requested supplier name. Trust the filter's decision — it has verified the alias relationship. For example, if you search for "Vantive" and the filter keeps "Baxter Healthcare Corporation" documents, that is correct because Vantive was formerly Baxter's renal care division.

**Documents that do NOT belong to the requested supplier:** Mark them as **EXCLUDED** and list them in the "Excluded Documents" section. Do NOT use the word "MISMATCH" when describing individual excluded documents — that word is reserved for the overall Match Status.

**Overall Match Status rules:**
- Set **CONFIRMED** when at least one document genuinely belongs to the requested supplier — including documents kept by the supplier filter under an alias/DBA/FKA relationship (even if other documents were excluded).
- Set **MISMATCH** ONLY when ZERO documents belong to the requested supplier — every returned document is for a different entity AND was NOT kept by the supplier filter.
- Set **PARTIAL** when a related entity is found (e.g., parent company but not subsidiary) but no exact match, AND the supplier filter did NOT confirm the relationship.

## ANTI-HALLUCINATION RULES (CRITICAL)

**These rules prevent fabrication of contract terms not present in the retrieved chunks.**

1. **VERBATIM EXTRACTION ONLY** — Every fact you report MUST appear verbatim (or near-verbatim) in at least one retrieved chunk. If you cannot point to a specific chunk that contains the information, DO NOT include it. Inventing plausible-sounding contract terms is the single worst failure mode.

2. **MANDATORY SOURCE CITATION** — Every extracted term MUST include `[source_filename.pdf]` inline. If you cannot cite a source file, the term does not exist.
   - CORRECT: `$1,000,000 liability cap [D1.LF.00111164.pdf]`
   - WRONG: `$1,000,000 liability cap` (no source = possibly fabricated)

3. **ZERO INFERENCE** — Do NOT infer, extrapolate, or "fill in" standard contract terms that are not explicitly stated in the chunks. Do NOT add terms because "most contracts include them." Only report what you can READ in the retrieved text.

4. **DOCUMENT TYPE CLASSIFICATION** — Classify each verified source document as one of:
   - **Master Agreement / Enterprise Agreement** — contains comprehensive pricing, terms, obligations
   - **Amendment** — modifies specific terms of an existing agreement
   - **SOW / Order Form** — project-specific scope and pricing
   - **MOU / Letter of Intent** — preliminary, non-binding
   - **NDA / Confidentiality Agreement** — no pricing content
   - **Facility Agreement** — site-specific service terms
   Report the document types found. If no Master/Enterprise Agreement is found, explicitly state this gap.

5. **WHEN DOCUMENTS ARE THIN** — If retrieved chunks contain only amendments, MOUs, NDAs, or facility-level agreements (but NO master agreement with comprehensive pricing):
   - Report ONLY what the retrieved documents actually contain
   - State: "No master supply/enterprise agreement found — only [amendments/MOUs/NDAs] retrieved"
   - Do NOT fabricate terms that would typically appear in a master agreement
   - Set Retrieval Confidence to LOW

## CONFIDENCE CALIBRATION (MANDATORY)

**Default is LOW. Upgrade ONLY with evidence.**

| Level | Criteria | Example |
|-------|----------|---------|
| **HIGH** | Master agreement found with specific pricing ($ amounts), AND 5+ chunks from verified supplier documents, AND key terms cited with source filenames | Full enterprise agreement with Exhibit A pricing |
| **MEDIUM** | Some contract documents found but incomplete (only amendments/SOWs, no master agreement), OR fewer than 5 verified chunks, OR pricing found but without volume tiers/rebates | 3 amendments found, no master agreement |
| **LOW** | Only NDAs/MOUs found, OR very few chunks (< 3), OR no pricing data at all, OR only boilerplate language found | 2 NDAs and 1 MOU, no pricing |

**Calibration rule:** Count the number of DISTINCT facts you extracted with source citations. If < 3 cited facts → LOW. If 3-7 cited facts → MEDIUM. If 8+ cited facts with pricing → HIGH.

---

## Output Format (MANDATORY — COMPACT SYNTHESIS)

**Chunks are pre-filtered by a post-retrieval supplier filter to remove wrong-supplier documents. Distill ALL remaining chunks into a compact structured summary (≤ 1500 words).**

**HARD LIMITS:**
- **NEVER emit per-chunk summaries or verbatim chunk dumps.**  Merge findings from ALL chunks into ONE bullet list per category.
- **NEVER include** a "Queries Executed" section, SQL code blocks, or tool call logs.
- **Target length: ≤ 1500 words total.**  Verbose per-chunk dumps caused 170-second responses; do NOT do that.
- **Do NOT repeat the same clause** across multiple bullets — state it once, cite the source doc inline.
- **Do preserve ALL numeric values verbatim** from the chunks — dollar amounts, percentages, dates, tier thresholds, SLA targets, liquidated damages amounts. Numerical fidelity is more important than narrative completeness.

### === CONTRACT SUMMARY === (MANDATORY — always emit this block FIRST)

Provide a condensed 3-5 sentence summary that downstream agents can use WITHOUT processing the full output.  Include:
1. Supplier name and contract type(s) found (e.g., "Enterprise Agreement", "Facility Services Agreement")
2. Key pricing terms — the most important unit prices, fixed fees, or tier thresholds (up to 5 line items)
3. Contract status (ACTIVE / EXPIRED) with effective and expiration dates
4. Any rebate, MFN, or exclusivity clauses (one sentence)
5. Confidence level (HIGH / MEDIUM / LOW)

**Example (single contract):**
```
=== CONTRACT SUMMARY ===
Supplier: Medline Industries. Governing Contract: Enterprise Agreement (effective 2024-01-01, expires 2026-12-31, ACTIVE).
Key pricing: Exam gloves $4.25/case, Gauze pads $2.10/unit, Syringes $0.85/unit.
3% rebate on annual spend >$500K, MFN clause active. Confidence: HIGH (12 verified chunks, master agreement + 2 amendments).
===
```

**Example (multiple contracts — latest governs):**
```
=== CONTRACT SUMMARY ===
Supplier: Medline Industries. Governing Contract: Amendment #2 (effective 2024-06-01, expires 2026-12-31, ACTIVE).
Supersedes: Original Enterprise Agreement (effective 2022-01-01). Amendment revised pricing on 12 SKUs.
Key pricing (from amendment): Exam gloves $3.95/case (was $4.25), Gauze pads $2.10/unit (unchanged).
3% rebate on annual spend >$500K, MFN clause active. Confidence: HIGH.
===
```

### Supplier Verification
- **Requested**: [SUPPLIER_NAME from parent]
- **Match Status**: CONFIRMED / PARTIAL / MISMATCH  (single word)
- **Matched Counterparties**: List the counterparty names shown in the "Supplier Filter Summary" appended to tool results — these are the exact entity names from contract metadata that matched the requested supplier.  Present them so the user can verify the right entities were included.
- **Source Documents (verified only)**: comma-separated list of file names that genuinely belong to the requested supplier
- **Document Types Found**: e.g., "2 Amendments, 1 MOU — no Master Agreement"
- **Excluded Documents**: comma-separated list of files for OTHER suppliers (one line, no per-doc rationale)

### Pricing & Rebates  (merged from all verified chunks)
- `[$ amount] per [unit]` — [service/item description]  `[source_filename.pdf]`
- `[X]% rebate` when annual spend ≥ `[$ threshold]` — [tier description]  `[source_filename.pdf]`
- (one bullet per distinct price/tier; omit section entirely if none found — do NOT fabricate)

### Commitments, Penalties, MFN, Exclusivity
- `[clause type]`: [concise one-line summary]  `[source_filename.pdf]`
- (bullets only; omit section entirely if none found — do NOT fabricate)

### Dates & Parties
- **Governing Contract**: [contract_name] (effective [date], expires [date]) — **ACTIVE / EXPIRED / UNKNOWN**
- **Parties**: [contracting entities]
- **Amendments**: [list date + what was amended, one line each] OR "None identified"
- **Superseded Contracts**: [list older contracts with dates, if any] OR "None — single contract on file"

### Gaps
- List what the parent asked for that was NOT found in the retrieved chunks.
- If no Master Agreement found: "No master supply/enterprise agreement retrieved — results based on [amendments/MOUs/etc.] only"
- If no pricing found: "No pricing terms found in retrieved documents"

### Retrieval Confidence
- **HIGH** / **MEDIUM** / **LOW** — [one-line reason citing number of verified docs and types found]

## Important Notes

1. **Amendment Priority**: Amendments with a later effective_date ALWAYS override the original contract for overlapping items. Present the amended price as the current/governing price. Flag the original price as superseded.
2. **ALL Volume Tiers**: Extract every tier (as separate bullets), not just the first.
3. **NEVER return data from the wrong supplier** — a mismatch is worse than no data.
4. **NEVER fabricate terms** — reporting "no data found" is ALWAYS better than inventing plausible terms. An honest gap is scored higher than a confident hallucination.
5. **Terminology**: Use "EXCLUDED" for individual discarded documents; "MISMATCH" ONLY as overall Match Status when NO documents match.
6. **Return Control**: Return results immediately after queries complete — no follow-up questions.
"""

async def _retriever_before_model_callback(callback_context, llm_request):
    """Extract the supplier name from the last user message and store in state.

    Scans user messages in reverse so each new retriever invocation picks up
    the current supplier — not a stale name from a prior query in the same
    session.  If no "supplier:" pattern is found (e.g. on subsequent model
    calls within the same invocation), the existing state value is kept.

    When a new supplier is detected and its candidate counterparties form
    multiple distinct clusters, returns a disambiguation LlmResponse instead
    of proceeding — the parent agent presents the options to the user.
    """
    for content in reversed(list(getattr(llm_request, "contents", []))):
        if getattr(content, "role", None) != "user":
            continue
        for part in getattr(content, "parts", []):
            text = getattr(part, "text", None)
            if not text:
                continue
            supplier = _extract_supplier_from_request(text)
            if supplier:
                prev = callback_context.state.get(_STATE_KEY_SUPPLIER)
                candidates = _find_candidate_counterparties(supplier)
                if not candidates and "," in supplier:
                    parts = supplier.split(",")
                    while len(parts) > 1 and not candidates:
                        parts.pop()
                        shorter = ",".join(parts).strip()
                        if shorter:
                            candidates = _find_candidate_counterparties(shorter)
                            if candidates:
                                logger.info(
                                    "Truncated supplier '%s' -> '%s' (%d candidates)",
                                    supplier, shorter, len(candidates),
                                )
                                supplier = shorter
                if not candidates and "(" in supplier:
                    stripped = re.sub(r"\s*\([^)]*\)", "", supplier).strip()
                    if stripped and stripped != supplier:
                        candidates = _find_candidate_counterparties(stripped)
                        if candidates:
                            logger.info(
                                "Stripped parenthetical from supplier '%s' -> '%s' (%d candidates)",
                                supplier, stripped, len(candidates),
                            )
                            supplier = stripped
                callback_context.state[_STATE_KEY_SUPPLIER] = supplier
                callback_context.state[_STATE_KEY_CANDIDATES] = candidates
                if prev != supplier:
                    logger.info(
                        "Supplier for filter: '%s' (was '%s'), %d candidate counterparties",
                        supplier, prev, len(candidates),
                    )

                    # --- Disambiguation check (only on new supplier) ---
                    if len(candidates) > 1:
                        clusters = _cluster_counterparties(candidates)
                        num_clusters = len(clusters)

                        if num_clusters > 1:
                            best = _auto_select_cluster(supplier, clusters)
                            if best is not None:
                                selected = clusters[best]
                                logger.info(
                                    "Disambiguation: '%s' → auto-selected cluster %d "
                                    "(%d counterparties: %s) out of %d clusters",
                                    supplier, best, len(selected),
                                    ", ".join(selected[:3]), num_clusters,
                                )
                                candidates = selected
                                callback_context.state[_STATE_KEY_CANDIDATES] = candidates
                                num_clusters = 1

                        if num_clusters > MAX_CLUSTERS_FOR_DISAMBIGUATION:
                            logger.info(
                                "Disambiguation: '%s' matched %d counterparties across "
                                "%d clusters (>%d) — too vague",
                                supplier, len(candidates), num_clusters,
                                MAX_CLUSTERS_FOR_DISAMBIGUATION,
                            )
                            return LlmResponse(
                                content=genai_types.Content(
                                    role="model",
                                    parts=[genai_types.Part(
                                        text=(
                                            f"--- DISAMBIGUATION NEEDED ---\n"
                                            f"The supplier name \"{supplier}\" is too broad — "
                                            f"it matched {len(candidates)} counterparties across "
                                            f"{num_clusters} distinct supplier groups in our "
                                            f"contract database.\n\n"
                                            f"Please provide a more specific supplier name "
                                            f"to proceed with contract retrieval."
                                        ),
                                    )],
                                ),
                            )

                        if num_clusters > 1:
                            logger.info(
                                "Disambiguation: '%s' matched %d counterparties across "
                                "%d clusters — presenting options",
                                supplier, len(candidates), num_clusters,
                            )
                            options = []
                            for idx, cluster in enumerate(clusters, 1):
                                names = ", ".join(cluster)
                                options.append(f"**Option {idx}:** {names}")

                            return LlmResponse(
                                content=genai_types.Content(
                                    role="model",
                                    parts=[genai_types.Part(
                                        text=(
                                            f"--- DISAMBIGUATION NEEDED ---\n"
                                            f"Multiple distinct supplier entities match "
                                            f"\"{supplier}\" in our contract database. "
                                            f"Please specify which supplier you're "
                                            f"interested in:\n\n"
                                            + "\n".join(options)
                                            + "\n\nReply with the specific supplier name "
                                            "to proceed."
                                        ),
                                    )],
                                ),
                            )

                        logger.info(
                            "Disambiguation: '%s' → 1 cluster (%d counterparties) — auto-proceed",
                            supplier, len(candidates),
                        )
                break
        else:
            continue
        break

    waited = await gemini_rate_limiter.acquire()
    if waited > 0:
        logger.info("Rate limiter delayed model call by %.2fs", waited)
    return None


def _retriever_before_tool_callback(tool, args, tool_context):
    """Block duplicate rag_search / rag_search_batch calls via shared cache."""
    tool_name = getattr(tool, "name", str(tool))
    cached = _dedup_check(tool_name, args, tool_context)
    if cached is not None:
        return cached
    return None


def _retriever_after_tool_callback(tool, args, tool_context, tool_response):
    """Filter wrong-supplier chunks, then store in shared cache.

    ADK MCPToolset returns a CallToolResult object, not a dict — mutations to
    a converted copy don't propagate.  When filtering occurs, we return the
    filtered dict so ADK uses it as the function response (functions.py L358).

    The supplier name is read from session state (set by
    _retriever_before_model_callback on the first LLM call).
    """
    tool_name = getattr(tool, "name", str(tool))
    filtered_resp = None

    if tool_name in ("rag_search_batch", "rag_search"):
        supplier = tool_context.state.get(_STATE_KEY_SUPPLIER)
        if not supplier:
            logger.warning(
                "Supplier filter: no supplier in session state — skipping filter",
            )
        else:
            resp = tool_response
            converted = False
            if not isinstance(resp, dict):
                logger.info(
                    "Supplier filter: tool_response is %s, not dict — converting",
                    type(resp).__name__,
                )
                if hasattr(resp, "model_dump"):
                    resp = resp.model_dump()
                    converted = True
                elif hasattr(resp, "__dict__"):
                    resp = vars(resp).copy()
                    converted = True
                else:
                    try:
                        resp = dict(resp)
                        converted = True
                    except (TypeError, ValueError):
                        resp = None
            if isinstance(resp, dict):
                _filter_chunks_by_supplier(resp, supplier)
                if converted:
                    filtered_resp = resp

    effective = filtered_resp if filtered_resp is not None else tool_response
    _dedup_store(tool_name, args, effective, tool_context)
    return filtered_resp


# Define the retriever agent
_tools = [mcp_toolset] if mcp_toolset else []
cia_retriever_agent = Agent(
    name="cia_retriever_agent",
    model=MultiRegionRetryGemini(model="gemini-2.5-flash"),
    description="CIA agent for semantic search on documents using RAG. Retrieves contracts, invoices, and policies and returns a COMPACT merged-findings summary (pricing, rebates, commitments, dates) \u2014 not a per-chunk dump.",
    instruction=retriever_instruction,
    tools=_tools,  # Already returns [] on failure
    generate_content_config=genai_types.GenerateContentConfig(
        temperature=0.1,
        # Retriever just extracts and formats RAG results — no reasoning needed.
        # Default (24k thinking budget) was causing 100s+ per model call.
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
        # Retriever emits a COMPACT merged-findings summary (see instruction's
        # Output Format section).  The compactness is enforced by the
        # INSTRUCTION ("≤ 1500 words", merged bullet lists) — not by this
        # cap.  The cap is a safety ceiling only.
        #
        # Observed real-world retriever output sizes (2026-04-23 logs):
        #   - Thin / excluded supplier:     ~ 500–2,000 chars  ( ~200–800 tok)
        #   - Standard supplier:            ~ 4,000–7,000 chars (~1.5–3k tok)
        #   - Rich supplier (5+ source PDFs): ~ 8,000–11,000 chars (~3.5–4.5k tok)
        #
        # A previous 4,096-token cap was truncating rich-supplier output
        # mid-sentence (Parnassus Group: 10,014 chars = EXACT 4096-token
        # boundary, cut at "This is").  16,384 gives ~3× headroom above
        # observed maxima while still being well below the legacy 24,576
        # (which correlated with verbose per-chunk dumps and ~90s latency).
        # If _log_truncation_if_any ever fires at this new ceiling, the
        # retriever instruction needs another round of tightening — not a
        # further cap increase.
        max_output_tokens=16384,
    ),
    before_model_callback=_retriever_before_model_callback,
    before_tool_callback=_retriever_before_tool_callback,
    after_tool_callback=_retriever_after_tool_callback,
    output_key="retrieval_result",
)
logger.info(
    "CIA Retriever Agent initialized (tools: %s)",
    "MCP" if mcp_toolset else "none",
)

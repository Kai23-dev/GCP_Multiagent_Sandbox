"""SQL Generation Agent - decides which tables to use for answering user questions."""
from __future__ import annotations

import logging
import os
import pathlib
import atexit
import signal

import vertexai
from vertexai.agent_engines import AdkApp
from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google.genai import types
from toolbox_core import ToolboxSyncClient
from google.auth.exceptions import DefaultCredentialsError
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google.cloud import storage
from datetime import datetime, timezone
import re
import subprocess
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('SQL_GEN')

logger.info("sg===== SQL Generation Agent loading...")

# GCS configuration for table schemas
GCS_BUCKET_NAME = os.environ.get("TABLE_SCHEMA_GCS_BUCKET", "")
GCS_PREFIX = os.environ.get("TABLE_SCHEMA_GCS_PREFIX", "ai_financial_dlp/")
logger.info("sg===== GCS config: bucket=%s, prefix=%s", GCS_BUCKET_NAME, GCS_PREFIX)


def load_table_schema(table_name: str) -> str:
    """Load a specific table schema markdown file from GCS bucket.

    Args:
        table_name: The name of the table to load schema for (e.g., 'AP_INVOICES_ALL', 'AP_CHECKS')

    Returns:
        The detailed schema information for the specified table, or an error message if not found.
    """
    if not GCS_BUCKET_NAME:
        return "Error: No GCS bucket configured for table schemas."

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        table_name_upper_case = table_name.upper()
        blob_path = f"{GCS_PREFIX}{table_name_upper_case}.md"
        blob = bucket.blob(blob_path)

        if blob.exists():
            logger.info("sg===== Loading schema for table: %s", table_name)
            content = blob.download_as_text().strip()
            if content:
                return content
            else:
                return f"Error: Schema file for table '{table_name}' is empty."
        else:
            return f"Error: Schema file not found for table '{table_name}'. Please check the table name."
    except Exception as e:
        logger.error("sg===== Error loading schema for %s: %s", table_name, e)
        return f"Error loading schema for table '{table_name}': {str(e)}"


# Environment variables for GenAI toolbox
GENAI_MCP_URL = os.environ.get("GENAI_MCP_URL") or ""
TOOLBOX_BQ_PROJECT_ID = os.environ.get("SCO_KB_PROJECT_ID") or ""
logger.info("sg===== Toolbox config: url=%s, bq_project=%s", bool(GENAI_MCP_URL), TOOLBOX_BQ_PROJECT_ID)


def get_id_token(audience: str) -> str:
    """Get Google Cloud ID token for authenticating to Cloud Run services."""
    try:
        request = Request()
        return id_token.fetch_id_token(request, audience)
    except DefaultCredentialsError:
        if sys.platform == "win32":
            result = subprocess.run('gcloud auth print-identity-token', capture_output=True, text=True, check=False, shell=True)
        else:
            result = subprocess.run(["gcloud", "auth", "print-identity-token"], capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


# GenAI Toolbox MCP setup
genai_mcp_tools = []
toolbox_client = None

if GENAI_MCP_URL:
    logger.info("sg===== Setting up GenAI toolbox")

    def _genai_toolbox_auth_header() -> str:
        token = get_id_token(GENAI_MCP_URL)
        return f"Bearer {token}" if token else ""

    toolbox_client = ToolboxSyncClient(
        GENAI_MCP_URL,
        client_headers={"Authorization": _genai_toolbox_auth_header},
    )
    logger.info("sg===== Toolbox client created")

    # Known user IDs
    _USER_IDS = ["auditor", "buyer", "supplier_classification", "trend", "financial_leakage", "visualizer"]

    def _canonical_tool_name(name: str) -> str:
        for _uid in _USER_IDS:
            for _sep in ("_", "-"):
                _prefix = f"{_uid}{_sep}"
                if name.startswith(_prefix):
                    name = name[len(_prefix):]
                    break
        for _prefix in ("bigquery_",):
            if name.startswith(_prefix):
                name = name[len(_prefix):]
        return name

    def _load_toolset(toolset_name: str) -> dict[str, object]:
        """Load a toolset by name and return tools keyed by tool name."""
        logger.debug("sg===== Loading toolset: %s", toolset_name)
        try:
            loaded = toolbox_client.load_toolset(toolset_name)
        except Exception as e:
            logger.error("sg===== Failed to load toolset %s: %s", toolset_name, e)
            raise

        if loaded is None:
            return {}

        if isinstance(loaded, list):
            tools = loaded
        else:
            try:
                tools = list(loaded)
            except TypeError:
                tools = [loaded]

        if TOOLBOX_BQ_PROJECT_ID:
            try:
                tools = [t.bind_params({"project_id": TOOLBOX_BQ_PROJECT_ID}) for t in tools]
            except Exception:
                pass

        return {_canonical_tool_name(t.__name__): t for t in tools}

    # Load all user toolsets at startup
    _toolset_cache: dict[str, dict[str, object]] = {}
    for _uid in _USER_IDS:
        _ts_name = f"{_uid}-toolset"
        try:
            _toolset_cache[_uid] = _load_toolset(_ts_name)
            logger.info("sg===== Loaded toolset '%s': %d tools", _ts_name, len(_toolset_cache[_uid]))
        except Exception as e:
            logger.warning("sg===== Failed to load toolset '%s': %s", _ts_name, e)
            _toolset_cache[_uid] = {}

    # Use the first successfully loaded toolset as reference
    _default_tools: list = []
    for _uid in _USER_IDS:
        if _toolset_cache[_uid]:
            _default_tools = list(_toolset_cache[_uid].values())
            logger.info("sg===== Using '%s' toolset as schema reference (%d tools)", _uid, len(_default_tools))
            break

    def _validate_sql(sql: str) -> str | None:
        """Validate SQL before execution. Returns error message if invalid, None if OK."""
        sql_upper = sql.upper()
        if 'XXC_GL_SUMMARY' in sql_upper and 'LEDGER_ID' not in sql_upper:
            return (
                "Error: Query against XXC_GL_SUMMARY is missing the required "
                "ledger_id filter. XXC_GL_SUMMARY contains multiple rows per "
                "transaction across different ledgers. You MUST add "
                "`AND TRIM(t1.ledger_id) = '1'` to the WHERE clause to prevent "
                "duplicate rows. TRIM is required because ledger_id has trailing whitespace. "
                "Fix the query and retry."
            )
        if 'XXC_GL_SUMMARY' in sql_upper and 'DISTINCT' not in sql_upper:
            has_agg = any(fn in sql_upper for fn in ('SUM(', 'COUNT(', 'AVG(', 'MIN(', 'MAX(', 'GROUP BY'))
            if not has_agg:
                return (
                    "Error: Non-aggregation query against XXC_GL_SUMMARY must "
                    "use SELECT DISTINCT to prevent duplicate rows. Fix the "
                    "query and retry."
                )
        if re.search(r'SELECT\s+\*\s+FROM', sql_upper) or re.search(r'SELECT\s+\w+\.\*', sql_upper):
            return (
                "Error: SELECT * or SELECT alias.* is not allowed. BigQuery is "
                "columnar — selecting all columns causes unnecessary full-column "
                "scans and timeouts. Specify only the columns needed for this "
                "query. Refer to the recommended column sets in your instructions. "
                "Fix the query and retry."
            )
        if 'XXC_GL_SUMMARY' in sql_upper and 'PERIOD_NAME' not in sql_upper:
            return (
                "Error: Query against XXC_GL_SUMMARY is missing the required "
                "period_name filter. You MUST add `AND period_name = 'OCT-25'` "
                "to the WHERE clause. Do NOT use effective_date — it causes "
                "incorrect results. Fix the query and retry."
            )
        if 'XXC_GL_SUMMARY' in sql_upper and 'EFFECTIVE_DATE' in sql_upper:
            return (
                "Error: Do NOT use effective_date for XXC_GL_SUMMARY queries. "
                "effective_date causes incorrect results. Use "
                "`period_name = 'OCT-25'` instead. Remove the effective_date "
                "filter and use period_name. Fix the query and retry."
            )
        is_invoice_lookup = 'XXC_GL_SUMMARY' in sql_upper and 'INVOICE_NUMBER' in sql_upper
        if is_invoice_lookup:
            if 'ACCOUNT' not in sql_upper or not re.search(r'ACCOUNT\s*(AS\s+INT|>|>=)', sql_upper, re.IGNORECASE):
                has_account_filter = re.search(
                    r'SAFE_CAST\s*\(\s*\w*\.?\s*ACCOUNT\s+AS\s+INT64\s*\)\s*>\s*5000',
                    sql_upper
                )
                if not has_account_filter:
                    return (
                        "Error: Invoice lookup query against XXC_GL_SUMMARY must "
                        "include `AND SAFE_CAST(account AS INT64) > 5000` to filter "
                        "for P&L accounts only. It must also use `SELECT DISTINCT`, "
                        "`AND TRIM(ledger_id) = '1'`, and `AND period_name = 'OCT-25'`. "
                        "Follow the invoice lookup template in instruction rule 16 exactly. "
                        "Fix the query and retry."
                    )
        return None

    def _make_user_tool_wrapper(default_tool, *, exposed_tool_name: str | None = None, lookup_tool_name: str | None = None):
        """Create a wrapper function that delegates to the user-specific toolset."""
        import inspect

        original_sig = inspect.signature(default_tool)
        canonical_name = _canonical_tool_name(default_tool.__name__)
        tool_name = exposed_tool_name or canonical_name
        dispatch_name = lookup_tool_name or canonical_name

        new_params = list(original_sig.parameters.values()) + [
            inspect.Parameter(
                "tool_context",
                inspect.Parameter.KEYWORD_ONLY,
                default=None,
                annotation=ToolContext,
            ),
        ]
        new_sig = original_sig.replace(parameters=new_params)

        def wrapper(**kwargs):
            tc = kwargs.pop("tool_context", None)
            if tc is None:
                return "Error: Missing tool_context for tool invocation."

            user_id = tc.user_id
            if user_id not in _toolset_cache:
                user_id = os.environ.get("DEFAULT_USER_ID", "auditor")

            user_tools = _toolset_cache.get(user_id, {})
            user_tool = user_tools.get(dispatch_name)

            if user_tool is None:
                for _candidate in user_tools.values():
                    try:
                        if inspect.signature(_candidate) != original_sig:
                            continue
                    except Exception:
                        continue
                    if default_tool.__doc__ and getattr(_candidate, "__doc__", None):
                        if _candidate.__doc__ != default_tool.__doc__:
                            continue
                    user_tool = _candidate
                    break

            if user_tool is None:
                return f"Error: Tool '{tool_name}' not available for user '{user_id}'."

            # Validate SQL before execution
            for key in ("query", "sql", "statement"):
                if key in kwargs:
                    sql_val = kwargs[key]
                    if isinstance(sql_val, str):
                        validation_error = _validate_sql(sql_val)
                        if validation_error:
                            logger.warning("sg===== SQL validation failed: %s", validation_error)
                            return validation_error
                    break


            logger.info("sg===== Tool call: %s (user=%s)", tool_name, user_id)
            result = user_tool(**kwargs)

            # Log SQL queries for testing
            for key in ["query", "sql", "statement"]:
                if key in kwargs:
                    sql = kwargs[key]
                    if isinstance(sql, str) and sql.strip().upper().startswith(("SELECT", "WITH")):
                        logger.info("sg===== Generated SQL:%s", sql.replace('\n', ' '))
                    break

            return result

        wrapper.__name__ = tool_name
        wrapper.__qualname__ = tool_name
        wrapper.__doc__ = default_tool.__doc__
        wrapper.__signature__ = new_sig
        wrapper.__annotations__ = {
            p.name: p.annotation for p in new_params if p.annotation is not inspect.Parameter.empty
        }
        return wrapper

    genai_mcp_tools = [_make_user_tool_wrapper(t) for t in _default_tools]

    # Backwards-compatible aliases
    _BIGQUERY_ALIASES: dict[str, str] = {
        "get_dataset_info": "bigquery_get_dataset_info",
        "get_table_info": "bigquery_get_table_info",
        "list_dataset_ids": "bigquery_list_dataset_ids",
        "list_table_ids": "bigquery_list_table_ids",
    }
    _tools_by_canonical_name = {_canonical_tool_name(t.__name__): t for t in _default_tools}
    for _canonical, _alias in _BIGQUERY_ALIASES.items():
        _default_tool = _tools_by_canonical_name.get(_canonical)
        if _default_tool is None:
            continue
        genai_mcp_tools.append(
            _make_user_tool_wrapper(
                _default_tool,
                exposed_tool_name=_alias,
                lookup_tool_name=_canonical,
            )
        )
    logger.info("sg===== Created %d tool wrappers", len(genai_mcp_tools))
else:
    logger.warning("sg===== GENAI_MCP_URL not configured, toolbox disabled")

# Cleanup handlers
if toolbox_client is not None:
    atexit.register(toolbox_client.close)

    def _shutdown_handler(_signum, _frame):
        try:
            toolbox_client.close()
        except Exception:
            pass
    try:
        signal.signal(signal.SIGTERM, _shutdown_handler)
        signal.signal(signal.SIGINT, _shutdown_handler)
    except Exception:
        pass

_INSTRUCTION_DIR = pathlib.Path(__file__).parent / "instruction"


def _load_additional_instruction_for_user(user_id: str) -> str:
    for candidate in (user_id, "auditor"):
        md_path = _INSTRUCTION_DIR / f"{candidate}.md"
        try:
            if md_path.exists():
                return md_path.read_text(encoding="utf-8")
        except Exception:
            continue
    return ""


def _build_instruction(ctx) -> str:
    """Dynamic instruction provider that selects the table summary based on user_id."""
    user_id = ctx.user_id
    if user_id not in _toolset_cache:
        user_id = os.environ.get("DEFAULT_USER_ID", "auditor")
    additional_instruction = _load_additional_instruction_for_user(user_id)
    logger.debug("sg===== Building instruction for user_id: %s", user_id)

    return f"""
You are a SQL Generation Agent specialized in analyzing user questions and determining which BigQuery tables should be used to answer them. And generate the SQL query to retrieve the data for the user.

Your task is to:
1. Analyze the user's question to understand what data they need
2. Review the available table summary below to identify relevant tables
3. Use the `load_table_schema` tool to get detailed schema information for the relevant tables
4. Generate the SQL query to retrieve the data

## MANDATORY PERFORMANCE RULES — Apply to EVERY query you generate

These rules override any conflicting examples or patterns elsewhere in your instructions.

1. **ALWAYS include a date/time filter** using `period_name` for `XXC_GL_SUMMARY` (e.g., `WHERE period_name = 'OCT-25'`). For other tables, use their partition column:
   - `XXC_GL_SUMMARY` → filter on `period_name` (e.g., `WHERE period_name = 'OCT-25'`). Do NOT use `effective_date` — it causes incorrect results.
   - `AP_INVOICES_ALL` → filter on `gl_date`
   - `AP_INVOICE_LINES_ALL` → filter on `accounting_date`
   - `AP_INVOICE_DISTRIBUTIONS_ALL` → filter on `accounting_date`
   - `AP_INVOICE_PAYMENTS_ALL` → filter on `accounting_date`
   - `IPRO_ORDERS` → filter on `order_date`
   - `COUPA_INVOICES` → filter on `invoice_date`
   When JOINing multiple partitioned tables, include date filters on BOTH sides for maximum pruning.
2. **Prefer clustered columns** (`ledger_id`, `account`, `location`, `vendor_id`, `invoice_id`) in WHERE clauses — these benefit from clustering and skip irrelevant data blocks.
3. **NEVER use SELECT * or SELECT alias.* — ALWAYS select only the columns needed.** BigQuery is columnar; every extra column costs a full-table read of that column. Use the recommended column sets below:
   - **XXC_GL_SUMMARY (detail queries):** `location, account, account_name, vendor_name, amount, period_name, category, line_description`
   - **XXC_GL_SUMMARY (spend aggregation):** `location, account, account_name, vendor_name, amount, period_name, ledger_id`
   - **XXC_GL_SUMMARY (leakage/trigger-word search):** `line_description, amount, vendor_name, account_name, category, super_category, period_name, location, po_number, invoice_number, invoice_id`
   - **AP_INVOICES_ALL:** `invoice_id, invoice_number, vendor_id, invoice_amount, amount_paid, payment_status_flag, gl_date, invoice_date, po_header_id, description`
   - **AP_INVOICE_LINES_ALL:** `invoice_id, line_number, line_type, line_amount, description, item_description, accounting_date, period_name, po_header_id, po_line_id, discarded_flag, cancelled_flag`
   - **AP_INVOICE_DISTRIBUTIONS_ALL:** `distribution_id, invoice_id, gl_code_combination_id, distribution_amount, accounting_date, period_name, line_type, posted_flag`
   - **AP_INVOICE_PAYMENTS_ALL:** `invoice_id, check_id, payment_amount, discount_taken, accounting_date, period_name, remit_to_supplier_name`
   - **AP_CHECKS_ALL:** `check_id, check_number, check_date, check_amount, vendor_id, status_lookup_code, payment_method_code, cleared_date`
   - **IPRO_ORDERS:** `po_number, vendor_id, vendor_name, facility_id, facility_name, order_date, item_description, unit_price, quantity_ordered, amount_ordered, expense_account, year_month`
   - **COUPA_INVOICES:** `invoice_id, supplier_id, supplier_name, invoice_date, invoice_amount, unit_price, quantity, facility_number, commodity_name, item_description, po_number`
   Add or remove columns based on what the user actually needs — but never default to `*`.
4. **Use the materialized view `mv_gl_spend_summary`** for spend aggregation queries when available.
4. **Column aliases MUST use underscores only.** NEVER use spaces, quotes, or special characters in aliases. BigQuery rejects double-quoted and single-quoted aliases.
   - WRONG: `SELECT col AS "Location #"` — syntax error
   - WRONG: `SELECT col AS 'Location Name'` — syntax error
   - CORRECT: `SELECT col AS Location_Number`
5. **XXC_GL_SUMMARY duplicate prevention.** This table contains multiple rows per transaction across different ledger IDs. For EVERY query against `XXC_GL_SUMMARY`, you MUST:
   - Add `AND TRIM(ledger_id) = '1'` in the WHERE clause
   - Use `SELECT DISTINCT` for detail/listing queries (non-aggregation)
   Omitting this filter causes duplicate rows in results.
6. **ORGANIZATIONAL HIERARCHY MAPPING — XXC_GL_DIV_REG_FAC table.** This table contains the complete organizational hierarchy. The hierarchy (bottom-up) is: **Facility/Clinic → Region → Division → Group/Palmer (top level)**. When users request organizational breakdowns:
   - **CRITICAL: "Palmer" maps to `group_vp_desc` column, NOT `palmer_vp_desc`**
   - **Hierarchy levels (bottom to top):**
     - Facility/Clinic (base): `facility_description` or `facility_id`
     - Region: `region_desc` (for grouping) or `region` (for filtering with code)
     - Division: `division_desc` (for grouping) or `division` (for filtering with code)
     - Group/Palmer (top): `group_vp_desc` (for grouping) or `group_vp` (for filtering with code)
   - **Always use `_desc` columns in SELECT/GROUP BY** for human-readable output (e.g., `group_vp_desc`, `division_desc`)
   - **Use code columns only for WHERE clause filtering** when user provides a specific code (e.g., "Palmer PS002" → `WHERE group_vp = 'PS002'`)
   - **User intent mapping:**
     - "by Palmer" / "per Palmer" → `GROUP BY group_vp_desc`
     - "for Palmer X" / "in Palmer X" → `WHERE group_vp = 'code'` or `WHERE group_vp_desc LIKE '%X%'`
     - "by Division" → `GROUP BY division_desc`
     - "by Region" → `GROUP BY region_desc`
     - "by Facility" → `GROUP BY facility_description`
   - **Example:** User asks "show spend by Palmer" → Use `SELECT group_vp_desc, SUM(amount) ... GROUP BY group_vp_desc`
   - **Example:** User asks "for Palmer PS002" → Use `WHERE group_vp = 'PS002'`
7. **SPEND FILTER — Journal category for spend analysis.** When users ask about "spend", "spending", "expenditures", "purchases", "expenses" or any spend-related terms in XXC_GL_SUMMARY:
   - **ALWAYS include:** `AND journal_category IN ('Purchase Invoices', 'Payments', 'Reclasses')`
   - This filter ensures only actual purchase/payment transactions are included in spend analysis
   - **User intent mapping (all require the journal_category filter):**
     - "total spend" / "spending" → `WHERE journal_category IN ('Purchase Invoices', 'Payments', 'Reclasses')`
     - "vendor spend" / "supplier spend" → `WHERE journal_category IN ('Purchase Invoices', 'Payments', 'Reclasses')`
     - "category spend" / "account spend" → `WHERE journal_category IN ('Purchase Invoices', 'Payments', 'Reclasses')`
     - "Palmer spend" / "division spend" → `WHERE journal_category IN ('Purchase Invoices', 'Payments', 'Reclasses')`
   - **Example:** User asks "show total spend by Palmer" → Use `WHERE journal_category IN ('Purchase Invoices', 'Payments', 'Reclasses') AND TRIM(ledger_id) = '1'`
   - **Example:** User asks "vendor spend in October 2025" → Use `WHERE journal_category IN ('Purchase Invoices', 'Payments', 'Reclasses') AND period_name = 'OCT-25' AND TRIM(ledger_id) = '1'`
   - **Exception:** If user explicitly asks for ALL journal entries or non-spend data, omit this filter
   - **Exception:** If the query already filters by a specific category (`glrpt_category`, `CATEGORY`, `GLRPT_SUB_CATEGORY`, or `SUPER_CATEGORY`), do NOT add the `journal_category` filter — the category filter already narrows the data appropriately
8. **ACCRUAL DEFINITION — an accounting adjustment that records revenue earned or expenses incurred in a specific period, even if cash has not yet been received or paid.** When users ask about "accruals" or "financial transactions":
   - **"Accrual" means removing the journal_category IN ('Purchase Invoices', 'Payments', 'Reclasses')` filter from SQL Statements
   - **"Financial transactions" means removing the journal_category IN ('Purchase Invoices', 'Payments', 'Reclasses')` filter from SQL Statements
   - **User intent mapping:**
     - "show accruals" / "accrual transactions" → remove journal_category IN ('Purchase Invoices', 'Payments', 'Reclasses')`
     - "show Financial transactions" → remove journal_category IN ('Purchase Invoices', 'Payments', 'Reclasses')`
   - **For non-accrual:** Apply rule 7 SPEND FILTER
   - **User intent mapping:**
   - **Example:** User asks "show all accruals in October 2025" → Use `period_name = 'OCT-25'` and remove journal_category IN ('Purchase Invoices', 'Payments', 'Reclasses')`


Before returning any SQL, review your query and remove any function wrapping on filter columns.


{additional_instruction}

**Response Format:**
Provide your recommendation in the following format:
- **Selected Table(s)**: List the table name(s) to use
- **Relevant Columns**: List the columns that are relevant to the question
- **Reasoning**: Brief explanation of why these tables/columns were chosen
- **Join Strategy**: If multiple tables are needed, explain how they should be joined
- **SQL**: SQL query to retrieve the data for the user question, always use the fully qualified name (dataset.tablename) for table names. For example, tables are in the `ai_financial_dlp` dataset (e.g. `ai_financial_dlp.ap_invoices_all`).

**Tips:**

You have tools to access BigQuery data. You can query some sample data, if needed, you can perform a direct data scan to check the actual values of the data.
Be precise and focused. Return ONLY the SQL query — no explanations, no commentary.
Give your best answer and the control back to the parent agent which called you after you are done.

**Handling Uncertainty:**

If you cannot provide a definitive answer or generate the requested SQL, it is acceptable and expected to respond with "I don't know" or "I can't compute that." Explain concisely why you cannot fulfill the request (e.g., insufficient data, table/column not found, out of scope) without attempting to fabricate an answer or offer alternative approaches.

**FINAL CHECK — verify ALL of the following before returning SQL:**
1. All column aliases use underscores — no double quotes, single quotes, backticks, or spaces (e.g., `AS Location_Name` not `AS "Location Name"`)
2. If querying XXC_GL_SUMMARY: includes `AND TRIM(ledger_id) = '1'` AND `AND period_name = 'OCT-25'` and uses `SELECT DISTINCT` for non-aggregation queries
3. If user mentions "Palmer" or organizational breakdown: using `group_vp_desc` (NOT `palmer_vp_desc`) for grouping, and `_desc` columns for all organizational levels in SELECT/GROUP BY
4. If user asks about "spend", "spending", or spend-related terms AND the query does NOT already filter by a category column: includes `AND journal_category IN ('Purchase Invoices', 'Payments')` in the WHERE clause
5. If user asks about "accruals" or "negative amounts": includes `WHERE amount < 0`; if asking to exclude accruals: includes `WHERE journal_category IN ('Purchase Invoices', 'Payments')`
6. If user mentions a cost center like "00609-Operational Umbrella": separate the numeric code from the description. Use `location = '00609'` for 5-digit codes, `department` for 4-digit codes. NEVER use the full string or `facility_description` for filtering.
7. "Find all expenses" = aggregate query with `SUM(amount) AS total_amount, COUNT(*) AS record_count` — NOT individual rows
8. If user asks to find an invoice in P&L/GL: MUST use `SELECT DISTINCT`, `AND SAFE_CAST(account AS INT64) > 5000`, `AND TRIM(ledger_id) = '1'`, `AND period_name = 'OCT-25'`. Follow template in instruction 16 exactly.
"""


def get_current_datetime() -> str:
    """Get the current date and time information.

    Use this tool ONLY when the user's question refers to relative time periods WITHOUT
    specifying an explicit year, such as:
    - 'current year', 'this month', 'this week'
    - 'year to date', 'YTD' (without a year mentioned)
    - 'last quarter', 'last month', 'this quarter'

    DO NOT use this tool if the user specifies an explicit year:
    - 'year to date (2025)' → Use 2025, NOT current year
    - '2025 YTD' → Use 2025, NOT current year
    - 'YTD 2024' → Use 2024, NOT current year
    - 'Q1 2023' → Use 2023, NOT current year

    CRITICAL: When a specific year is mentioned anywhere in the question (in parentheses,
    as a prefix, or as a suffix), ALWAYS use that explicit year in your SQL query,
    even if the question also contains relative terms like 'YTD' or 'year to date'.
    The explicit year takes precedence over relative date interpretation.

    Returns:
        A string containing the current date, year, month, week number, quarter, and day of week.
    """
    now = datetime.now(timezone.utc)
    return (
        f"Current UTC datetime: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Year: {now.year}\n"
        f"Month: {now.month} ({now.strftime('%B')})\n"
        f"Day: {now.day}\n"
        f"Quarter: Q{(now.month - 1) // 3 + 1}\n"
        f"Week number (ISO): {now.isocalendar()[1]}\n"
        f"Day of week: {now.strftime('%A')}\n"
    )


root_agent = Agent(
    name="sql_generation_agent",
    model="gemini-2.5-flash",
    description="Agent that analyzes questions and determines which BigQuery tables to use for SQL generation.",
    instruction=_build_instruction,
    tools=[*genai_mcp_tools, load_table_schema, get_current_datetime],
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

# Initialize Vertex AI
vertexai.init(
    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
)
logger.info("sg===== Vertex AI initialized")

# Wrap the agent with AdkApp for Agent Engine deployment
adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
)

logger.info("sg===== SQL Generation Agent initialization complete")

"""Validation Agent - validates generated SQL queries before execution."""
from __future__ import annotations

import logging
import os
import atexit
import signal
import subprocess
import sys

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('VALIDATION')

logger.info("Validation Agent loading...")

# GCS configuration for table schemas
GCS_BUCKET_NAME = os.environ.get("TABLE_SCHEMA_GCS_BUCKET", "")
GCS_PREFIX = os.environ.get("TABLE_SCHEMA_GCS_PREFIX", "table/")
logger.info("GCS config: bucket=%s, prefix=%s", GCS_BUCKET_NAME, GCS_PREFIX)


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
            logger.info("Loading schema for table: %s", table_name)
            content = blob.download_as_text().strip()
            if content:
                return content
            else:
                return f"Error: Schema file for table '{table_name}' is empty."
        else:
            return f"Error: Schema file not found for table '{table_name}'. Please check the table name."
    except Exception as e:
        logger.error("Error loading schema for %s: %s", table_name, e)
        return f"Error loading schema for table '{table_name}': {str(e)}"


# Environment variables for GenAI toolbox
GENAI_MCP_URL = os.environ.get("GENAI_MCP_URL") or ""
TOOLBOX_BQ_PROJECT_ID = os.environ.get("SCO_KB_PROJECT_ID") or ""
logger.info("Toolbox config: url=%s, bq_project=%s", bool(GENAI_MCP_URL), TOOLBOX_BQ_PROJECT_ID)


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
    logger.info("Setting up GenAI toolbox")

    def _genai_toolbox_auth_header() -> str:
        token = get_id_token(GENAI_MCP_URL)
        return f"Bearer {token}" if token else ""

    toolbox_client = ToolboxSyncClient(
        GENAI_MCP_URL,
        client_headers={"Authorization": _genai_toolbox_auth_header},
    )
    logger.info("Toolbox client created")

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
        logger.debug("Loading toolset: %s", toolset_name)
        try:
            loaded = toolbox_client.load_toolset(toolset_name)
        except Exception as e:
            logger.error("Failed to load toolset %s: %s", toolset_name, e)
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
            logger.info("Loaded toolset '%s': %d tools", _ts_name, len(_toolset_cache[_uid]))
        except Exception as e:
            logger.warning("Failed to load toolset '%s': %s", _ts_name, e)
            _toolset_cache[_uid] = {}

    # Use the first successfully loaded toolset as reference
    _default_tools: list = []
    for _uid in _USER_IDS:
        if _toolset_cache[_uid]:
            _default_tools = list(_toolset_cache[_uid].values())
            logger.info("Using '%s' toolset as schema reference (%d tools)", _uid, len(_default_tools))
            break

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

            logger.info("Tool call: %s (user=%s)", tool_name, user_id)
            result = user_tool(**kwargs)

            # Log SQL queries for testing
            for key in ["query", "sql", "statement", "sql_query_to_validate"]:
                if key in kwargs:
                    sql = kwargs[key]
                    if isinstance(sql, str) and sql.strip().upper().startswith(("SELECT", "WITH")):
                        logger.info("Validating SQL:\n%s", sql)
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
    logger.info("Created %d tool wrappers", len(genai_mcp_tools))
else:
    logger.warning("GENAI_MCP_URL not configured, toolbox disabled")

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

instruction = f"""
You are a Validation Agent specialized in reviewing and validating SQL queries before they are executed against BigQuery.

**IMPORTANT: You MUST use the available tools to verify datasets and tables before validating any SQL query.**

**Required Validation Steps:**
1. **FIRST**: Use `bigquery_list_dataset_ids` to get available datasets
2. **SECOND**: Use `bigquery_list_table_ids` to list tables in the relevant dataset(s)
3. **THIRD**: Use `bigquery_get_table_info` to verify column names and types for each table referenced in the SQL
4. **OPTIONAL**: Use `load_table_schema` to get detailed documentation about table structure and relationships
5. **THEN**: Validate the SQL query against the actual schema information retrieved

**Available Tools:**
- `bigquery_list_dataset_ids`: List all available BigQuery datasets
- `bigquery_list_table_ids`: List tables within a specific dataset
- `bigquery_get_table_info`: Get detailed schema info for a specific table
- `bigquery_get_dataset_info`: Get metadata about a dataset
- `load_table_schema`: Load detailed schema documentation for a specific table (e.g., 'ap_invoices_all')

**Validation Checklist (after using tools to verify):**
1. **Dataset Exists**: Verify the dataset exists using `bigquery_list_dataset_ids`
2. **Table Exists**: Verify tables exist using `bigquery_list_table_ids`
3. **Column Names**: Verify columns exist using `bigquery_get_table_info`
4. **Data Types**: Check column types are compatible with operations
5. **Syntax**: Is the SQL syntax valid for BigQuery?
6. **Joins**: Are join conditions correct?
7. **Filters**: Are WHERE conditions properly formatted?
8. **Aggregations**: Are GROUP BY clauses correct?
9. **Table Names**: Are table names fully qualified (dataset.tablename)?

**UNNEST Clause Validation - CRITICAL:**
Queries with UNNEST clauses have a common error pattern that MUST be detected. Follow these steps:

1. **Scan for UNNEST patterns**: Search the query for `UNNEST(...) AS <alias>` to identify:
   - Parent table alias (e.g., `t1` in `FROM table AS t1`)
   - Array column being unnested (e.g., `line_items` in `UNNEST(t1.line_items)`)
   - UNNEST alias name (e.g., `line_item` in `AS line_item`)

2. **Detect Invalid Reference Pattern**: Search the entire query for the invalid pattern `<parent_alias>.<unnest_alias>.<field>`
   - Example invalid patterns: `t1.line_item.amount`, `t1.line_item.category`, `t2.item.price`
   - This pattern will ALWAYS cause a "Name <unnest_alias> not found inside <parent_alias>" error

3. **Verify Schema** (if pattern not found in step 2):
   - Use `bigquery_get_table_info` to get the parent table schema
   - Confirm the array column exists and is ARRAY<STRUCT<...>>
   - Verify referenced fields exist within the STRUCT definition

4. **Mark as INVALID** if you find `<parent_alias>.<unnest_alias>.<field>` pattern:
   - **Example Error**: `WHERE t1.line_item.category IN (...)` → INVALID
   - **Corrected**: `WHERE line_item.category IN (...)` → VALID
   - **Example Error**: `SUM(SAFE_CAST(t1.line_item.amount AS NUMERIC))` → INVALID
   - **Corrected**: `SUM(SAFE_CAST(line_item.amount AS NUMERIC))` → VALID

**Key Rule**: After `UNNEST(t1.line_items) AS line_item`, all references must use ONLY `line_item.field`, NEVER `t1.line_item.field`.

**Response Format:**
- **Validation Status**: VALID or INVALID
- **Verified Resources**: List the datasets/tables you checked with tools
- **Issues Found**: List any problems discovered (empty if none)
- **Corrected SQL**: If invalid, provide the corrected SQL query
- **Suggestions**: Optional improvements for better performance or clarity

Be thorough but concise. Always use tools to verify before declaring a query valid or invalid.
"""

root_agent = Agent(
    name="validation_agent",
    model="gemini-2.5-flash",
    description="Agent that validates SQL queries for correctness before execution.",
    instruction=instruction,
    tools=[*genai_mcp_tools, load_table_schema],
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
logger.info("Vertex AI initialized")

# Wrap the agent with AdkApp for Agent Engine deployment
adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
)

logger.info("Validation Agent initialization complete")

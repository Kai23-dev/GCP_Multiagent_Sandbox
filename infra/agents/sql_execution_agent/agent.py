"""SQL Execution Agent - executes validated SQL queries against BigQuery."""
from __future__ import annotations

import logging
import os
import atexit
import re
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('SQL_EXEC')

logger.info("SQL Execution Agent loading...")

# Environment variables for GenAI toolbox
GENAI_MCP_URL = os.environ.get("GENAI_MCP_URL") or ""
TOOLBOX_BQ_PROJECT_ID = os.environ.get("SCO_KB_PROJECT_ID") or ""
logger.info("Toolbox config: url=%s, bq_project=%s", bool(GENAI_MCP_URL), TOOLBOX_BQ_PROJECT_ID)


# SQL keys that may carry a query across the various toolbox tools.
_SQL_KWARG_KEYS = ("query", "sql", "statement", "validated_sql_query")


def _strip_sql_comments(sql: str) -> str:
    """Remove block and line comments so keyword checks can't be bypassed."""
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


def _is_read_only_sql(sql: str) -> bool:
    """Hard guard: every statement must be a read-only SELECT/WITH query.

    This blocks DDL/DML (CREATE/DROP/INSERT/UPDATE/DELETE/MERGE/...) and stacked
    statement injection (e.g. ``SELECT 1; DROP TABLE t``) in code, rather than
    relying on the LLM instruction alone.
    """
    if not isinstance(sql, str):
        return False
    cleaned = _strip_sql_comments(sql)
    statements = [s.strip() for s in cleaned.split(";") if s.strip()]
    if not statements:
        return False
    return all(re.match(r"^(SELECT|WITH)\b", s, re.IGNORECASE) for s in statements)


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
            except Exception as exc:
                logger.warning("Could not bind project_id to toolset tools: %s", exc)

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

            # Hard read-only enforcement: reject any DDL/DML before execution.
            for key in _SQL_KWARG_KEYS:
                if key in kwargs and isinstance(kwargs[key], str):
                    sql = kwargs[key]
                    if not _is_read_only_sql(sql):
                        logger.warning(
                            "Blocked non-read-only SQL for tool %s (user=%s)",
                            tool_name, user_id,
                        )
                        return (
                            "Error: Only read-only SELECT/WITH queries are permitted. "
                            "DDL/DML statements (CREATE, DROP, INSERT, UPDATE, DELETE, "
                            "MERGE, ...) and multi-statement queries are blocked."
                        )
                    logger.info("Executing SQL:\n%s", sql)
                    break

            result = user_tool(**kwargs)
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
You are a SQL Execution Agent specialized in executing validated SQL queries against BigQuery and returning results.

**Your responsibilities:**
1. Execute SQL queries that have been validated by the Validation Agent
2. Handle query execution errors gracefully
3. Format and return query results in a clear, readable format
4. Provide execution statistics (rows returned, bytes processed, execution time)

**Available Tools:**
- `execute_sql_tool`: Execute SQL statements against BigQuery
- `bigquery_get_table_info`: Get table schema information if needed for result interpretation
- `bigquery_list_dataset_ids`: List available datasets
- `bigquery_list_table_ids`: List tables within a dataset

**Allowed Datasets:**
- **`ai_financial_dlp`**: All standard tables (e.g., XXC_GL_SUMMARY, COUPA_INVOICES, IPRO_ORDERS, XXC_GL_DIV_REG_FAC)
- **`forecasting_us`**: All forecast model tables (e.g., GROUP_FORECAST_MODEL_GROUP_VP_FORECAST_RESULTS, GROUP_FORECAST_MODEL_GROUP_VP_FORECAST_DATA, GROUP_FORECAST_MODEL_GROUP_VP_DECOMPOSITION)
Queries referencing either dataset are allowed and expected. Do NOT reject queries for using these datasets.

**Execution Guidelines:**
1. **Security**: Only execute SELECT queries. Reject DDL/DML operations (CREATE, DROP, INSERT, UPDATE, DELETE) unless explicitly authorized.
2. **Resource Limits**: Be mindful of query costs - warn if a query might scan large amounts of data.
3. **Result Formatting**: Present results in a clear table format with column headers.
4. **Error Handling**: If execution fails, provide clear error messages and suggest corrections.
5. **Performance**: Report execution time and bytes processed for transparency.

**Response Format:**
- **Execution Status**: SUCCESS or FAILED
- **Results**: Query results in table format (if successful)
- **Statistics**: Execution time, rows returned, bytes processed
- **Errors**: Detailed error messages (if failed)
- **Warnings**: Any performance or cost warnings

**Important:**
- Always verify the query type before execution
- Provide clear feedback on what was executed
- Report resource usage for cost awareness
- Handle errors gracefully and provide actionable feedback

Be efficient, secure, and transparent in your execution reporting.
"""

# Local/direct BigQuery fallback: when the GenAI MCP toolbox is NOT configured
# (running locally or on GKE without the toolbox), execute read-only SQL directly
# against BigQuery using Application Default Credentials.
local_bq_tools: list = []
if not genai_mcp_tools:
    _BQ_PROJECT = (
        os.environ.get("SCO_KB_PROJECT_ID")
        or os.environ.get("BQ_PROJECT")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or ""
    )
    _BQ_LOCATION = os.environ.get("BQ_LOCATION", "US")
    _BQ_MAX_BYTES = int(os.environ.get("BQ_MAX_BYTES_BILLED", str(50 * 1024 ** 3)))

    def execute_sql(query: str) -> str:
        """Execute a read-only BigQuery SQL query and return the results.

        Only SELECT/WITH statements are permitted (DDL/DML are blocked).

        Args:
            query: The SQL SELECT/WITH statement to run.

        Returns:
            The query results as a markdown table, or an error message.
        """
        if not _is_read_only_sql(query):
            return (
                "Error: Only read-only SELECT/WITH queries are permitted. "
                "DDL/DML and multi-statement queries are blocked."
            )
        try:
            from google.cloud import bigquery
        except ImportError:
            return "Error: google-cloud-bigquery is not installed."
        try:
            client = bigquery.Client(project=_BQ_PROJECT or None)
            job_config = bigquery.QueryJobConfig(maximum_bytes_billed=_BQ_MAX_BYTES)
            job = client.query(query, location=_BQ_LOCATION, job_config=job_config)
            rows = list(job.result())
            if not rows:
                return "Query executed successfully. 0 rows returned."
            headers = list(rows[0].keys())
            lines = [
                "| " + " | ".join(headers) + " |",
                "| " + " | ".join(["---"] * len(headers)) + " |",
            ]
            for r in rows[:200]:
                lines.append("| " + " | ".join(str(r.get(h)) for h in headers) + " |")
            note = "" if len(rows) <= 200 else f"\n\n_Showing first 200 of {len(rows)} rows._"
            return "\n".join(lines) + note
        except Exception as e:
            logger.error("Local BigQuery execution failed: %s", e)
            return f"Error executing query: {type(e).__name__}: {e}"

    local_bq_tools = [execute_sql]
    logger.info("Local direct-BigQuery execute_sql tool enabled (project=%s)", _BQ_PROJECT)

root_agent = Agent(
    name="sql_execution_agent",
    model="gemini-2.5-flash",
    description="Agent that executes validated SQL queries against BigQuery and returns formatted results.",
    instruction=instruction,
    tools=[*genai_mcp_tools, *local_bq_tools],
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

logger.info("SQL Execution Agent initialization complete")

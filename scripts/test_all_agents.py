"""
test_all_agents.py
==================
A standalone script to test ALL deployed agents on Vertex AI Agent Engine.

Run this on your COMPANY LAPTOP after deploying agents.

Usage:
    # Basic — test all agents whose IDs are in deployed_agents_state.json
    python scripts/test_all_agents.py

    # Test a single agent by key name
    python scripts/test_all_agents.py --agent spend_iq_agent

    # Test a single agent by its raw resource name
    python scripts/test_all_agents.py --resource "projects/.../reasoningEngines/ID"

    # List all agents defined in this script (with their test queries)
    python scripts/test_all_agents.py --list

    # Save results to a file (good for showing your manager)
    python scripts/test_all_agents.py --save-report

Prerequisites:
    pip install google-cloud-aiplatform[agent-engines] google-auth
    gcloud auth application-default login
    Set: GOOGLE_CLOUD_PROJECT=gp-ct-sbox-con-sbp0i2-eyenterp
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_agents")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "gp-ct-sbox-con-sbp0i2-eyenterp")
LOCATION   = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
STATE_FILE = "deployed_agents_state.json"   # written by deploy_agents.py

# ─────────────────────────────────────────────────────────────────────────────
# AGENT TEST DEFINITIONS
# Each entry has:
#   key         - matches the key in deployed_agents_state.json
#   name        - human-readable display name
#   description - what this agent does
#   test_query  - the question we send to verify it works
#   expect      - keywords we look for in the response to confirm it worked
# ─────────────────────────────────────────────────────────────────────────────

AGENTS = [
    {
        "key":         "sql_generation_agent",
        "name":        "SQL Generation Agent",
        "description": "Selects the right BigQuery tables and writes optimised SQL",
        "test_query":  (
            "Generate a BigQuery SQL query to find the top 5 vendors by total spend "
            "from the XXC_GL_SUMMARY table in the ai_financial_dlp dataset."
        ),
        "expect": ["SELECT", "vendor_name", "SUM", "amount"],
    },
    {
        "key":         "validation_agent",
        "name":        "SQL Validation Agent",
        "description": "Reviews generated SQL and flags any issues before execution",
        "test_query":  (
            "Please validate this SQL query and tell me if it is correct:\n"
            "SELECT vendor_name, SUM(amount) AS total_spend "
            "FROM `gp-ct-sbox-con-sbp0i2-eyenterp.ai_financial_dlp.XXC_GL_SUMMARY` "
            "GROUP BY vendor_name ORDER BY total_spend DESC LIMIT 10"
        ),
        "expect": ["valid", "SQL", "query"],
    },
    {
        "key":         "sql_execution_agent",
        "name":        "SQL Execution Agent",
        "description": "Runs validated SQL against BigQuery and returns results",
        "test_query":  (
            "Execute this SQL query and return the results:\n"
            "SELECT COUNT(*) AS row_count "
            "FROM `gp-ct-sbox-con-sbp0i2-eyenterp.ai_financial_dlp.XXC_GL_SUMMARY`"
        ),
        "expect": ["row_count", "result", "count"],
    },
    {
        "key":         "auditor_agent",
        "name":        "Auditor Agent",
        "description": "Audit & compliance analysis — finds anomalies and policy violations",
        "test_query":  (
            "Perform an audit analysis on the supplier spend data. "
            "Are there any duplicate payments, missing PO numbers on large invoices, "
            "or unusual spend patterns that would be flagged in an audit? "
            "Use the ai_financial_dlp dataset."
        ),
        "expect": ["audit", "spend", "vendor", "invoice", "PO"],
    },
    {
        "key":         "buyer_agent",
        "name":        "Buyer Agent",
        "description": "Procurement & purchasing analysis — buying behaviour and PO compliance",
        "test_query":  (
            "Analyse the purchasing data and tell me: "
            "Which categories have the highest spend? "
            "Are there any purchases made without a PO number? "
            "Summarise key procurement insights from the ai_financial_dlp dataset."
        ),
        "expect": ["category", "spend", "purchase", "procurement"],
    },
    {
        "key":         "trend_agent",
        "name":        "Trend Agent",
        "description": "Spend trend analysis over time periods and categories",
        "test_query":  (
            "Analyse the spend trends from the XXC_GL_SUMMARY table. "
            "Which categories or vendors have seen the most significant changes in spend "
            "across different time periods? Provide a trend summary."
        ),
        "expect": ["trend", "spend", "period", "category", "vendor"],
    },
    {
        "key":         "supplier_classification_agent",
        "name":        "Supplier Classification Agent",
        "description": "Categorises suppliers by type, risk, and spend tier",
        "test_query":  (
            "Classify the top suppliers from the AP_SUPPLIERS table. "
            "Group them by vendor type and spend tier. "
            "Which suppliers would be considered strategic vs. tail spend?"
        ),
        "expect": ["supplier", "vendor", "classify", "category", "tier"],
    },
    {
        "key":         "financial_leakage_agent",
        "name":        "Financial Leakage Agent",
        "description": "Identifies unapproved spend, contract deviations, and leakage risks",
        "test_query":  (
            "Identify any financial leakage risks in the spend data. "
            "Look for transactions without PO numbers, unusually high amounts, "
            "or spending in suspicious categories that might indicate financial leakage. "
            "Use the ai_financial_dlp dataset."
        ),
        "expect": ["leakage", "risk", "spend", "PO", "transaction"],
    },
    {
        "key":         "contract_intelligence_agent",
        "name":        "Contract Intelligence Agent",
        "description": "Analyses contract compliance and invoice vs. contract deviations",
        "test_query":  (
            "Analyse the procurement data for contract compliance issues. "
            "Are there vendors being paid outside of standard contract terms? "
            "Flag any invoices that appear to deviate from expected contract pricing."
        ),
        "expect": ["contract", "compliance", "invoice", "vendor", "payment"],
    },
    {
        "key":         "spend_iq_agent",
        "name":        "Spend IQ Agent (Orchestrator)",
        "description": "Master orchestrator — routes queries to the right specialist agent",
        "test_query":  (
            "Give me a comprehensive overview of our supplier spend situation. "
            "Include: top vendors by spend, any audit concerns, current spend trends, "
            "and highlight any financial leakage risks you can identify."
        ),
        "expect": ["vendor", "spend", "audit", "trend"],
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    """Load deployed agent resource names from the state file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def resource_name(agent_id: str) -> str:
    """Build the full Vertex AI resource name from a numeric agent ID."""
    return f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{agent_id}"


def parse_agent_response(raw_response) -> str:
    """Extract text from whatever stream_query returns."""
    texts = []

    # Handle if it's already a string
    if isinstance(raw_response, str):
        return raw_response.strip()

    # Handle iterable (streaming)
    try:
        for chunk in raw_response:
            if isinstance(chunk, str):
                texts.append(chunk)
            elif isinstance(chunk, dict):
                # Try various paths where text might live
                output = chunk.get("output", chunk)
                if isinstance(output, dict):
                    content = output.get("content", {})
                    if isinstance(content, dict):
                        for part in content.get("parts", []):
                            if isinstance(part, dict) and "text" in part:
                                texts.append(part["text"])
                    elif isinstance(content, str):
                        texts.append(content)
                elif isinstance(output, str):
                    texts.append(output)
    except Exception as e:
        return f"[parse error: {e}]"

    return "\n".join(texts).strip() or "[empty response]"


def check_keywords(response: str, keywords: list[str]) -> tuple[bool, list[str]]:
    """Check if any expected keywords appear in the response (case-insensitive)."""
    found    = [k for k in keywords if k.lower() in response.lower()]
    missing  = [k for k in keywords if k.lower() not in response.lower()]
    passed   = len(found) > 0   # at least one keyword must appear
    return passed, found


def print_banner(text: str, char: str = "=", width: int = 65) -> None:
    print("\n" + char * width)
    print(f"  {text}")
    print(char * width)


def print_section(label: str, value: str, indent: int = 2) -> None:
    pad = " " * indent
    print(f"\n{pad}📌 {label}:")
    for line in value.strip().splitlines():
        print(f"{pad}   {line}")


# ─────────────────────────────────────────────────────────────────────────────
# CORE TEST FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def test_agent(agent_def: dict, agent_resource: str) -> dict:
    """
    Test a single deployed agent.
    Returns a result dict with keys: name, resource, passed, response, duration_s, error
    """
    import vertexai

    name        = agent_def["name"]
    test_query  = agent_def["test_query"]
    expect      = agent_def.get("expect", [])

    print_banner(f"Testing: {name}", char="-")
    print(f"  Resource : {agent_resource}")
    print(f"  Query    : {test_query[:120]}{'...' if len(test_query) > 120 else ''}")
    print()

    result = {
        "name":        name,
        "key":         agent_def["key"],
        "resource":    agent_resource,
        "passed":      False,
        "response":    "",
        "duration_s":  0.0,
        "error":       "",
        "keywords_found": [],
    }

    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        agent = vertexai.agent_engines.get(agent_resource)

        logger.info("Sending query to %s ...", name)
        start = time.time()

        raw = agent.stream_query(
            message=test_query,
            user_id="sandbox-validation-test",
        )

        response_text = parse_agent_response(raw)
        duration = round(time.time() - start, 1)

        result["response"]   = response_text
        result["duration_s"] = duration

        # Keyword check
        passed, found = check_keywords(response_text, expect)
        result["passed"]         = passed
        result["keywords_found"] = found

        status = "✅ PASSED" if passed else "⚠️  RESPONDED (no expected keywords found)"
        print(f"  Status   : {status}  ({duration}s)")
        print(f"  Keywords : found {found} out of {expect}")
        print_section("Response preview", response_text[:600] + ("..." if len(response_text) > 600 else ""))

    except Exception as e:
        result["error"] = str(e)
        result["passed"] = False
        import traceback
        err_detail = traceback.format_exc()
        print(f"  Status   : ❌ ERROR")
        print(f"  Error    : {e}")
        logger.debug("Full traceback:\n%s", err_detail)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────────────────────────────────────

def save_report(results: list[dict]) -> str:
    """Save test results to a timestamped markdown file."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"docs/agent_test_report_{ts}.md"
    os.makedirs("docs", exist_ok=True)

    lines = [
        "# Agent Validation Test Report",
        "",
        f"**Project:** `{PROJECT_ID}`",
        f"**Location:** `{LOCATION}`",
        f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Agent | Status | Duration | Keywords Found |",
        "|---|---|---|---|",
    ]

    for r in results:
        if r.get("error"):
            status = "❌ Error"
        elif r["passed"]:
            status = "✅ Passed"
        else:
            status = "⚠️ Responded"

        duration = f"{r['duration_s']}s" if r['duration_s'] else "—"
        keywords = ", ".join(r.get("keywords_found", [])) or "—"
        lines.append(f"| {r['name']} | {status} | {duration} | {keywords} |")

    passed  = sum(1 for r in results if r["passed"] and not r.get("error"))
    errored = sum(1 for r in results if r.get("error"))
    total   = len(results)

    lines += [
        "",
        f"**Total:** {total} agents tested | **Passed:** {passed} | **Errors:** {errored}",
        "",
        "---",
        "",
        "## Detailed Results",
        "",
    ]

    for r in results:
        lines.append(f"### {r['name']}")
        lines.append("")
        lines.append(f"- **Resource:** `{r['resource']}`")
        lines.append(f"- **Duration:** {r['duration_s']}s")
        if r.get("error"):
            lines.append(f"- **Status:** ❌ Error — `{r['error']}`")
        else:
            status = "✅ Passed" if r["passed"] else "⚠️ Responded (no keyword match)"
            lines.append(f"- **Status:** {status}")
            lines.append(f"- **Keywords found:** {r.get('keywords_found', [])}")
            lines.append("")
            lines.append("**Response:**")
            lines.append("")
            lines.append("```")
            lines.append(r["response"][:1500])
            if len(r["response"]) > 1500:
                lines.append("... [truncated]")
            lines.append("```")
        lines.append("")

    content = "\n".join(lines)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return filename


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test all deployed SCO agents on Vertex AI Agent Engine"
    )
    parser.add_argument(
        "--agent",
        metavar="KEY",
        help="Test only a specific agent by key name (e.g. auditor_agent)",
    )
    parser.add_argument(
        "--resource",
        metavar="RESOURCE_NAME",
        help="Test a specific agent by full resource name",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all agent definitions with their test queries",
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save results to docs/agent_test_report_<timestamp>.md",
    )
    args = parser.parse_args()

    # ── List mode ─────────────────────────────────────────────────────────
    if args.list:
        print_banner("Defined Agent Tests")
        for i, a in enumerate(AGENTS, 1):
            print(f"\n  {i:2}. {a['name']} ({a['key']})")
            print(f"       {a['description']}")
            print(f"       Query: {a['test_query'][:100]}...")
        return

    # ── Check project ──────────────────────────────────────────────────────
    if not PROJECT_ID:
        logger.error(
            "GOOGLE_CLOUD_PROJECT is not set.\n"
            "  PowerShell: $env:GOOGLE_CLOUD_PROJECT = 'gp-ct-sbox-con-sbp0i2-eyenterp'"
        )
        sys.exit(1)

    # ── Load deployment state ──────────────────────────────────────────────
    state = load_state()

    # ── Single resource mode ───────────────────────────────────────────────
    if args.resource:
        # Find the matching agent definition if possible
        agent_def = next(
            (a for a in AGENTS if a["key"] in args.resource), AGENTS[-1]
        )
        result = test_agent(agent_def, args.resource)
        if args.save_report:
            path = save_report([result])
            print(f"\n📄 Report saved to: {path}")
        return

    # ── Single agent key mode ──────────────────────────────────────────────
    if args.agent:
        agent_def = next((a for a in AGENTS if a["key"] == args.agent), None)
        if not agent_def:
            logger.error("Unknown agent key: %s. Use --list to see valid keys.", args.agent)
            sys.exit(1)
        if args.agent not in state:
            logger.error(
                "Agent '%s' not found in %s.\n"
                "Run deploy_agents.py first, or use --resource to specify the resource name directly.",
                args.agent, STATE_FILE
            )
            sys.exit(1)
        resource = state[args.agent]
        result = test_agent(agent_def, resource)
        if args.save_report:
            path = save_report([result])
            print(f"\n📄 Report saved to: {path}")
        return

    # ── Test ALL agents in state file ──────────────────────────────────────
    print_banner(f"SCO Agent Validation — Project: {PROJECT_ID}")
    print(f"\n  State file : {STATE_FILE}")
    print(f"  Agents in state : {list(state.keys()) or 'none (run deploy_agents.py first)'}")

    if not state:
        logger.error(
            "\nNo deployed agents found in %s.\n"
            "Run: python scripts/deploy_agents.py\n"
            "Or use: python scripts/test_all_agents.py --resource 'projects/.../reasoningEngines/ID'",
            STATE_FILE
        )
        sys.exit(1)

    results   = []
    skipped   = []

    for agent_def in AGENTS:
        key = agent_def["key"]
        if key not in state:
            skipped.append(agent_def["name"])
            print(f"\n  ⏭  Skipping {agent_def['name']} — not found in state file")
            continue

        result = test_agent(agent_def, state[key])
        results.append(result)

        # Small pause between agents to avoid rate-limit bursts
        time.sleep(2)

    # ── Print final summary ────────────────────────────────────────────────
    print_banner("TEST SUMMARY")

    passed  = sum(1 for r in results if r["passed"] and not r.get("error"))
    errored = sum(1 for r in results if r.get("error"))
    total   = len(results)

    for r in results:
        if r.get("error"):
            icon = "❌"
        elif r["passed"]:
            icon = "✅"
        else:
            icon = "⚠️ "
        print(f"  {icon}  {r['name']:<45} ({r['duration_s']}s)")

    if skipped:
        for name in skipped:
            print(f"  ⏭   {name:<45} (not deployed)")

    print()
    print(f"  Results: {passed}/{total} passed  |  {errored} errors  |  {len(skipped)} skipped")
    print()

    if args.save_report:
        path = save_report(results)
        print(f"  📄 Full report saved to: {path}")
        print(f"     → Commit and push this file to show your manager!\n")

    if errored > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

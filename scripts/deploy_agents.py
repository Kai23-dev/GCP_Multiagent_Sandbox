"""
deploy_agents.py
================
Step-by-step script to deploy ALL agents to Vertex AI Agent Engine (Reasoning Engine).
Run this on your company laptop where you have GCP sandbox access.

Usage:
    # Set environment variables first:
    #   Windows PowerShell:
    #   $env:GOOGLE_CLOUD_PROJECT = "your-project-id"
    #   $env:GOOGLE_CLOUD_LOCATION = "us-central1"   # optional, defaults to us-central1

    python scripts/deploy_agents.py

    # To deploy only a specific agent (useful for re-deploying one agent):
    python scripts/deploy_agents.py --agent auditor

    # To test an already deployed agent:
    python scripts/deploy_agents.py --test --resource-name "projects/xxx/locations/us-central1/reasoningEngines/yyy"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("deploy_agents")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION — Edit these if needed
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
# Staging bucket will be auto-created if it doesn't exist
STAGING_BUCKET = os.environ.get(
    "AGENT_STAGING_BUCKET", f"gs://{PROJECT_ID}-agent-staging"
)

# Deployment order matters! Sub-agents must come before their orchestrators.
AGENT_DEPLOY_ORDER = [
    "sql_generation_agent",
    "validation_agent",
    "sql_execution_agent",
    "auditor_agent",
    "buyer_agent",
    "trend_agent",
    "supplier_classification_agent",
    "financial_leakage_agent",
    "spend_iq_agent",   # Orchestrator — must be LAST
]

# Friendly display names for each agent
AGENT_DISPLAY_NAMES = {
    "sql_generation_agent":          "SQL Generation Agent",
    "validation_agent":              "SQL Validation Agent",
    "sql_execution_agent":           "SQL Execution Agent",
    "auditor_agent":                 "Auditor Agent",
    "buyer_agent":                   "Buyer Agent",
    "trend_agent":                   "Trend Agent",
    "supplier_classification_agent": "Supplier Classification Agent",
    "financial_leakage_agent":       "Financial Leakage Agent",
    "spend_iq_agent":                "SpendIQ Orchestrator Agent",
}

# Environment variables each agent needs from previously deployed agents
# Format: { agent_key: { env_var_name: "other_agent_key" } }
AGENT_ENV_DEPS = {
    "auditor_agent": {
        "SQL_GENERATION_AGENT_RESOURCE": "sql_generation_agent",
        "VALIDATION_AGENT_RESOURCE":     "validation_agent",
        "SQL_EXECUTION_AGENT_RESOURCE":  "sql_execution_agent",
    },
    "buyer_agent": {
        "SQL_GENERATION_AGENT_RESOURCE": "sql_generation_agent",
        "VALIDATION_AGENT_RESOURCE":     "validation_agent",
        "SQL_EXECUTION_AGENT_RESOURCE":  "sql_execution_agent",
    },
    "trend_agent": {
        "SQL_GENERATION_AGENT_RESOURCE": "sql_generation_agent",
        "VALIDATION_AGENT_RESOURCE":     "validation_agent",
        "SQL_EXECUTION_AGENT_RESOURCE":  "sql_execution_agent",
    },
    "supplier_classification_agent": {
        "SQL_GENERATION_AGENT_RESOURCE": "sql_generation_agent",
        "VALIDATION_AGENT_RESOURCE":     "validation_agent",
        "SQL_EXECUTION_AGENT_RESOURCE":  "sql_execution_agent",
    },
    "financial_leakage_agent": {
        "SQL_GENERATION_AGENT_RESOURCE": "sql_generation_agent",
        "VALIDATION_AGENT_RESOURCE":     "validation_agent",
        "SQL_EXECUTION_AGENT_RESOURCE":  "sql_execution_agent",
    },
    "spend_iq_agent": {
        "AUDITOR_AGENT_RESOURCE":                 "auditor_agent",
        "BUYER_AGENT_RESOURCE":                   "buyer_agent",
        "TREND_AGENT_RESOURCE":                   "trend_agent",
        "SUPPLIER_CLASSIFICATION_AGENT_RESOURCE": "supplier_classification_agent",
        "FINANCIAL_LEAKAGE_AGENT_RESOURCE":       "financial_leakage_agent",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# STATE FILE — Saves deployed resource names so you don't lose them
# ─────────────────────────────────────────────────────────────────────────────

STATE_FILE = "deployed_agents_state.json"


def load_state() -> dict:
    """Load previously saved deployment state."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    """Save deployment state to file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    logger.info("State saved to %s", STATE_FILE)


# ─────────────────────────────────────────────────────────────────────────────
# DEPLOYMENT FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def check_prerequisites() -> bool:
    """Check that all required tools and credentials are set up."""
    logger.info("Checking prerequisites...")

    if not PROJECT_ID:
        logger.error(
            "GOOGLE_CLOUD_PROJECT environment variable is not set!\n"
            "  Windows: $env:GOOGLE_CLOUD_PROJECT = 'your-project-id'\n"
            "  Linux/Mac: export GOOGLE_CLOUD_PROJECT=your-project-id"
        )
        return False

    try:
        import vertexai
        logger.info("✓ vertexai package found")
    except ImportError:
        logger.error("vertexai package not found. Run: pip install google-cloud-aiplatform[agent-engines]")
        return False

    try:
        from vertexai.agent_engines import AdkApp
        logger.info("✓ AdkApp available")
    except ImportError:
        logger.error("AdkApp not found. Run: pip install google-cloud-aiplatform[agent-engines]>=1.118.0")
        return False

    try:
        import google.auth
        creds, project = google.auth.default()
        logger.info("✓ Google credentials found (project=%s)", project)
    except Exception as e:
        logger.error(
            "No Google credentials found: %s\n"
            "Run: gcloud auth application-default login",
            e,
        )
        return False

    logger.info("✓ All prerequisites met! Project: %s, Location: %s", PROJECT_ID, LOCATION)
    return True


def get_agent_requirements(agent_key: str) -> list[str]:
    """Read requirements.txt for an agent."""
    req_path = os.path.join("infra", "agents", agent_key, "requirements.txt")
    if not os.path.exists(req_path):
        # Fall back to common requirements
        return [
            "google-adk>=1.30.0,<2.0.0",
            "google-cloud-aiplatform[agent-engines]>=1.118.0,<2.0.0",
            "google-cloud-bigquery",
            "google-auth>=2.49.0",
            "requests>=2.33.0",
        ]
    with open(req_path) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def deploy_agent(agent_key: str, state: dict) -> str | None:
    """Deploy a single agent and return its resource name."""
    import vertexai
    from vertexai.agent_engines import AdkApp
    import importlib.util

    display_name = AGENT_DISPLAY_NAMES.get(agent_key, agent_key)
    logger.info("\n" + "="*60)
    logger.info("Deploying: %s", display_name)
    logger.info("="*60)

    # Load the agent module dynamically
    agent_path = os.path.join("infra", "agents", agent_key, "agent.py")
    if not os.path.exists(agent_path):
        logger.error("Agent file not found: %s", agent_path)
        return None

    # Set environment variables needed by this agent from previously deployed agents
    deps = AGENT_ENV_DEPS.get(agent_key, {})
    for env_var, dep_agent_key in deps.items():
        if dep_agent_key in state:
            os.environ[env_var] = state[dep_agent_key]
            logger.info("Set %s = %s", env_var, state[dep_agent_key])
        else:
            logger.warning(
                "Dependency %s (%s) not deployed yet! Continuing anyway...",
                dep_agent_key, env_var
            )

    # Set required env vars
    os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
    os.environ["GOOGLE_CLOUD_LOCATION"] = LOCATION

    try:
        # Initialize Vertex AI
        vertexai.init(project=PROJECT_ID, location=LOCATION)

        # Dynamically import the agent module
        spec = importlib.util.spec_from_file_location(agent_key, agent_path)
        module = importlib.util.module_from_spec(spec)

        # Add the agents directory to path so relative imports work
        agents_dir = os.path.join("infra", "agents")
        if agents_dir not in sys.path:
            sys.path.insert(0, agents_dir)
        if "infra" not in sys.path:
            sys.path.insert(0, "infra")

        spec.loader.exec_module(module)

        # Get the root_agent from the module
        if hasattr(module, "root_agent"):
            agent_obj = module.root_agent
        elif hasattr(module, "agent"):
            agent_obj = module.agent
        else:
            # Look in __init__.py
            init_path = os.path.join("infra", "agents", agent_key, "__init__.py")
            if os.path.exists(init_path):
                spec2 = importlib.util.spec_from_file_location(f"{agent_key}.__init__", init_path)
                init_module = importlib.util.module_from_spec(spec2)
                spec2.loader.exec_module(init_module)
                agent_obj = getattr(init_module, "root_agent", None)
            else:
                agent_obj = None

        if agent_obj is None:
            logger.error("Could not find 'root_agent' in %s", agent_path)
            return None

        # Get requirements
        requirements = get_agent_requirements(agent_key)
        logger.info("Requirements: %s", requirements[:3], "...")

        # Wrap in AdkApp and deploy
        app = AdkApp(agent=agent_obj)
        logger.info("Deploying to Vertex AI Agent Engine... (this can take 5-10 minutes)")

        remote_agent = vertexai.agent_engines.create(
            app,
            requirements=requirements,
            display_name=display_name,
            staging_bucket=STAGING_BUCKET,
        )

        resource_name = remote_agent.resource_name
        logger.info("✅ Successfully deployed: %s", display_name)
        logger.info("   Resource: %s", resource_name)
        return resource_name

    except Exception as e:
        logger.error("❌ Failed to deploy %s: %s", display_name, e)
        import traceback
        traceback.print_exc()
        return None


def test_agent(resource_name: str, test_message: str = "Hello! Are you working? Give me a brief status.") -> None:
    """Test a deployed agent with a simple query."""
    import vertexai

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    logger.info("\nTesting agent: %s", resource_name)
    logger.info("Query: %s", test_message)

    try:
        agent = vertexai.agent_engines.get(resource_name)
        logger.info("Sending query...")

        responses = []
        for chunk in agent.stream_query(
            message=test_message,
            user_id="test-user-deploy-script",
        ):
            if isinstance(chunk, dict):
                content = chunk.get("content", {})
                if isinstance(content, dict):
                    for part in content.get("parts", []):
                        if isinstance(part, dict) and "text" in part:
                            responses.append(part["text"])

        if responses:
            logger.info("\n✅ Agent responded successfully!")
            logger.info("Response:\n%s", "\n".join(responses))
        else:
            logger.warning("Agent returned no text response (may still be working)")

    except Exception as e:
        logger.error("❌ Test failed: %s", e)
        import traceback
        traceback.print_exc()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy SCO agents to Vertex AI")
    parser.add_argument(
        "--agent",
        choices=list(AGENT_DISPLAY_NAMES.keys()),
        help="Deploy only a specific agent (default: deploy all in order)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a test query after deploying",
    )
    parser.add_argument(
        "--test-only",
        metavar="RESOURCE_NAME",
        help="Test a specific already-deployed agent (skip deployment)",
    )
    parser.add_argument(
        "--list-deployed",
        action="store_true",
        help="List all previously deployed agents from state file",
    )
    args = parser.parse_args()

    # Load existing deployment state
    state = load_state()

    # ── List deployed agents ────────────────────────────────────────────────
    if args.list_deployed:
        if state:
            logger.info("\nPreviously deployed agents:")
            for agent_key, resource_name in state.items():
                logger.info("  %-40s  %s", AGENT_DISPLAY_NAMES.get(agent_key, agent_key), resource_name)
        else:
            logger.info("No agents have been deployed yet (no state file found).")
        return

    # ── Test only mode ──────────────────────────────────────────────────────
    if args.test_only:
        if not check_prerequisites():
            sys.exit(1)
        test_agent(args.test_only)
        return

    # ── Check prerequisites before deploying ───────────────────────────────
    if not check_prerequisites():
        sys.exit(1)

    # ── Determine which agents to deploy ───────────────────────────────────
    if args.agent:
        agents_to_deploy = [args.agent]
    else:
        agents_to_deploy = AGENT_DEPLOY_ORDER

    # ── Deploy agents ───────────────────────────────────────────────────────
    failed = []
    for agent_key in agents_to_deploy:
        if agent_key in state:
            logger.info(
                "\nSkipping %s — already deployed: %s",
                AGENT_DISPLAY_NAMES.get(agent_key, agent_key),
                state[agent_key],
            )
            continue

        resource_name = deploy_agent(agent_key, state)
        if resource_name:
            state[agent_key] = resource_name
            save_state(state)  # Save after each successful deployment

            if args.test:
                time.sleep(10)  # Give the agent a moment to start
                test_agent(resource_name)
        else:
            failed.append(agent_key)
            logger.error("Deployment of %s failed. Stopping.", agent_key)
            break

    # ── Summary ─────────────────────────────────────────────────────────────
    logger.info("\n" + "="*60)
    logger.info("DEPLOYMENT SUMMARY")
    logger.info("="*60)
    for agent_key, resource_name in state.items():
        status = "✅" if agent_key not in failed else "❌"
        logger.info("%s %-40s", status, AGENT_DISPLAY_NAMES.get(agent_key, agent_key))
        logger.info("   %s", resource_name)

    if failed:
        logger.error("\nFailed agents: %s", failed)
        logger.info("Check logs above. You can re-run and it will skip already deployed agents.")
        sys.exit(1)
    else:
        logger.info("\n✅ All agents deployed successfully!")
        logger.info("Resource names saved to: %s", STATE_FILE)
        logger.info("\nNext steps:")
        logger.info("  1. Test the Spend IQ agent: python scripts/deploy_agents.py --test-only '%s'", state.get("spend_iq_agent", "RESOURCE_NAME"))
        logger.info("  2. Start the web app: cd web-app && npm run dev")


if __name__ == "__main__":
    main()

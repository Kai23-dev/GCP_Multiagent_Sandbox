import sys
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import run_sandbox_agent_validations as runner


class SandboxAgentValidationSelectionTests(unittest.TestCase):
    def test_available_agents_contains_expected_agents(self):
        expected_agents = {
            "trend",
            "financial_leakage",
            "supplier_classification",
            "buyer",
            "auditor",
            "visualization",
            "contract_intelligence_check",
        }

        self.assertEqual(set(runner.available_agents()), expected_agents)

    def test_resolve_single_agent(self):
        self.assertEqual(runner.resolve_agents("trend"), ["trend"])

    def test_resolve_all_agents(self):
        self.assertEqual(runner.resolve_agents("all"), runner.available_agents())

    def test_unknown_agent_raises_error(self):
        with self.assertRaises(ValueError):
            runner.resolve_agents("unknown_agent")


if __name__ == "__main__":
    unittest.main()
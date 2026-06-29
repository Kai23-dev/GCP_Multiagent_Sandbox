import argparse
import sys
from dataclasses import dataclass
from typing import Dict, List


PROJECT_ID = "gp-ct-sbox-con-sbp0i2-eyenterp"
DATASET = "ai_financial_dlp"


@dataclass
class ValidationQuery:
    title: str
    sql: str


AGENT_VALIDATIONS: Dict[str, List[ValidationQuery]] = {
    "trend": [
        ValidationQuery(
            "Monthly vendor spend trend",
            f"""
SELECT
  period_name,
  vendor_name,
  SUM(amount) AS total_spend
FROM `{PROJECT_ID}.{DATASET}.XXC_GL_SUMMARY`
GROUP BY period_name, vendor_name
ORDER BY period_name, total_spend DESC
""",
        ),
        ValidationQuery(
            "Category-wise spend",
            f"""
SELECT
  category,
  SUM(amount) AS total_spend
FROM `{PROJECT_ID}.{DATASET}.XXC_GL_SUMMARY`
GROUP BY category
ORDER BY total_spend DESC
""",
        ),
    ],
    "financial_leakage": [
        ValidationQuery(
            "Financial leakage risk classification",
            f"""
SELECT
  vendor_name,
  amount,
  category,
  commodity,
  line_description,
  po_number,
  CASE
    WHEN LOWER(line_description) LIKE "%gift card%" THEN "High Risk"
    WHEN LOWER(line_description) LIKE "%airpods%" THEN "High Risk"
    WHEN po_number IS NULL AND amount > 1000 THEN "High Risk"
    WHEN LOWER(line_description) LIKE "%coffee machine%" THEN "Medium Risk"
    WHEN LOWER(line_description) LIKE "%streaming%" THEN "Medium Risk"
    WHEN po_number IS NULL AND amount > 500 THEN "Medium Risk"
    ELSE "Low Risk"
  END AS leakage_risk
FROM `{PROJECT_ID}.{DATASET}.XXC_GL_SUMMARY_FINANCIAL_LEAKAGE_SANDBOX`
ORDER BY amount DESC
""",
        )
    ],
    "supplier_classification": [
        ValidationQuery(
            "Supplier classification by category and commodity",
            f"""
SELECT
  vendor_name,
  category,
  super_category,
  commodity,
  SUM(amount) AS total_spend
FROM `{PROJECT_ID}.{DATASET}.XXC_GL_SUMMARY`
GROUP BY vendor_name, category, super_category, commodity
ORDER BY total_spend DESC
""",
        )
    ],
    "buyer": [
        ValidationQuery(
            "Buyer/procurement vendor concentration",
            f"""
SELECT
  vendor_name,
  category,
  COUNT(*) AS transaction_count,
  SUM(amount) AS total_spend,
  AVG(amount) AS avg_transaction_amount
FROM `{PROJECT_ID}.{DATASET}.XXC_GL_SUMMARY`
GROUP BY vendor_name, category
ORDER BY total_spend DESC
""",
        )
    ],
    "auditor": [
        ValidationQuery(
            "Unpaid invoices",
            f"""
SELECT
  invoice_id,
  vendor_id,
  invoice_number,
  invoice_amount,
  invoice_date,
  payment_status_flag
FROM `{PROJECT_ID}.{DATASET}.AP_INVOICES_ALL`
WHERE payment_status_flag = "N"
ORDER BY invoice_amount DESC
""",
        ),
        ValidationQuery(
            "Duplicate invoice check",
            f"""
SELECT
  invoice_number,
  COUNT(*) AS duplicate_count
FROM `{PROJECT_ID}.{DATASET}.AP_INVOICES_ALL`
GROUP BY invoice_number
HAVING COUNT(*) > 1
""",
        ),
        ValidationQuery(
            "High-value invoice check",
            f"""
SELECT
  invoice_id,
  vendor_id,
  invoice_number,
  invoice_amount,
  invoice_date,
  payment_status_flag
FROM `{PROJECT_ID}.{DATASET}.AP_INVOICES_ALL`
WHERE invoice_amount > 10000
ORDER BY invoice_amount DESC
""",
        ),
    ],
    "visualization": [
        ValidationQuery(
            "Monthly spend chart-ready output",
            f"""
SELECT
  period_name,
  SUM(amount) AS total_spend
FROM `{PROJECT_ID}.{DATASET}.XXC_GL_SUMMARY`
GROUP BY period_name
ORDER BY period_name
""",
        ),
        ValidationQuery(
            "Category spend chart-ready output",
            f"""
SELECT
  category,
  SUM(amount) AS total_spend
FROM `{PROJECT_ID}.{DATASET}.XXC_GL_SUMMARY`
GROUP BY category
ORDER BY total_spend DESC
""",
        ),
    ],
    "contract_intelligence_check": [
        ValidationQuery(
            "Contract-related table availability check",
            f"""
SELECT table_name
FROM `{PROJECT_ID}.{DATASET}.INFORMATION_SCHEMA.TABLES`
ORDER BY table_name
""",
        )
    ],
}


def available_agents() -> List[str]:
    return sorted(AGENT_VALIDATIONS.keys())


def resolve_agents(agent: str) -> List[str]:
    if agent == "all":
        return available_agents()

    if agent not in AGENT_VALIDATIONS:
        raise ValueError(
            f"Unknown agent '{agent}'. Valid values: {', '.join(available_agents())}, all"
        )

    return [agent]


def print_rows(rows, max_rows: int = 20) -> None:
    count = 0
    for row in rows:
        print(dict(row))
        count += 1
        if count >= max_rows:
            break

    if count == 0:
        print("(No rows returned)")


def run_query(sql: str, max_rows: int) -> None:
    try:
        from google.cloud import bigquery
    except ImportError:
        print("ERROR: google-cloud-bigquery is not installed.")
        print("Install it with: python -m pip install google-cloud-bigquery")
        sys.exit(1)

    client = bigquery.Client(project=PROJECT_ID)
    job = client.query(sql)
    rows = job.result()
    print_rows(rows, max_rows=max_rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run sandbox-only BigQuery validations for agent use cases without deploying agents."
    )
    parser.add_argument(
        "--agent",
        required=True,
        choices=available_agents() + ["all"],
        help="Agent validation to run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print SQL only. Do not query BigQuery.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=20,
        help="Maximum rows to print per validation query.",
    )

    args = parser.parse_args()
    selected_agents = resolve_agents(args.agent)

    print("Sandbox Agent Validation Runner")
    print(f"Project: {PROJECT_ID}")
    print(f"Dataset: {DATASET}")
    print(f"Selected agent(s): {', '.join(selected_agents)}")
    print("=" * 80)

    for agent_name in selected_agents:
        print(f"\nAGENT: {agent_name}")
        print("-" * 80)

        for validation in AGENT_VALIDATIONS[agent_name]:
            print(f"\nValidation: {validation.title}")
            print("SQL:")
            print(validation.sql.strip())

            if args.dry_run:
                print("\nDry run enabled. Query not executed.")
                continue

            print("\nResult:")
            run_query(validation.sql, max_rows=args.max_rows)

    print("\nValidation run completed.")


if __name__ == "__main__":
    main()
"""ETL: Flatten contract metadata JSONs → BigQuery CONTRACT_METADATA table.

Reads all contracts_metadata_*.json files from the metadata folder,
normalizes the heterogeneous schemas into a flat structure, and loads
into ai_financial_dlp.CONTRACT_METADATA in BigQuery.

Usage:
    # Dry run — outputs NDJSON to stdout (no BigQuery write)
    python etl_contract_metadata_to_bq.py --dry-run

    # Load into BigQuery
    python etl_contract_metadata_to_bq.py \
        --project <GCP_PROJECT_ID> \
        --metadata-dir <path/to/metadata/folder>

    # Default metadata dir (relative to this script):
    #   ../web-app/SSI/contract-intelligent-agent/contracts/metadata
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
import sys
from datetime import date, datetime
from typing import Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("etl_contract_metadata")

# ─── Constants ────────────────────────────────────────────────────────────────
DATASET = "ai_financial_dlp"
TABLE = "CONTRACT_METADATA"
FULL_TABLE_ID = f"{DATASET}.{TABLE}"

# Default path relative to this script
_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_METADATA_DIR = (
    _SCRIPT_DIR.parent
    / "web-app"
    / "SSI"
    / "contract-intelligent-agent"
    / "contracts"
    / "metadata"
)


# ─── Schema (BigQuery) ───────────────────────────────────────────────────────
BQ_SCHEMA = [
    {"name": "ironclad_id", "type": "STRING", "mode": "NULLABLE"},
    {"name": "contract_type", "type": "STRING", "mode": "NULLABLE"},
    {"name": "contract_name", "type": "STRING", "mode": "NULLABLE"},
    {"name": "counterparty_name", "type": "STRING", "mode": "NULLABLE"},
    {"name": "agreement_date", "type": "DATE", "mode": "NULLABLE"},
    {"name": "effective_date", "type": "DATE", "mode": "NULLABLE"},
    {"name": "expiration_date", "type": "DATE", "mode": "NULLABLE"},
    {"name": "anniversary_date", "type": "DATE", "mode": "NULLABLE"},
    {"name": "renewal_type", "type": "STRING", "mode": "NULLABLE"},
    {"name": "renewal_term_length", "type": "STRING", "mode": "NULLABLE"},
    {"name": "initial_term_length", "type": "STRING", "mode": "NULLABLE"},
    {"name": "contract_value_amount", "type": "FLOAT64", "mode": "NULLABLE"},
    {"name": "contract_value_currency", "type": "STRING", "mode": "NULLABLE"},
    {"name": "contract_status", "type": "STRING", "mode": "NULLABLE"},
    {"name": "remaining_duration", "type": "STRING", "mode": "NULLABLE"},
    {"name": "hierarchy_type", "type": "STRING", "mode": "NULLABLE"},
    {"name": "agreement_type", "type": "STRING", "mode": "NULLABLE"},
    {"name": "business_group", "type": "STRING", "mode": "NULLABLE"},
    {"name": "last_updated", "type": "TIMESTAMP", "mode": "NULLABLE"},
    {"name": "signed_copy_filename", "type": "STRING", "mode": "NULLABLE"},
]


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_prop_value(props: dict, key: str) -> Any:
    """Safely extract value from the Ironclad properties format: {key: {type, value}}."""
    entry = props.get(key)
    if entry is None:
        return None
    return entry.get("value")


def _parse_date(raw: Any) -> Optional[str]:
    """Parse various date formats from Ironclad metadata → YYYY-MM-DD string or None."""
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None
        # Try ISO 8601 formats
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
                     "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ",
                     "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(raw[:26].rstrip("Z"), fmt.replace("%z", "").rstrip("Z").rstrip())
                return dt.strftime("%Y-%m-%d")
            except (ValueError, IndexError):
                continue
        # Last resort: take first 10 chars if they look like a date
        if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
            return raw[:10]
    return None


def _parse_monetary(raw: Any) -> tuple[Optional[float], Optional[str]]:
    """Extract (amount, currency) from contractValue format."""
    if raw is None:
        return None, None
    if isinstance(raw, dict):
        amount = raw.get("amount")
        currency = raw.get("currency")
        if amount is not None:
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                amount = None
        return amount, currency
    return None, None


def _extract_signed_copy_filename(attachments: dict) -> Optional[str]:
    """Extract the signed copy filename (D1.LF.XXXXX.pdf) from Ironclad attachments.

    Returns the filename if it starts with 'D1.' (the format used in the RAG index),
    or None otherwise.
    """
    signed = attachments.get("signedCopy")
    if isinstance(signed, dict):
        fn = signed.get("filename", "")
        if fn.startswith("D1."):
            return fn
    return None


def flatten_contract(contract: dict) -> dict:
    """Flatten a single Ironclad contract record into the normalized schema."""
    props = contract.get("properties", {})
    status_obj = contract.get("contractStatus", {})

    # Extract monetary value
    cv_raw = _get_prop_value(props, "contractValue") or _get_prop_value(props, "committedSpend")
    amount, currency = _parse_monetary(cv_raw)

    return {
        "ironclad_id": contract.get("ironcladId"),
        "contract_type": contract.get("type"),
        "contract_name": contract.get("name"),
        "counterparty_name": _get_prop_value(props, "counterpartyName"),
        "agreement_date": _parse_date(_get_prop_value(props, "agreementDate")),
        "effective_date": _parse_date(_get_prop_value(props, "effectiveDate")),
        "expiration_date": _parse_date(_get_prop_value(props, "expirationDate")),
        "anniversary_date": _parse_date(_get_prop_value(props, "standard_anniversaryDate")),
        "renewal_type": _get_prop_value(props, "standard_renewalType"),
        "renewal_term_length": _get_prop_value(props, "standard_renewalTermLength"),
        "initial_term_length": _get_prop_value(props, "standard_initialTermLength"),
        "contract_value_amount": amount,
        "contract_value_currency": currency,
        "contract_status": status_obj.get("enhancedStatus") or status_obj.get("status"),
        "remaining_duration": status_obj.get("remainingDuration"),
        "hierarchy_type": _get_prop_value(props, "hierarachyType"),  # Note: Ironclad typo
        "agreement_type": _get_prop_value(props, "agreementType"),
        "business_group": (
            _get_prop_value(props, "businessGroup")
            or _get_prop_value(props, "businessGroupType")
        ),
        "last_updated": contract.get("lastUpdated"),
        "signed_copy_filename": _extract_signed_copy_filename(
            contract.get("attachments", {})
        ),
    }


def load_and_flatten(metadata_dir: pathlib.Path) -> list[dict]:
    """Load all JSON files from the metadata directory and flatten all contracts."""
    rows: list[dict] = []
    json_files = sorted(metadata_dir.glob("contracts_metadata_*.json"))

    if not json_files:
        logger.error("No contracts_metadata_*.json files found in %s", metadata_dir)
        return rows

    for json_file in json_files:
        logger.info("Processing %s ...", json_file.name)
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                contracts = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read %s: %s", json_file.name, e)
            continue

        if not isinstance(contracts, list):
            logger.warning("%s is not a JSON array, skipping", json_file.name)
            continue

        file_count = 0
        for contract in contracts:
            try:
                row = flatten_contract(contract)
                rows.append(row)
                file_count += 1
            except Exception as e:
                logger.warning(
                    "Failed to flatten contract %s in %s: %s",
                    contract.get("ironcladId", "?"),
                    json_file.name,
                    e,
                )
        logger.info("  → %d contracts flattened from %s", file_count, json_file.name)

    logger.info("Total: %d contracts flattened", len(rows))
    return rows


def write_ndjson(rows: list[dict], output_path: pathlib.Path) -> None:
    """Write flattened rows as NDJSON (newline-delimited JSON)."""
    with open(output_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")
    logger.info("NDJSON written to %s (%d rows)", output_path, len(rows))


def load_to_bigquery(rows: list[dict], project_id: str) -> None:
    """Load flattened rows into BigQuery using the Python client."""
    try:
        from google.cloud import bigquery
    except ImportError:
        logger.error(
            "google-cloud-bigquery not installed. "
            "Run: pip install google-cloud-bigquery"
        )
        sys.exit(1)

    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.{FULL_TABLE_ID}"

    # Build schema from BQ_SCHEMA
    schema = [
        bigquery.SchemaField(col["name"], col["type"], mode=col["mode"])
        for col in BQ_SCHEMA
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    # Write to temp NDJSON, then load
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ndjson", delete=False, encoding="utf-8"
    ) as tmp:
        for row in rows:
            tmp.write(json.dumps(row, default=str) + "\n")
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            load_job = client.load_table_from_file(
                f, table_ref, job_config=job_config
            )
        load_job.result()  # Wait for completion
        logger.info(
            "Loaded %d rows into %s (job: %s)",
            load_job.output_rows,
            table_ref,
            load_job.job_id,
        )
    finally:
        os.unlink(tmp_path)


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Flatten Ironclad contract metadata JSONs → BigQuery CONTRACT_METADATA"
    )
    parser.add_argument(
        "--metadata-dir",
        type=pathlib.Path,
        default=DEFAULT_METADATA_DIR,
        help="Path to metadata JSON folder (default: auto-detected)",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        help="GCP project ID for BigQuery loading",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Flatten only — write NDJSON to file, skip BigQuery loading",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help="Output NDJSON file path (default: contract_metadata.ndjson in current dir)",
    )
    args = parser.parse_args()

    # Validate metadata dir
    if not args.metadata_dir.is_dir():
        logger.error("Metadata directory not found: %s", args.metadata_dir)
        sys.exit(1)

    # Flatten all contracts
    rows = load_and_flatten(args.metadata_dir)
    if not rows:
        logger.error("No contracts to process. Exiting.")
        sys.exit(1)

    # Summary stats
    with_expiry = sum(1 for r in rows if r["expiration_date"] is not None)
    with_effective = sum(1 for r in rows if r["effective_date"] is not None)
    with_status = sum(1 for r in rows if r["contract_status"] is not None)
    logger.info(
        "Coverage: %d/%d have expiration_date, %d/%d have effective_date, %d/%d have contract_status",
        with_expiry, len(rows), with_effective, len(rows), with_status, len(rows),
    )

    # Always write NDJSON
    output_path = args.output or pathlib.Path("contract_metadata.ndjson")
    write_ndjson(rows, output_path)

    if args.dry_run:
        logger.info("Dry run complete. Review %s before loading to BigQuery.", output_path)
        # Print sample
        logger.info("Sample row:")
        print(json.dumps(rows[0], indent=2, default=str))
        return

    # Load to BigQuery
    if not args.project:
        logger.error(
            "No GCP project specified. Use --project <ID> or set GOOGLE_CLOUD_PROJECT."
        )
        sys.exit(1)

    load_to_bigquery(rows, args.project)
    logger.info("Done! Table: %s.%s", args.project, FULL_TABLE_ID)


if __name__ == "__main__":
    main()

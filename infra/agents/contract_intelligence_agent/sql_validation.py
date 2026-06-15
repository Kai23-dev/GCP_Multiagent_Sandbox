"""Shared SQL column validation for CIA root agent and sub-agents.

Catches invalid column names before SQL reaches BigQuery, preventing 500
errors and giving the LLM a correction hint so it can self-correct.

Design: two-tier strategy to avoid false positives:
  Tier 1 — Table-qualified refs (alias.column): always checked against the
           full corrections map.  Safe because the alias pins the table.
  Tier 2 — Unqualified refs in single-table queries: checked against a SAFE
           subset of corrections that are unambiguous (column name never
           valid in any other table).
  Tier 3 — UNNEST struct aliases: detects `UNNEST(field) AS alias` and
           validates alias.column references against known struct schemas.
Multi-table queries with unqualified columns are NOT checked (ambiguous).
String literals are stripped before scanning.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger("cia.sql_validation")

# ─── Blocked SQL keywords ────────────────────────────────────────────────────
BLOCKED_SQL_KEYWORDS = frozenset(
    ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE", "MERGE"]
)

ALLOWED_DATASETS = frozenset(
    ["ai_financial_dlp", "sco_rage_invoice_extract_ds"]
)

DATASET_PATTERN = re.compile(
    r"(?:FROM|JOIN|INTO)\s+`?(?:[\w-]+\.)?(\w+)\.\w+`?",
    re.IGNORECASE,
)

# ─── UNNEST struct schemas ────────────────────────────────────────────────────
# Maps parent_table.struct_field → valid struct member names.
# Used to validate references like `line_item.description` after
# `UNNEST(line_items) AS line_item`.
_UNNEST_STRUCT_SCHEMAS: dict[str, frozenset[str]] = {
    "line_items": frozenset([
        "sku_or_service", "description", "quantity",
        "unit_price", "amount", "category",
    ]),
}

_UNNEST_STRUCT_CORRECTIONS: dict[str, dict[str, str]] = {
    "line_items": {
        "item_description": "description",
        "line_description": "description",
        "sku": "sku_or_service",
        "service": "sku_or_service",
        "sku_or_service_code": "sku_or_service",
        "product": "sku_or_service",
        "price": "unit_price",
        "total": "amount",
        "total_amount": "amount",
        "line_amount": "amount",
        "qty": "quantity",
        "quantity_ordered": "quantity",
        "quantity_invoiced": "quantity",
    },
}

# Pattern: UNNEST(field_name) [AS] alias
_UNNEST_ALIAS_PATTERN = re.compile(
    r"UNNEST\s*\(\s*(\w+)\s*\)\s+(?:AS\s+)?(\w+)",
    re.IGNORECASE,
)

# ─── Column Corrections ──────────────────────────────────────────────────────
# Full corrections map — used ONLY for table-qualified references (alias.col)
COLUMN_CORRECTIONS: dict[str, dict[str, str]] = {
    "COUPA_INVOICES": {
        "line_amount": "invoice_amount",
        "line_item_description": "item_description",
        "description": "item_description",
        "category": "commodity_category",
        "total": "invoice_amount",
        "vendor_name": "supplier_name_normalized",
        "total_amount": "invoice_amount",
        "amount": "invoice_amount",
        "commodity": "commodity_category",
        "vendor_name_normalized": "supplier_name_normalized",
        "effective_date": "invoice_date",
        "order_date": "invoice_date",
        "line_description": "item_description",
        "price": "unit_price",
        "quantity_ordered": "quantity",
        "amount_ordered": "invoice_amount",
        "order_amount": "invoice_amount",
    },
    "IPRO_ORDERS": {
        "invoice_date": "order_date",
        "supplier_name_normalized": "vendor_name_normalized",
        "invoice_amount": "amount_ordered",
        "supplier_name": "vendor_name_normalized",
        "quantity": "quantity_ordered",
        "order_total": "amount_ordered",
        "amount": "amount_ordered",
        "category": "category1",
        "description": "item_description",
        "commodity": "category2",
        "commodity_category": "category1",
        "total": "amount_ordered",
        "total_amount": "amount_ordered",
        "price": "unit_price",
        "facility_number": "facility_id",
        "order_amount": "amount_ordered",
    },
    "XXC_GL_SUMMARY": {
        "invoice_date": "effective_date",
        "supplier_name_normalized": "vendor_name",
        "supplier_name": "vendor_name",
        "invoice_amount": "amount",
        "description": "line_description",
        "item_description": "line_description",
        "vendor_name_normalized": "vendor_name",
        "order_date": "effective_date",
        "amount_ordered": "amount",
        "commodity_category": "commodity",
        "total_amount": "amount",
        "total": "amount",
        "order_amount": "amount",
    },
    "PO_LINES_ALL": {
        "supplier_name_normalized": "po_header_id",
        "supplier_name": "po_header_id",
        "vendor_name": "po_header_id",
        "vendor_name_normalized": "po_header_id",
        "invoice_date": "expiration_date",
        "description": "item_description",
        "quantity_ordered": "quantity",
        "price": "unit_price",
        "order_date": "expiration_date",
        "amount": "unit_price",
        "amount_ordered": "unit_price",
        "order_amount": "unit_price",
    },
    "PO_HEADERS_ALL": {
        "invoice_date": "start_date",
        "order_date": "start_date",
        "effective_date": "start_date",
        "supplier_name": "vendor_id",
        "supplier_name_normalized": "vendor_id",
        "vendor_name": "vendor_id",
        "vendor_name_normalized": "vendor_id",
        "amount": "blanket_total_amount",
        "total": "blanket_total_amount",
        "total_amount": "blanket_total_amount",
        "invoice_amount": "blanket_total_amount",
        "status": "authorization_status",
        "order_amount": "blanket_total_amount",
    },
    "IPRO_CATALOG": {
        "supplier_name_normalized": "vendor_name_normalized",
        "supplier_name": "vendor_name_normalized",
        "unit_price": "price",
        "invoice_date": "effective_date_from",
        "description": "item_description",
        "amount": "price",
        "category": "po_category_1",
        "category1": "po_category_1",
        "commodity": "po_category_1",
        "commodity_category": "po_category_1",
        "item_number": "davita_item_number",
        "item_id": "davita_item_number",
        "order_date": "effective_date_from",
    },
    "COUPA_CATALOG": {
        "vendor_name_normalized": "supplier_name_normalized",
        "vendor_name": "supplier_name_normalized",
        "description": "item_description",
        "category": "commodity_name",
        "commodity": "commodity_name",
        "commodity_category": "commodity_name",
        "invoice_date": "catalog_start_date",
    },
    "AP_INVOICE_DISTRIBUTIONS_ALL": {
        "quantity": "quantity_invoiced",
        "invoice_date": "accounting_date",
        "supplier_name_normalized": "description",
        "supplier_name": "description",
        "amount": "distribution_amount",
        "total": "distribution_amount",
        "vendor_name": "description",
        "vendor_name_normalized": "description",
        "item_description": "description",
        "line_amount": "distribution_amount",
        "order_amount": "distribution_amount",
    },
    "AP_INVOICE_LINES_ALL": {
        "quantity": "quantity_invoiced",
        "invoice_date": "accounting_date",
        "supplier_name_normalized": "item_description",
        "supplier_name": "item_description",
        "line_type": "line_type_lookup_code",
        "amount": "line_amount",
        "total": "line_amount",
        "vendor_name": "item_description",
        "vendor_name_normalized": "item_description",
        "order_amount": "line_amount",
    },
    "CONTRACT_METADATA": {
        "contract_id": "ironclad_id",
        "supplier_name": "counterparty_name",
        "supplier_name_normalized": "counterparty_name",
        "vendor_name": "counterparty_name",
        "vendor_name_normalized": "counterparty_name",
        "status": "contract_status",
        "auto_renewal": "renewal_type",
        "invoice_date": "effective_date",
        "start_date": "effective_date",
        "end_date": "expiration_date",
    },
    "AP_INVOICES_ALL": {
        "supplier_name": "description",
        "supplier_name_normalized": "description",
        "vendor_name": "description",
        "vendor_name_normalized": "description",
        "quantity": "invoice_amount",
        "unit_price": "invoice_amount",
        "currency_code": "invoice_currency_code",
        "invoice_type": "invoice_type_lookup_code",
        "amount": "invoice_amount",
        "total": "invoice_amount",
        "total_amount": "invoice_amount",
        "status": "payment_status_flag",
        "payment_status": "payment_status_flag",
        "order_amount": "invoice_amount",
    },
    "AP_SUPPLIERS": {
        "vendor_name": "supplier_name",
        "vendor_name_normalized": "supplier_name_normalized",
        "invoice_date": "start_date_active",
        "counterparty_name": "supplier_name",
        "vendor_type": "vendor_type_lookup_code",
    },
    "INVOICE_EXTRACTS": {
        "supplier_name": "vendor",
        "supplier_name_normalized": "vendor",
        "vendor_name": "vendor",
        "vendor_name_normalized": "vendor",
        "amount": "total_amount",
        "invoice_amount": "total_amount",
        "confidence": "extraction_confidence",
        "manufacturer": "manufacturer_name",
    },
}

# Safe corrections — column names that are NEVER valid in any table that
# might appear in the same query.  Used for unqualified refs in single-table
# queries only.
SAFE_COLUMN_CORRECTIONS: dict[str, dict[str, str]] = {
    "COUPA_INVOICES": {
        "line_amount": "invoice_amount",
        "line_item_description": "item_description",
        "total_amount": "invoice_amount",
        "line_description": "item_description",
        "amount_ordered": "invoice_amount",
        "order_amount": "invoice_amount",
    },
    "IPRO_ORDERS": {
        "line_amount": "amount_ordered",
        "line_item_description": "item_description",
        "total_amount": "amount_ordered",
        "quantity": "quantity_ordered",
        "order_total": "amount_ordered",
        "commodity_category": "category1",
        "facility_number": "facility_id",
        "order_amount": "amount_ordered",
    },
    "IPRO_CATALOG": {
        "unit_price": "price",
        "item_number": "davita_item_number",
        "category1": "po_category_1",
    },
    "AP_INVOICE_DISTRIBUTIONS_ALL": {
        "quantity": "quantity_invoiced",
        "item_description": "description",
        "line_amount": "distribution_amount",
    },
    "AP_INVOICE_LINES_ALL": {
        "quantity": "quantity_invoiced",
        "line_type": "line_type_lookup_code",
    },
    "CONTRACT_METADATA": {
        "contract_id": "ironclad_id",
        "supplier_name": "counterparty_name",
        "supplier_name_normalized": "counterparty_name",
        "status": "contract_status",
        "auto_renewal": "renewal_type",
    },
    "AP_INVOICES_ALL": {
        "payment_status": "payment_status_flag",
    },
    "AP_SUPPLIERS": {
        "vendor_type": "vendor_type_lookup_code",
    },
    "INVOICE_EXTRACTS": {
        "confidence": "extraction_confidence",
    },
}

# Valid columns per table
TABLE_COLUMNS: dict[str, frozenset[str]] = {
    "COUPA_INVOICES": frozenset([
        "invoice_id", "supplier_id", "invoice_number", "line_number",
        "invoice_date", "created_date", "contract_creation_date",
        "invoice_amount", "unit_price", "quantity", "currency_code",
        "facility_number", "department_number", "gl_account_number",
        "supplier_name", "supplier_name_normalized", "po_number",
        "order_line_number", "contract_name", "contract_number",
        "commodity_category", "commodity_id", "commodity_name",
        "item_description", "requested_by", "requested_by_email",
        "approval_status", "source_system", "created_at", "updated_at",
    ]),
    "IPRO_ORDERS": frozenset([
        "po_number", "vendor_id", "requisition_id", "line_number",
        "davita_item_number", "product_number", "facility_id",
        "facility_name", "city", "state", "phone", "po_creation_date",
        "order_date", "need_by_date", "item_description", "product",
        "manufacturer", "product_category", "category1", "category2",
        "category3", "vendor_name", "vendor_name_normalized", "ordered_by",
        "unit_price", "quantity_ordered", "quantity_received",
        "amount_ordered", "amount_received", "unit_of_measure",
        "expense_account", "charge_to", "sub_account", "eaches",
        "eaches_uom", "quantity_eaches", "service_type", "source",
        "closed_code", "urgent_flag", "year", "month", "year_month",
        "source_system", "created_at", "updated_at",
    ]),
    "XXC_GL_SUMMARY": frozenset([
        "journal_header_id", "journal_line_number", "invoice_id",
        "invoice_number", "gl_code_combination_id", "legal_entity",
        "location", "department", "account", "sub_account", "account_name",
        "sub_account_name", "amount", "stat_amount", "currency_code",
        "ledger_id", "effective_date", "period_name", "journal_posted_date",
        "journal_category", "journal_source", "line_description",
        "batch_name", "category", "super_category", "commodity",
        "vendor_name", "vendor_id", "po_number", "check_id",
        "check_number", "source_system", "created_at", "updated_at",
    ]),
    "AP_INVOICES_ALL": frozenset([
        "invoice_id", "vendor_id", "invoice_number", "invoice_amount",
        "invoice_date", "invoice_currency_code", "payment_status_flag",
        "source", "created_by", "creation_date", "last_updated_by",
        "last_update_date", "org_id", "gl_date", "description",
        "amount_paid", "discount_amount_taken",
        "invoice_type_lookup_code", "batch_id", "source_system",
        "created_at", "updated_at",
    ]),
    "AP_SUPPLIERS": frozenset([
        "vendor_id", "supplier_name", "supplier_name_normalized",
        "vendor_type_lookup_code", "enabled_flag", "is_active",
        "start_date_active", "end_date_active", "source_system",
        "created_at", "updated_at",
    ]),
    "AP_INVOICE_DISTRIBUTIONS_ALL": frozenset([
        "invoice_id", "invoice_line_number", "distribution_line_number",
        "distribution_amount", "unit_price", "quantity_invoiced",
        "description", "gl_code_combination_id", "period_name",
        "accounting_date", "po_distribution_id", "match_type",
        "assets_tracking_flag", "source_system", "created_at", "updated_at",
    ]),
    "AP_INVOICE_LINES_ALL": frozenset([
        "invoice_id", "line_number", "line_type_lookup_code", "line_amount",
        "item_description", "quantity_invoiced", "unit_price", "po_line_id",
        "accounting_date", "description", "source_system",
        "created_at", "updated_at",
    ]),
    "CONTRACT_METADATA": frozenset([
        "ironclad_id", "contract_name", "contract_type", "counterparty_name",
        "agreement_date", "effective_date", "expiration_date", "anniversary_date",
        "renewal_type", "renewal_term_length", "initial_term_length",
        "contract_value_amount", "contract_value_currency", "contract_status",
        "remaining_duration", "hierarchy_type", "agreement_type",
        "business_group", "last_updated",
    ]),
    "PO_HEADERS_ALL": frozenset([
        "po_header_id", "vendor_id", "vendor_site_id", "buyer_id",
        "po_number", "po_type", "ship_to_location_id", "bill_to_location_id",
        "payment_terms_id", "currency_code", "exchange_rate",
        "blanket_total_amount", "amount_limit", "min_release_amount",
        "start_date", "end_date", "approved_date", "authorization_status",
        "is_cancelled", "org_id", "source_system", "created_at", "updated_at",
    ]),
    "PO_LINES_ALL": frozenset([
        "po_line_id", "po_header_id", "item_id", "category_id",
        "line_number", "item_description", "vendor_product_num",
        "unit_price", "base_unit_price", "list_price", "unit_of_measure",
        "quantity", "quantity_committed", "order_type", "purchase_basis",
        "matching_basis", "allow_price_override", "closed_status",
        "expiration_date", "source_system", "created_at", "updated_at",
    ]),
    "IPRO_CATALOG": frozenset([
        "davita_item_number", "item_description", "model_number",
        "manufacturer_part_number", "price", "unit_of_measure",
        "pack_factor", "pack_factor_conversion", "ndc_code",
        "ndc_unit_of_use", "weight", "weight_code", "po_category_1",
        "po_category_2", "po_category_3", "po_category_4",
        "product_category", "updated_product_category", "vendor_name",
        "vendor_name_normalized", "vendor_site", "account_code",
        "modality", "pfbc", "effective_date_from", "effective_date_to",
        "inventoriable", "countable", "green_flag",
        "replacement_item_number", "spare_part", "image_file_name",
        "professional_logo", "price_change_comment",
        "source_system", "created_at", "updated_at",
    ]),
    "COUPA_CATALOG": frozenset([
        "item_id", "supplier_id", "commodity_id", "catalog_id",
        "item_description", "commodity_name", "commodity_custom_field_3",
        "commodity_custom_field_4", "supplier_name",
        "supplier_name_normalized", "catalog_start_date",
        "catalog_end_date", "source_system", "created_at", "updated_at",
    ]),
    "XXC_GL_DIV_REG_FAC": frozenset([
        "facility_id", "facility_description", "facility_common_name",
        "palmer_vp", "palmer_vp_desc", "group_vp", "group_vp_desc",
        "division", "division_desc", "region", "region_desc",
        "facility_type", "legal_entity", "legal_entity_desc",
        "inactive_date", "is_active", "accounting_start_date",
        "accounting_end_date", "denovo_flag", "rollup_flag",
        "facility_administrator_name", "regional_director_name",
        "facility_city", "facility_state", "facility_zip_code",
        "county", "source_system", "created_at", "updated_at",
    ]),
    "Expense_Taxonomy": frozenset([
        "Sourcing_Lane", "L1_Category", "L2_Category", "L3_Category",
        "GL_Account_L3_Code", "GL_Account_Description", "Is_Direct_Flag",
        "Category_Owner", "Effective_Start_Date", "Effective_End_Date",
    ]),
    "DOCUMENTS": frozenset([
        "document_id", "media_id", "datatype_id", "category_id",
        "attached_entity_type", "attached_entity_id", "document_type",
        "document_type_display", "language_code", "document_content",
        "file_name", "document_url", "usage_type", "security_type",
        "translation_language", "source_system", "created_at", "updated_at",
    ]),
    "INVOICE_EXTRACTS": frozenset([
        "document_id", "invoice_number", "vendor", "manufacturer_name",
        "invoice_date", "total_amount", "extraction_confidence",
        "line_items",
    ]),
}

# Pattern: FROM/JOIN `dataset.TABLE` [AS] alias
_TABLE_ALIAS_PATTERN = re.compile(
    r"(?:FROM|JOIN)\s+`?(?:[\w-]+\.)*(\w+)`?"
    r"(?:\s+(?:AS\s+)?(\w+))?",
    re.IGNORECASE,
)

# Pattern: table-qualified column reference (alias.column)
_QUALIFIED_COL_PATTERN = re.compile(r"\b(\w+)\.(\w+)\b")

# SQL keywords that should not be treated as table aliases
_SQL_KEYWORDS = frozenset([
    "WHERE", "ON", "SET", "GROUP", "ORDER", "HAVING", "LIMIT", "UNION",
    "LEFT", "RIGHT", "INNER", "OUTER", "CROSS", "FULL", "AND", "OR",
    "AS", "SELECT", "FROM", "JOIN", "INTO", "VALUES", "CASE", "WHEN",
    "THEN", "ELSE", "END", "NOT", "IN", "BETWEEN", "LIKE", "IS",
    "NULL", "TRUE", "FALSE", "ALL", "ANY", "EXISTS", "DISTINCT",
])


def validate_sql_columns(sql: str) -> Optional[str]:
    """Validate SQL column references against known schemas.

    Three-tier strategy to catch bad columns without false positives:
      Tier 1: Table-qualified refs (alias.column) — checked against full
              corrections map.  Safe because the alias pins the table.
      Tier 2: Unqualified refs in single-table queries — checked against
              SAFE corrections only (unambiguous column names).
      Tier 3: UNNEST struct aliases (alias.field) — checked against known
              struct schemas (e.g., line_items fields).

    Returns an error message with correction hints, or None if valid.
    """
    sql_clean = re.sub(r"'[^']*'", "''", sql)
    sql_clean = re.sub(r'"[^"]*"', '""', sql_clean)

    # Build alias→table map from FROM/JOIN clauses
    alias_map: dict[str, str] = {}
    tables_found: list[str] = []
    for match in _TABLE_ALIAS_PATTERN.finditer(sql_clean):
        table = match.group(1).upper()
        alias = match.group(2)
        if table not in TABLE_COLUMNS:
            continue
        tables_found.append(table)
        alias_map[table] = table
        if alias and alias.upper() not in _SQL_KEYWORDS:
            alias_map[alias.upper()] = table

    # Build UNNEST alias→struct_field map
    unnest_alias_map: dict[str, str] = {}
    for match in _UNNEST_ALIAS_PATTERN.finditer(sql_clean):
        struct_field = match.group(1).lower()
        alias = match.group(2).upper()
        if struct_field in _UNNEST_STRUCT_SCHEMAS:
            unnest_alias_map[alias] = struct_field

    if not tables_found and not unnest_alias_map:
        return None

    errors = []

    # Tier 1: Check table-qualified references (e.g., c.line_amount)
    for match in _QUALIFIED_COL_PATTERN.finditer(sql_clean):
        qualifier = match.group(1).upper()
        column = match.group(2).lower()

        # Tier 3: Check UNNEST struct aliases first
        if qualifier in unnest_alias_map:
            struct_field = unnest_alias_map[qualifier]
            valid_members = _UNNEST_STRUCT_SCHEMAS[struct_field]
            corrections = _UNNEST_STRUCT_CORRECTIONS.get(struct_field, {})
            if column in corrections:
                errors.append(
                    f"Column `{match.group(2)}` does not exist in STRUCT "
                    f"`{struct_field}`. Use `{corrections[column]}` instead. "
                    f"Valid fields: {', '.join(sorted(valid_members))}"
                )
            elif column not in valid_members and column not in _SQL_KEYWORDS:
                suggestion = ""
                if corrections:
                    suggestion = (
                        f" Valid fields: {', '.join(sorted(valid_members))}"
                    )
                errors.append(
                    f"Column `{match.group(2)}` does not exist in STRUCT "
                    f"`{struct_field}`.{suggestion}"
                )
            continue

        # Tier 1: Table-qualified references
        table = alias_map.get(qualifier)
        if table is None:
            continue
        corrections = COLUMN_CORRECTIONS.get(table, {})
        if column in corrections:
            errors.append(
                f"Column `{match.group(2)}` does not exist in {table}. "
                f"Use `{corrections[column]}` instead."
            )

    # Tier 2: Single-table queries — check unqualified columns against
    # safe corrections only (unambiguous names like line_amount)
    unique_tables = list(dict.fromkeys(tables_found))
    if len(unique_tables) == 1:
        table = unique_tables[0]
        safe_corrections = SAFE_COLUMN_CORRECTIONS.get(table, {})
        if safe_corrections:
            sql_no_alias = re.sub(
                r"\bAS\s+(\w+)\b", "", sql_clean, flags=re.IGNORECASE
            )
            sql_tokens = set(re.findall(r"\b(\w+)\b", sql_no_alias.lower()))
            for bad_col, good_col in safe_corrections.items():
                if bad_col in sql_tokens:
                    errors.append(
                        f"Column `{bad_col}` does not exist in {table}. "
                        f"Use `{good_col}` instead."
                    )

    if errors:
        unique_errors = list(dict.fromkeys(errors))
        return (
            "SQL column validation failed:\n"
            + "\n".join(f"- {e}" for e in unique_errors)
            + "\n\nPlease fix the column names and retry."
        )
    return None


def validate_sql_safety(sql: str) -> Optional[str]:
    """Check SQL for destructive operations, unauthorized datasets, and
    information_schema queries.

    Returns an error message string if blocked, or None if safe.
    """
    sql_upper = sql.upper()

    for kw in BLOCKED_SQL_KEYWORDS:
        if kw in sql_upper.split():
            return (
                f"Destructive SQL ({kw}) is not permitted. "
                "Only SELECT queries are allowed."
            )

    datasets_found = set(DATASET_PATTERN.findall(sql))
    unauthorized = datasets_found - ALLOWED_DATASETS
    if unauthorized:
        return (
            f"Unauthorized dataset(s): {', '.join(sorted(unauthorized))}. "
            f"Only these datasets are allowed: {', '.join(sorted(ALLOWED_DATASETS))}."
        )

    if "INFORMATION_SCHEMA" in sql_upper:
        return (
            "Queries against INFORMATION_SCHEMA are not permitted. "
            "Use the provided specialized tools for schema information."
        )

    return None


def make_before_tool_callback(agent_name: str = "sub_agent"):
    """Create a before_tool_callback that validates SQL for sub-agents.

    Returns a callback function suitable for the Agent `before_tool_callback`
    parameter. Validates destructive SQL, dataset whitelist, and column names.
    """

    def _before_tool_callback(tool, args, tool_context):
        tool_name = getattr(tool, "name", str(tool))

        if tool_name in ("ssi_execute_sql", "execute_sql_tool"):
            sql = str(
                args.get("sql", "")
                or args.get("statement", "")
                or ""
            )

            logger.info(
                "[%s] SQL query: tool=%s | sql=%s",
                agent_name, tool_name, sql[:500],
            )

            safety_error = validate_sql_safety(sql)
            if safety_error:
                logger.warning(
                    "[%s] BLOCKED: %s | sql=%s",
                    agent_name, safety_error, sql[:200],
                )
                return {"error": safety_error}

            col_error = validate_sql_columns(sql)
            if col_error:
                logger.warning(
                    "[%s] BLOCKED invalid column: %s | sql=%s",
                    agent_name, col_error, sql[:300],
                )
                return {"error": col_error}

        return None

    return _before_tool_callback

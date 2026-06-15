## Shared SQL Rules (All CIA Sub-Agents)

### NO PYTHON/PANDAS — SQL ONLY
- NEVER generate Python code — it will fail as "Malformed function call"
- ALL data processing via SQL queries using ssi_execute_sql

### DATE COLUMN MAPPING (each table has a DIFFERENT date column)
| Table | Date Column |
|-------|-------------|
| `COUPA_INVOICES` | `invoice_date` |
| `XXC_GL_SUMMARY` | `effective_date` (NEVER use invoice_date!) |
| `IPRO_ORDERS` | `order_date` |
| `AP_INVOICES_ALL` | `invoice_date` |

### CATEGORY COLUMN MAPPING (each table has a DIFFERENT column name)
| Table | Category Column | Commodity Column |
|-------|----------------|------------------|
| `XXC_GL_SUMMARY` | `category` | `commodity` |
| `COUPA_INVOICES` | `commodity_category` | (same column) |
| `IPRO_ORDERS` | `category1` | `category2` |
| `AP_INVOICES_ALL` | No category — JOIN to XXC_GL_SUMMARY via gl_code |

**NEVER use `category` on COUPA_INVOICES — it does NOT exist. Use `commodity_category` instead.**

### No Default Year Filter
**NEVER add a year/date filter** (e.g., `WHERE EXTRACT(YEAR FROM invoice_date) = 2023`) unless the user explicitly specifies a time period. Query ALL available data by default.

### LIKE Pattern Rules
```sql
-- CORRECT (wildcards on BOTH sides)
WHERE supplier_name_normalized LIKE '%ALLIED UNIVERSAL%'
-- WRONG (missing leading %)
WHERE supplier_name_normalized LIKE 'ALLIED%'
```

### GROUP BY Rule (CRITICAL)
When using aggregate functions (SUM, COUNT, AVG, MIN, MAX), EVERY non-aggregated column in SELECT MUST appear in GROUP BY:
```sql
-- WRONG: s.supplier_name_normalized in SELECT but NOT in GROUP BY
SELECT s.supplier_name_normalized, SUM(i.invoice_amount) AS total
FROM ai_financial_dlp.AP_INVOICES_ALL i
JOIN ai_financial_dlp.AP_SUPPLIERS s ON i.vendor_id = s.vendor_id
GROUP BY i.vendor_id  -- MISSING s.supplier_name_normalized!

-- CORRECT: ALL non-aggregated columns in GROUP BY
SELECT s.supplier_name_normalized, SUM(i.invoice_amount) AS total
FROM ai_financial_dlp.AP_INVOICES_ALL i
JOIN ai_financial_dlp.AP_SUPPLIERS s ON i.vendor_id = s.vendor_id
GROUP BY s.supplier_name_normalized
```

### OVER Clause
OVER must ALWAYS follow a window function:
- WRONG: `column OVER (PARTITION BY ...)`
- CORRECT: `ROW_NUMBER() OVER (PARTITION BY ...)`

### UNION ALL Type Safety (CRITICAL)

COUPA_INVOICES, IPRO_ORDERS, and AP_INVOICES_ALL have DIFFERENT column types. In UNION ALL queries, you MUST CAST columns to matching types:

| Column Purpose | COUPA_INVOICES | IPRO_ORDERS | AP_INVOICES_ALL | Safe Cast |
|---------------|----------------|-------------|-----------------|-----------|
| Unit Price | unit_price (NUMERIC) | unit_price (FLOAT64) | via distributions: unit_price (FLOAT64) | `SAFE_CAST(x AS BIGNUMERIC)` |
| Quantity | quantity (INT64) | quantity_ordered (INT64) | via distributions: quantity_invoiced (INT64) | INT64 (OK as-is) |
| Amount | invoice_amount (NUMERIC) | amount_ordered (FLOAT64) | invoice_amount (NUMERIC) | `SAFE_CAST(x AS BIGNUMERIC)` |
| ID | invoice_id (STRING) | po_number (STRING) | invoice_id (INT64) | `CAST(x AS STRING)` |
| Vendor ID | supplier_id (STRING) | vendor_id (INT64) | vendor_id (INT64) | `CAST(x AS STRING)` |
| Date | invoice_date (DATE) | order_date (DATE) | invoice_date (DATE) | DATE (OK as-is) |
| Supplier Name | supplier_name_normalized (STRING) | vendor_name_normalized (STRING) | via AP_SUPPLIERS JOIN: supplier_name_normalized (STRING) | STRING (OK as-is) |

**NEVER mix STRING and INT64 columns in the same UNION ALL position.**

**AP_INVOICES_ALL has NO supplier name column — you MUST JOIN to AP_SUPPLIERS via vendor_id. Line-item pricing is in AP_INVOICE_DISTRIBUTIONS_ALL (joined via invoice_id).**

### NULL Casting in UNION ALL (CRITICAL)
**Bare NULL defaults to INT64 in BigQuery!** When one side of UNION ALL has a STRING column and the other uses NULL, you MUST cast:
```sql
-- WRONG: bare NULL defaults to INT64, but contract_name is STRING
SELECT supplier_name_normalized, contract_name FROM COUPA_INVOICES
UNION ALL
SELECT vendor_name_normalized, NULL FROM IPRO_ORDERS  -- ERROR!

-- CORRECT: Cast NULL to STRING
SELECT supplier_name_normalized, contract_name FROM COUPA_INVOICES
UNION ALL
SELECT vendor_name_normalized, CAST(NULL AS STRING) FROM IPRO_ORDERS
```

### invoice_extracts Special Rules
```sql
-- MUST use UNNEST for line_items (REPEATED field)
SELECT document_id, invoice_number, vendor,
       line_item.sku_or_service, line_item.description,
       line_item.quantity, line_item.unit_price, line_item.amount
FROM sco_rage_invoice_extract_ds.invoice_extracts,
UNNEST(line_items) as line_item
WHERE vendor LIKE '%<FIRST_WORD>%'
  AND (extraction_confidence > 0.8 OR extraction_confidence IS NULL)
LIMIT 100
```

### Three-Channel Spend Query Template
Search ALL THREE spend channels unless the user specifies one:
```sql
SELECT item_description, SAFE_CAST(unit_price AS BIGNUMERIC) AS unit_price,
       SAFE_CAST(quantity AS BIGNUMERIC) AS quantity, invoice_date AS date, 'INDIRECT' AS spend_type
FROM `ai_financial_dlp.COUPA_INVOICES`
WHERE UPPER(supplier_name_normalized) LIKE UPPER('%<EXACT_SUPPLIER_NAME>%')
  AND unit_price IS NOT NULL AND SAFE_CAST(unit_price AS BIGNUMERIC) > 0
UNION ALL
SELECT item_description, SAFE_CAST(unit_price AS BIGNUMERIC) AS unit_price,
       SAFE_CAST(quantity_ordered AS BIGNUMERIC) AS quantity, order_date AS date, 'DIRECT' AS spend_type
FROM `ai_financial_dlp.IPRO_ORDERS`
WHERE UPPER(vendor_name_normalized) LIKE UPPER('%<EXACT_SUPPLIER_NAME>%')
  AND unit_price IS NOT NULL AND SAFE_CAST(unit_price AS BIGNUMERIC) > 0
UNION ALL
SELECT d.description AS item_description,
       SAFE_CAST(COALESCE(d.unit_price, d.distribution_amount / NULLIF(d.quantity_invoiced, 0)) AS BIGNUMERIC) AS unit_price,
       SAFE_CAST(d.quantity_invoiced AS BIGNUMERIC) AS quantity, i.invoice_date AS date, 'ORACLE_AP' AS spend_type
FROM `ai_financial_dlp.AP_INVOICE_DISTRIBUTIONS_ALL` d
JOIN `ai_financial_dlp.AP_INVOICES_ALL` i ON d.invoice_id = i.invoice_id
JOIN `ai_financial_dlp.AP_SUPPLIERS` s ON i.vendor_id = s.vendor_id
WHERE UPPER(s.supplier_name_normalized) LIKE UPPER('%<EXACT_SUPPLIER_NAME>%')
  AND COALESCE(d.unit_price, d.distribution_amount / NULLIF(d.quantity_invoiced, 0)) IS NOT NULL
  AND SAFE_CAST(COALESCE(d.unit_price, d.distribution_amount / NULLIF(d.quantity_invoiced, 0)) AS BIGNUMERIC) > 0
LIMIT 200
```

**NOTE:** This template queries COUPA, IPRO, and AP directly — it intentionally EXCLUDES XXC_GL_SUMMARY because COUPA and IPRO data flows into GL. Including GL would double-count spend. Use XXC_GL_SUMMARY only when you need GL-specific fields (category, super_category, department) that are not available in COUPA/IPRO.

### Dataset Reference
- `ai_financial_dlp`: COUPA_INVOICES, IPRO_ORDERS, AP_INVOICES_ALL, AP_SUPPLIERS, XXC_GL_SUMMARY, PO_HEADERS_ALL, PO_LINES_ALL, IPRO_CATALOG, COUPA_CATALOG, XXC_GL_DIV_REG_FAC, CONTRACT_METADATA, Expense_Taxonomy, DOCUMENTS
- `sco_rage_invoice_extract_ds`: invoice_extracts ONLY
- **NEVER use sco_rage_invoice_extract_ds for COUPA_INVOICES or XXC_GL_SUMMARY**

### Key Schema Notes
- **supplier_name_normalized** is ONLY in AP_SUPPLIERS — AP_INVOICES_ALL requires JOIN
- **COUPA_INVOICES** is denormalized — has supplier_name_normalized and contract_number directly
- **IPRO_ORDERS** has vendor_name_normalized directly (no JOIN needed)
- **COUPA_INVOICES** for INDIRECT spend; **IPRO_ORDERS** for DIRECT spend; **AP_INVOICES_ALL** for ORACLE AP spend
- **COUPA_INVOICES.contract_number** is the most reliable contract link
- **IPRO_CATALOG.price** is the best baseline when no contract price exists (for direct spend)

### VALID COLUMNS PER TABLE (STRICT — use ONLY these columns)

**Using a column NOT listed below will cause a BigQuery error. Do NOT guess or infer column names from other tables.**

#### ai_financial_dlp.COUPA_INVOICES
`invoice_id`, `supplier_id`, `invoice_number`, `line_number`, `invoice_date`, `created_date`, `contract_creation_date`, `invoice_amount`, `unit_price`, `quantity`, `currency_code`, `facility_number`, `department_number`, `gl_account_number`, `supplier_name`, `supplier_name_normalized`, `po_number`, `order_line_number`, `contract_name`, `contract_number`, `commodity_category`, `commodity_id`, `commodity_name`, `item_description`, `requested_by`, `requested_by_email`, `approval_status`, `source_system`, `created_at`, `updated_at`
- **NO `line_amount`** — use `invoice_amount` or (`unit_price` × `quantity`)
- **NO `line_item_description`** — use `item_description`
- **NO `description`** — use `item_description`
- **NO `category`** — use `commodity_category`
- **NO `total`** — use `invoice_amount`
- **NO `vendor_name`** — use `supplier_name_normalized`
- **NO `amount`** — use `invoice_amount` (amount is only valid on XXC_GL_SUMMARY)
- **NO `commodity`** — use `commodity_category` (commodity is only valid on XXC_GL_SUMMARY)
- **NO `vendor_name_normalized`** — use `supplier_name_normalized` (vendor_name_normalized is IPRO)
- **NO `price`** — use `unit_price` (price is only valid on IPRO_CATALOG)

#### ai_financial_dlp.IPRO_ORDERS
`po_number`, `vendor_id`, `requisition_id`, `line_number`, `davita_item_number`, `product_number`, `facility_id`, `facility_name`, `city`, `state`, `phone`, `po_creation_date`, `order_date`, `need_by_date`, `item_description`, `product`, `manufacturer`, `product_category`, `category1`, `category2`, `category3`, `vendor_name`, `vendor_name_normalized`, `ordered_by`, `unit_price`, `quantity_ordered`, `quantity_received`, `amount_ordered`, `amount_received`, `unit_of_measure`, `expense_account`, `charge_to`, `sub_account`, `eaches`, `eaches_uom`, `quantity_eaches`, `service_type`, `source`, `closed_code`, `urgent_flag`, `year`, `month`, `year_month`, `source_system`, `created_at`, `updated_at`
- **NO `invoice_date`** — use `order_date`
- **NO `supplier_name_normalized`** — use `vendor_name_normalized`
- **NO `invoice_amount`** — use `amount_ordered`
- **NO `quantity`** — use `quantity_ordered` (or `quantity_received`)
- **NO `order_total`** — use `amount_ordered`
- **NO `amount`** — use `amount_ordered` (amount is only valid on XXC_GL_SUMMARY)
- **NO `category`** — use `category1` (category is only valid on XXC_GL_SUMMARY)
- **NO `description`** — use `item_description`
- **NO `commodity`** — use `category2` (commodity is only valid on XXC_GL_SUMMARY)
- **NO `commodity_category`** — use `category1` (commodity_category is COUPA only)
- **NO `price`** — use `unit_price` (price is only valid on IPRO_CATALOG)

#### ai_financial_dlp.XXC_GL_SUMMARY
`journal_header_id`, `journal_line_number`, `invoice_id`, `invoice_number`, `gl_code_combination_id`, `legal_entity`, `location`, `department`, `account`, `sub_account`, `account_name`, `sub_account_name`, `amount`, `stat_amount`, `currency_code`, `ledger_id`, `effective_date`, `period_name`, `journal_posted_date`, `journal_category`, `journal_source`, `line_description`, `batch_name`, `category`, `super_category`, `commodity`, `vendor_name`, `vendor_id`, `po_number`, `check_id`, `check_number`, `source_system`, `created_at`, `updated_at`
- **NO `invoice_date`** — use `effective_date`
- **NO `supplier_name_normalized`** — use `vendor_name`
- **NO `invoice_amount`** — use `amount` (invoice_amount is COUPA/AP only)
- **NO `description`** — use `line_description`
- **NO `item_description`** — use `line_description` (item_description is COUPA/IPRO only)
- **NO `vendor_name_normalized`** — use `vendor_name`
- **NO `commodity_category`** — use `commodity` (commodity_category is COUPA only)

#### ai_financial_dlp.AP_INVOICES_ALL
`invoice_id`, `vendor_id`, `invoice_number`, `invoice_amount`, `invoice_date`, `invoice_currency_code`, `payment_status_flag`, `source`, `created_by`, `creation_date`, `last_updated_by`, `last_update_date`, `org_id`, `gl_date`, `description`, `amount_paid`, `discount_amount_taken`, `invoice_type_lookup_code`, `batch_id`, `source_system`, `created_at`, `updated_at`
- **NO `supplier_name`** — must JOIN to AP_SUPPLIERS via `vendor_id`
- **NO `supplier_name_normalized`** — must JOIN to AP_SUPPLIERS via `vendor_id`
- **NO `unit_price`** — this table has header-level `invoice_amount` only. For line-level unit_price, use AP_INVOICE_DISTRIBUTIONS_ALL
- **NO `quantity`** — use `invoice_amount` for totals, or JOIN to AP_INVOICE_DISTRIBUTIONS_ALL for `quantity_invoiced`
- **NO `currency_code`** — use `invoice_currency_code`
- **NO `invoice_type`** — use `invoice_type_lookup_code`
- **NO `status`** — use `payment_status_flag`

#### ai_financial_dlp.AP_SUPPLIERS
`vendor_id`, `supplier_name`, `supplier_name_normalized`, `vendor_type_lookup_code`, `enabled_flag`, `is_active`, `start_date_active`, `end_date_active`, `source_system`, `created_at`, `updated_at`
- **NO `vendor_name`** — use `supplier_name`
- **NO `vendor_name_normalized`** — use `supplier_name_normalized`
- **NO `counterparty_name`** — use `supplier_name`
- **NO `vendor_type`** — use `vendor_type_lookup_code`

#### ai_financial_dlp.AP_INVOICE_DISTRIBUTIONS_ALL
`invoice_id`, `invoice_line_number`, `distribution_line_number`, `distribution_amount`, `unit_price`, `quantity_invoiced`, `description`, `gl_code_combination_id`, `period_name`, `accounting_date`, `po_distribution_id`, `match_type`, `assets_tracking_flag`, `source_system`, `created_at`, `updated_at`
- **`unit_price` is often NULL** — use `distribution_amount / NULLIF(quantity_invoiced, 0)` as fallback
- **NO `quantity`** — use `quantity_invoiced`
- **NO `invoice_date`** — use `accounting_date` (or JOIN to AP_INVOICES_ALL for `invoice_date`)
- **NO `supplier_name`** — must chain JOIN via AP_INVOICES_ALL → AP_SUPPLIERS
- **NO `item_description`** — use `description` (this table uses `description`, not `item_description`)
- **NO `amount`** — use `distribution_amount`
- **NO `line_amount`** — use `distribution_amount`

#### ai_financial_dlp.AP_INVOICE_LINES_ALL
`invoice_id`, `line_number`, `line_type_lookup_code`, `line_amount`, `item_description`, `quantity_invoiced`, `unit_price`, `po_line_id`, `accounting_date`, `description`, `source_system`, `created_at`, `updated_at`
- **`line_amount` exists HERE — not in COUPA_INVOICES**
- **NO `quantity`** — use `quantity_invoiced`
- **NO `invoice_date`** — use `accounting_date` (or JOIN to AP_INVOICES_ALL for `invoice_date`)
- **NO `supplier_name`** — must chain JOIN via AP_INVOICES_ALL → AP_SUPPLIERS
- **NO `line_type`** — use `line_type_lookup_code`

#### ai_financial_dlp.CONTRACT_METADATA
`ironclad_id`, `contract_name`, `contract_type`, `counterparty_name`, `agreement_date`, `effective_date`, `expiration_date`, `anniversary_date`, `renewal_type`, `renewal_term_length`, `initial_term_length`, `contract_value_amount`, `contract_value_currency`, `contract_status`, `remaining_duration`, `hierarchy_type`, `agreement_type`, `business_group`, `last_updated`
- **NO `contract_id`** — use `ironclad_id`
- **NO `supplier_name`** — use `counterparty_name`
- **NO `supplier_name_normalized`** — use `counterparty_name` with UPPER()
- **NO `status`** — use `contract_status`
- **NO `auto_renewal`** — use `renewal_type` (values: Auto-Renew, Evergreen, Manual)

#### sco_rage_invoice_extract_ds.invoice_extracts
`document_id`, `invoice_number`, `vendor`, `manufacturer_name`, `invoice_date`, `total_amount`, `extraction_confidence`, `line_items` (REPEATED: `sku_or_service`, `description`, `quantity`, `unit_price`, `amount`, `category`)
- **MUST use `UNNEST(line_items) AS line_item`** to access nested fields
- **NO `supplier_name`** — use `vendor`
- **NO `supplier_name_normalized`** — use `vendor`
- **NO `vendor_name`** — use `vendor`
- **NO `invoice_amount`** — use `total_amount`
- **NO `amount`** (top-level) — use `total_amount` (amount is only inside line_items)
- **NO `manufacturer`** — use `manufacturer_name`

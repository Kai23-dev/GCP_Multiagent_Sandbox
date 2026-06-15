Purchasing & Supplier Tables

## Maverick Purchase Detection

A **maverick** purchase is an invoice that entered Accounts Payable WITHOUT a Purchase Order. A **proper** purchase flows: Catalog → Purchase Order → AP → General Ledger.

### How to Detect Maverick

An invoice is maverick when it has no PO reference. Check these columns:

| Table | Column(s) | Maverick When |
|---|---|---|
| AP_INVOICES_ALL | po_header_id | IS NULL or = 'N/A' |
| AP_INVOICE_LINES_ALL | po_header_id | IS NULL or = 'N/A' |
| XXC_GL_SUMMARY | po_number | IS NULL or = 'N/A' |

**Key rules:**
- Best single indicator: `AP_INVOICES_ALL.po_header_id IS NULL OR = 'N/A` (header-level) or `AP_INVOICE_LINES_ALL.po_header_id IS NULL OR = 'N/A` (line-level).

**Proper Path:** AP_INVOICES_ALL.po_header_id → PO_HEADERS_ALL.po_header_id → PO_LINES_ALL (via po_header_id) → optionally COUPA_CATALOG/IPRO_CATALOG for catalog origin.

**Maverick Path (no PO tables):** AP_INVOICES_ALL → AP_INVOICE_LINES_ALL (via invoice_id) → AP_INVOICE_DISTRIBUTIONS_ALL (via invoice_id) → XXC_GL_SUMMARY (via invoice_id).

### SQL Pattern

**Classify a specific invoice (header + line-level maverick detection):**
Check both header and line-level PO references:
```sql
SELECT 
  COALESCE(h.invoice_id, l.invoice_id) AS invoice_id,
  h.invoice_number,
  h.po_header_id AS header_po_id,
  l.po_header_id AS line_po_id,
  l.line_number,
  CASE WHEN h.po_header_id IS NULL OR h.po_header_id = 'N/A' THEN 'Maverick' ELSE 'Proper' END AS header_route,
  CASE WHEN l.po_header_id IS NULL OR l.po_header_id = 'N/A' THEN 'Maverick' ELSE 'Proper' END AS line_route
FROM `ai_financial_dlp.AP_INVOICES_ALL` h
FULL OUTER JOIN `ai_financial_dlp.AP_INVOICE_LINES_ALL` l 
  ON h.invoice_id = l.invoice_id
WHERE h.invoice_id = @invoice_num 
   OR h.invoice_number = @invoice_num
   OR l.invoice_id = @invoice_num
   AND TRIM(ai.org_id) = '0'
   AND COALESCE(TRIM(ail.discarded_flag), 'N') = 'N'
   AND COALESCE(TRIM(ail.cancelled_flag), 'N') = 'N'
   AND ai.cancelled_date IS NULL
ORDER BY l.line_number
```

## Item Description
Use case when user asks for an item:
- who bought it from PO perspective?
- for how much?
- who sold it?

### SQL Pattern

```sql
-- Uses TRIM on line_number, discarded_flag and cancelled_flag to strip trailing whitespace from stored values.
-- All columns are STRING. All joins are LEFT JOIN.
--
-- Usage:
--   @search_value — invoice_id OR invoice_number (STRING)
--   @line_number  — line number (STRING, e.g. '7')

SELECT DISTINCT
  ail.invoice_id,
  ai.invoice_number,
  COALESCE(ail.po_header_id, ai.po_header_id) AS po_header_id,
  ph.po_number,
  TRIM(ail.line_number) as line_number,
  ail.line_type,
  ail.line_source,
  ail.line_amount,
  ail.description,
  ail.item_description,
  ail.inventory_item_id,
  ail.accounting_date,
  ail.period_name,
  ail.gl_code_combination_id,
  ail.po_line_id,
  ail.receipt_transaction_id,
  TRIM(ail.discarded_flag) AS discarded_flag,
  TRIM(ail.cancelled_flag) AS cancelled_flag,
  ail.source_system,
  ai.currency_code,
  ai.vendor_id,
  sup.vendor_number,
  sup.supplier_name,
  sup.vendor_type,
  sup.is_active,
  ph.buyer_id
FROM
  `ai_financial_dlp.AP_INVOICE_LINES_ALL`   AS ail
LEFT JOIN
  `ai_financial_dlp.AP_INVOICES_ALL`         AS ai
  ON ail.invoice_id = ai.invoice_id
LEFT JOIN
  `ai_financial_dlp.PO_HEADERS_ALL`          AS ph
  ON COALESCE(ail.po_header_id, ai.po_header_id) = ph.po_header_id
LEFT JOIN
  `ai_financial_dlp.AP_SUPPLIERS`            AS sup
  ON ai.vendor_id = sup.vendor_id
WHERE
  TRIM(ail.line_number) = @line_number
  AND (
    ail.invoice_id = @search_value
    OR ai.invoice_number = @search_value
  )
  AND TRIM(ai.org_id) = '0'
```

# Important info 
**CRITICAL:** You have to entirely follow SQL Pattern for detailed use case to provide user with high quality response. Do not add any column or where statement.
**CRITICAL:** Before response - check if provided sql generated query follows SQL Pattern.

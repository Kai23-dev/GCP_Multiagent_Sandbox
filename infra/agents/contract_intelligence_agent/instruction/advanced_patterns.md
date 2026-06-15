## Advanced SQL Patterns (CIA Reference)

These patterns are used by comparison, reconciliation, and recommendation sub-agents for complex analysis. The root agent should delegate complex SQL work to sub-agents rather than executing these directly.

### Pattern 1: Three-Way Price Match (Contract -> PO -> Invoice)

When contract pricing is found, validate across all three sources:

```sql
SELECT
    p.vendor_product_num AS sku,
    p.item_description,
    p.unit_price AS po_price,
    p.unit_of_measure,
    ci.unit_price AS invoice_price,
    ROUND(ci.unit_price - p.unit_price, 2) AS po_vs_invoice_variance,
    ROUND((ci.unit_price - p.unit_price) / NULLIF(p.unit_price, 0) * 100, 2) AS variance_pct
FROM ai_financial_dlp.PO_LINES_ALL p
JOIN ai_financial_dlp.PO_HEADERS_ALL h ON p.po_header_id = h.po_header_id
JOIN ai_financial_dlp.AP_SUPPLIERS s ON h.vendor_id = s.vendor_id
LEFT JOIN ai_financial_dlp.COUPA_INVOICES ci
    ON ci.supplier_name_normalized = s.supplier_name_normalized
    AND ci.item_description LIKE CONCAT('%', SUBSTR(p.item_description, 1, 20), '%')
WHERE s.supplier_name_normalized LIKE '%<SUPPLIER>%'
  AND p.unit_price > 0
ORDER BY variance_pct DESC
LIMIT 50
```

Then compare contract price (from RAG) against both PO and invoice prices.
This catches: PO created at wrong price AND invoice diverging from PO.

### Pattern 2: Catalog Price as Baseline (when no contract)

When no contract pricing is found, use catalog prices instead of MIN invoice:

```sql
SELECT
    cat.davita_item_number,
    cat.item_description,
    cat.price AS catalog_price,
    cat.unit_of_measure,
    AVG(o.unit_price) AS avg_invoice_price,
    MIN(o.unit_price) AS min_invoice_price,
    MAX(o.unit_price) AS max_invoice_price,
    COUNT(*) AS order_count,
    ROUND((AVG(o.unit_price) - cat.price) / NULLIF(cat.price, 0) * 100, 2) AS avg_variance_pct
FROM ai_financial_dlp.IPRO_CATALOG cat
JOIN ai_financial_dlp.IPRO_ORDERS o
    ON cat.vendor_name_normalized = o.vendor_name_normalized
    AND o.item_description LIKE CONCAT('%', SUBSTR(cat.item_description, 1, 20), '%')
WHERE cat.vendor_name_normalized LIKE '%<SUPPLIER>%'
  AND cat.effective_date_to >= CURRENT_DATE()
  AND o.unit_price > 0
GROUP BY cat.davita_item_number, cat.item_description, cat.price, cat.unit_of_measure
HAVING AVG(o.unit_price) > cat.price * 1.05
ORDER BY avg_variance_pct DESC
```

### Pattern 3: SKU-Level Price Match via invoice_extracts

Match SKUs from P8-extracted invoices to catalog items:

```sql
SELECT
    ie.vendor,
    ie.invoice_number,
    li.sku_or_service,
    li.description,
    li.unit_price AS invoice_unit_price,
    li.quantity,
    cat.price AS catalog_price,
    cat.unit_of_measure,
    ROUND(li.unit_price - cat.price, 2) AS price_variance
FROM sco_rage_invoice_extract_ds.invoice_extracts ie,
     UNNEST(ie.line_items) AS li
LEFT JOIN ai_financial_dlp.IPRO_CATALOG cat
    ON cat.manufacturer_part_number = li.sku_or_service
WHERE ie.vendor LIKE '%<SUPPLIER>%'
  AND (ie.extraction_confidence > 0.8 OR ie.extraction_confidence IS NULL)
  AND li.unit_price > 0
  AND cat.price IS NOT NULL
ORDER BY price_variance DESC
```

### Pattern 4: Volume Commitment Tracking

Track spend against blanket PO commitments:

```sql
SELECT
    s.supplier_name_normalized,
    h.po_number,
    h.po_type,
    h.blanket_total_amount AS committed_amount,
    SUM(ci.invoice_amount) AS actual_spend,
    ROUND(SUM(ci.invoice_amount) / NULLIF(h.blanket_total_amount, 0) * 100, 2) AS utilization_pct,
    h.end_date AS commitment_end_date
FROM ai_financial_dlp.PO_HEADERS_ALL h
JOIN ai_financial_dlp.AP_SUPPLIERS s ON h.vendor_id = s.vendor_id
LEFT JOIN ai_financial_dlp.COUPA_INVOICES ci
    ON ci.supplier_name_normalized = s.supplier_name_normalized
WHERE s.supplier_name_normalized LIKE '%<SUPPLIER>%'
  AND h.po_type = 'BLANKET'
  AND h.is_cancelled = FALSE
GROUP BY s.supplier_name_normalized, h.po_number, h.po_type, h.blanket_total_amount, h.end_date
```

### Pattern 5: Facility-Level Pricing (for service contracts)

For facility services contracts (cleaning, security, maintenance):

```sql
SELECT
    f.facility_id,
    f.facility_common_name,
    f.division,
    f.region,
    ci.supplier_name_normalized,
    COUNT(DISTINCT ci.invoice_id) AS invoice_count,
    SUM(ci.invoice_amount) AS total_spend,
    COUNT(DISTINCT EXTRACT(MONTH FROM ci.invoice_date)) AS months_billed,
    ROUND(SUM(ci.invoice_amount) / NULLIF(COUNT(DISTINCT EXTRACT(MONTH FROM ci.invoice_date)), 0), 2) AS avg_monthly
FROM ai_financial_dlp.XXC_GL_DIV_REG_FAC f
JOIN ai_financial_dlp.COUPA_INVOICES ci ON CAST(f.facility_id AS STRING) = ci.facility_number
WHERE ci.supplier_name_normalized LIKE '%<SUPPLIER>%'
  AND f.is_active = TRUE
GROUP BY f.facility_id, f.facility_common_name, f.division, f.region, ci.supplier_name_normalized
ORDER BY total_spend DESC
```

Compare `avg_monthly` against the contract's per-facility rate (from RAG).

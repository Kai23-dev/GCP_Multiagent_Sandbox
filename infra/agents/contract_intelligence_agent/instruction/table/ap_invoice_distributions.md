# AP_INVOICE_DISTRIBUTIONS_ALL

**Dataset:** ai_financial_dlp
**Purpose:** Invoice accounting distributions - **CRITICAL for price comparison**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| distribution_id | INT64 | Primary key | Unique identifier |
| invoice_id | INT64 | FK to AP_INVOICES_ALL | Join to invoice header |
| invoice_line_number | INT64 | Line number reference | Line identification |
| **unit_price** | NUMERIC | **Unit price** | **Compare to contract price** |
| **quantity_invoiced** | NUMERIC | **Quantity invoiced** | **Calculate overcharge amount** |
| distribution_amount | NUMERIC | Distribution amount | Line total |
| base_amount | NUMERIC | Base currency amount | Currency normalization |
| accounting_date | DATE | Accounting date | Date filtering |
| period_name | STRING | GL period name | Period filtering |
| description | STRING | Description | Item identification |

## Sample Query

```sql
SELECT
    d.invoice_id,
    d.unit_price,
    d.quantity_invoiced,
    d.distribution_amount,
    s.supplier_name
FROM ai_financial_dlp.AP_INVOICE_DISTRIBUTIONS_ALL d
JOIN ai_financial_dlp.AP_INVOICES_ALL i ON d.invoice_id = i.invoice_id
JOIN ai_financial_dlp.AP_SUPPLIERS s ON i.vendor_id = s.vendor_id
WHERE s.supplier_name_normalized LIKE '%MEDLINE%'
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| unit_price | 5.25, 12.99, 78.14, 2000.00 |
| quantity_invoiced | 100, 250, 1, 42500 |
| distribution_amount | 525.00, 3247.50, 78.14, 85000.00 |
| period_name | JAN-25, FEB-25, MAR-25 |

## Join Considerations

- **To AP_INVOICES_ALL**: Join on `invoice_id` (required to get vendor_id)
- **To AP_SUPPLIERS**: Chain join via AP_INVOICES_ALL.vendor_id
- **To Contracts**: Compare `unit_price` against contract pricing from RAG
- **Price Variance**: Calculate as `(invoice_unit_price - contract_unit_price) * quantity_invoiced`

## Notes

- This table contains **unit_price** which is critical for contract price comparison
- Join via invoice_id to AP_INVOICES_ALL for vendor information
- Use for line-level price analysis
- **Key table for price discrepancy detection**

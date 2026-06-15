# AP_INVOICES_ALL

**Dataset:** ai_financial_dlp
**Purpose:** Oracle invoice headers - **CRITICAL for joining distributions to suppliers**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| invoice_id | INT64 | Primary key | **Join key for distributions** |
| **vendor_id** | INT64 | FK to AP_SUPPLIERS | **Link to supplier** |
| vendor_site_id | INT64 | FK to AP_SUPPLIER_SITES_ALL | Site reference |
| invoice_number | STRING | Invoice number | Invoice identification |
| po_header_id | INT64 | FK to PO_HEADERS_ALL | PO linkage |
| invoice_date | DATE | Invoice date | Date filtering |
| gl_date | DATE | GL posting date | Period filtering |
| invoice_amount | NUMERIC | Total invoice amount | Amount analysis |
| amount_paid | NUMERIC | Amount already paid | Payment status |
| currency_code | STRING | Currency code (USD) | Currency validation |
| invoice_type | STRING | Invoice type code | Type filtering |
| payment_status_flag | STRING | Payment status (Y/N/P) | Status filtering |
| description | STRING | Invoice description | Context |

## Sample Query

```sql
-- Get invoice headers with supplier info
SELECT
    i.invoice_id,
    i.invoice_number,
    i.invoice_date,
    i.invoice_amount,
    s.supplier_name,
    s.supplier_name_normalized
FROM ai_financial_dlp.AP_INVOICES_ALL i
JOIN ai_financial_dlp.AP_SUPPLIERS s ON i.vendor_id = s.vendor_id
WHERE s.supplier_name_normalized LIKE '%MEDLINE%'
  AND i.invoice_date >= '2024-01-01'
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| invoice_number | INV-2025-001; VANCAP_TAXSUM__42516697 |
| invoice_amount | 6.52, 30.60, 15000.00 |
| invoice_type | STANDARD, CREDIT |
| payment_status_flag | Y (Paid), N (Not Paid), P (Partial) |

## Join Considerations

- **To AP_INVOICE_DISTRIBUTIONS_ALL**: Join on `invoice_id` (parent-child relationship)
- **To AP_SUPPLIERS**: Join on `vendor_id` (CRITICAL for supplier identification)
- **To PO_HEADERS_ALL**: Join on `po_header_id` (for PO-matched invoices)
- **Bridge Table**: This table bridges invoice line items to supplier master data

## Notes

- **CRITICAL TABLE** - Required to join invoice distributions to suppliers
- vendor_id is the immutable link to AP_SUPPLIERS (never use vendor_name for joins)
- Use invoice_date for date filtering, gl_date for GL period filtering
- Check payment_status_flag: Y=Fully Paid, N=Not Paid, P=Partially Paid

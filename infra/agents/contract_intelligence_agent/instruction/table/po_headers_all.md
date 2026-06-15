# PO_HEADERS_ALL

**Dataset:** ai_financial_dlp
**Purpose:** Oracle PO headers - **CRITICAL for joining PO lines to suppliers**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| po_header_id | INT64 | Primary key | **Join key for PO lines** |
| **vendor_id** | INT64 | FK to AP_SUPPLIERS | **Link to supplier** |
| vendor_site_id | INT64 | FK to AP_SUPPLIER_SITES_ALL | Site reference |
| po_number | STRING | Purchase order number | PO identification |
| po_type | STRING | PO type (STANDARD, BLANKET) | Type filtering |
| currency_code | STRING | Currency code | Currency validation |
| blanket_total_amount | NUMERIC | Blanket PO total | **Commitment tracking** |
| amount_limit | NUMERIC | Amount limit | Commitment limit |
| start_date | DATE | PO start date | Date filtering |
| end_date | DATE | PO end date | Expiration check |
| approved_date | DATE | Approval date | Status tracking |
| authorization_status | STRING | Authorization status | Status filtering |
| is_cancelled | BOOLEAN | Cancelled flag | Active PO check |

## Sample Query

```sql
-- Get PO headers with supplier info
SELECT
    h.po_header_id,
    h.po_number,
    h.po_type,
    h.blanket_total_amount,
    h.start_date,
    h.end_date,
    s.supplier_name,
    s.supplier_name_normalized
FROM ai_financial_dlp.PO_HEADERS_ALL h
JOIN ai_financial_dlp.AP_SUPPLIERS s ON h.vendor_id = s.vendor_id
WHERE s.supplier_name_normalized LIKE '%MEDLINE%'
  AND h.is_cancelled = FALSE
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| po_number | PO-2025-001; 1234567 |
| po_type | STANDARD, BLANKET, CONTRACT |
| blanket_total_amount | 100000.00, 500000.00 |
| authorization_status | APPROVED, IN PROCESS, INCOMPLETE |

## Join Considerations

- **To PO_LINES_ALL**: Join on `po_header_id` (parent-child relationship)
- **To AP_SUPPLIERS**: Join on `vendor_id` (CRITICAL for supplier identification)
- **To AP_INVOICES_ALL**: Can be linked via `po_header_id` for PO-matched invoices
- **Bridge Table**: This table bridges PO line items to supplier master data

## Notes

- **CRITICAL TABLE** - Required to join PO lines to suppliers
- BLANKET POs have `blanket_total_amount` for commitment tracking
- Check `is_cancelled = FALSE` for active POs
- `end_date` is important for contract period validation
- **Volume Commitment**: Compare PO quantities against contract commitments

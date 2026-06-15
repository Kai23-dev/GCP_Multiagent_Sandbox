# AP_SUPPLIERS

**Dataset:** ai_financial_dlp
**Purpose:** Oracle supplier master data - **CRITICAL for supplier matching**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| vendor_id | INT64 | Primary key | FK for joins |
| vendor_number | STRING | Supplier number | Supplier reference |
| supplier_name | STRING | Supplier name (original) | Display name |
| **supplier_name_normalized** | STRING | **UPPER, TRIMMED** | **For matching** |
| vendor_type | STRING | Vendor type | Classification |
| enabled_flag | STRING | Enabled flag (Y/N) | Active check |
| is_active | BOOLEAN | Derived active status | Active check |
| start_date_active | DATE | Active start date | Date filtering |
| end_date_active | DATE | Active end date | Date filtering |
| hold_flag | STRING | Hold flag | Payment status |
| payment_terms_id | INT64 | Payment terms ID | Terms reference |

## Sample Query

```sql
-- Get all active suppliers
SELECT
    vendor_id,
    supplier_name,
    supplier_name_normalized,
    vendor_type
FROM ai_financial_dlp.AP_SUPPLIERS
WHERE is_active = TRUE
ORDER BY supplier_name
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| supplier_name | Medline Industries, LP; ACCENTURE LLP; Fresenius Kabi |
| supplier_name_normalized | MEDLINE INDUSTRIES LP; ACCENTURE LLP; FRESENIUS KABI |
| vendor_type | SUPPLIER, VENDOR, SERVICE |
| enabled_flag | Y, N |

## Join Considerations

- **To AP_INVOICES_ALL**: Join on `vendor_id` to get all invoices for a supplier
- **To COUPA_INVOICES**: Match on `supplier_name_normalized` (exact match preferred)
- **To invoice_extracts**: Fuzzy match on `vendor` field (MEDIUM reliability)
- **To Contracts (via RAG)**: Use `supplier_name_normalized` to match contract party names

## Notes

- Always use **supplier_name_normalized** for matching across systems (UPPER, TRIMMED)
- vendor_id is the primary key for joining to invoices
- Check is_active or enabled_flag for active suppliers
- supplier_name_normalized removes: punctuation, extra spaces, case differences

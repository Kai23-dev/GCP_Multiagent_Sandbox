# COUPA_INVOICES

**Dataset:** ai_financial_dlp
**Purpose:** Coupa invoices - **CRITICAL for direct contract linking**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| invoice_id | STRING | Invoice ID | Unique identifier |
| supplier_id | STRING | Supplier ID | Supplier reference |
| invoice_number | STRING | Invoice number | Invoice identification |
| **contract_name** | STRING | **Contract name** | **Direct contract link** |
| **contract_number** | STRING | **Contract number** | **Direct contract link** |
| supplier_name | STRING | Supplier name | Supplier identification |
| **supplier_name_normalized** | STRING | **Normalized name** | **For matching** |
| **unit_price** | NUMERIC | **Unit price** | **Price comparison** |
| quantity | INT64 | Quantity | Volume analysis |
| invoice_amount | NUMERIC | Invoice amount | Total amount |
| invoice_date | DATE | Invoice date | Date filtering |
| commodity_category | STRING | Commodity category | Category matching |
| item_description | STRING | Item description | Item identification |

## Sample Query

```sql
-- Find invoices with direct contract reference
SELECT
    invoice_id,
    invoice_number,
    supplier_name,
    contract_name,
    contract_number,
    unit_price,
    quantity
FROM ai_financial_dlp.COUPA_INVOICES
WHERE contract_number IS NOT NULL
  AND supplier_name_normalized LIKE '%MEDLINE%'
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| contract_name | Medline Master Agreement 2024; Accenture MSA-SOW-001 |
| contract_number | MSA-2024-001; ENT-2023-456 |
| supplier_name_normalized | MEDLINE INDUSTRIES LP; ACCENTURE LLP |
| unit_price | 5.25, 12.99, 78.14 |
| commodity_category | Medical Supplies, IT Services, Facilities |

## Join Considerations

- **To AP_SUPPLIERS**: Match on `supplier_name_normalized` (exact match)
- **To Contracts (via RAG)**: Use `contract_number` for HIGH reliability match
- **To AP_INVOICES_ALL**: Match on `invoice_number` if available
- **Direct Contract Link**: This table has the BEST contract-to-invoice linking via `contract_number`

## Notes

- **contract_number** is the most reliable contract link (HIGH reliability)
- Use **supplier_name_normalized** for consistent supplier matching
- Contains both contract reference and unit_price for direct comparison
- **Preferred source** for contract-linked invoice analysis

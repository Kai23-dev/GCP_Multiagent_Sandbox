# invoice_extracts

**Dataset:** sco_rage_invoice_extract_ds
**Purpose:** P8 extracted invoices - **SKU-level price comparison**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| document_id | STRING | P8 document ID | Document reference |
| invoice_number | STRING | Invoice number | Match to AP_INVOICES_ALL |
| **vendor** | STRING | Vendor name | **Fuzzy match to contracts** |
| invoice_date | DATE | Invoice date | Date filtering |
| total_amount | NUMERIC | Invoice total | Total validation |
| manufacturer_name | STRING | Manufacturer | Manufacturer info |
| **line_items** | REPEATED RECORD | **Line item details** | **SKU-level data** |
| extraction_confidence | FLOAT | Quality indicator | Filter by >0.8 for high quality |

## Line Items Structure (REPEATED)

| Field | Type | Description | CIA Use |
|-------|------|-------------|---------|
| **sku_or_service** | STRING | **SKU/item code** | **Match to contract SKU** |
| description | STRING | Item description | Item identification |
| quantity | NUMERIC | Quantity | Volume analysis |
| **unit_price** | NUMERIC | **Unit price** | **Price comparison** |
| amount | NUMERIC | Line amount | Line total |
| category | STRING | Category | Category validation |

## Sample Query

```sql
-- Get line items with unit prices
SELECT
    document_id,
    invoice_number,
    vendor,
    line_item.sku_or_service,
    line_item.description,
    line_item.quantity,
    line_item.unit_price,
    line_item.amount
FROM sco_rage_invoice_extract_ds.invoice_extracts,
UNNEST(line_items) as line_item
WHERE vendor LIKE '%MEDLINE%'
  AND extraction_confidence > 0.8
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| vendor | Medline Industries LP; ACCENTURE; Fresenius |
| invoice_number | INV-2025-001; 42516697; PO-12345 |
| extraction_confidence | 0.95, 0.87, 0.72 |
| line_items.sku_or_service | MED-GLV-001; SVC-CONSULT-HR; CHR-ENT-001 |
| line_items.unit_price | 5.25, 150.00, 78.14 |

## Join Considerations

- **To AP_INVOICES_ALL**: Match on `invoice_number` (may require normalization)
- **To AP_SUPPLIERS**: Fuzzy match on `vendor` field (MEDIUM reliability)
- **To Contracts (via RAG)**: Match `line_items.sku_or_service` to contract SKUs
- **SKU-Level Comparison**: Best source for SKU-to-contract price matching

## Notes

- **REPEATED structure** - use UNNEST for line_items
- Use **extraction_confidence > 0.8** for reliable data
- **vendor** field requires fuzzy matching (MEDIUM reliability)
- Contains SKU-level pricing not available in Oracle AP tables
- **Best source for SKU-level contract price comparison**

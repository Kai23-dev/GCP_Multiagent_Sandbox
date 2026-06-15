# PO_LINES_ALL

**Dataset:** ai_financial_dlp
**Purpose:** Oracle PO lines - **SKU matching for contract comparison**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| po_line_id | INT64 | Primary key | Unique identifier |
| po_header_id | INT64 | FK to PO_HEADERS_ALL | Join to PO header |
| item_id | INT64 | Item ID | Item reference |
| category_id | INT64 | Category ID | Category reference |
| line_number | INT64 | Line number | Line identification |
| item_description | STRING | Item description | Item identification |
| **vendor_product_num** | STRING | **Vendor product number** | **SKU matching** |
| **unit_price** | NUMERIC | **Unit price** | **Price comparison** |
| base_unit_price | NUMERIC | Base unit price | Base price reference |
| list_price | NUMERIC | List price | List price reference |
| unit_of_measure | STRING | Unit of measure | UOM validation |
| **quantity** | NUMERIC | Quantity | **Volume tracking** |
| quantity_committed | NUMERIC | Quantity committed | Commitment tracking |
| closed_status | STRING | Closed status | Status filtering |
| expiration_date | DATE | Expiration date | Date filtering |

## Sample Query

```sql
-- Get PO lines with SKU and pricing
SELECT
    p.po_line_id,
    h.po_number,
    s.supplier_name,
    p.vendor_product_num,
    p.item_description,
    p.unit_price,
    p.quantity
FROM ai_financial_dlp.PO_LINES_ALL p
JOIN ai_financial_dlp.PO_HEADERS_ALL h ON p.po_header_id = h.po_header_id
JOIN ai_financial_dlp.AP_SUPPLIERS s ON h.vendor_id = s.vendor_id
WHERE s.supplier_name_normalized LIKE '%MEDLINE%'
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| vendor_product_num | MED-GLV-001; SKU-12345; PART-ABC |
| item_description | Exam Gloves Large; Chrome Enterprise License; Maintenance Parts |
| unit_price | 5.25, 78.14, 150.00 |
| quantity | 1000, 42500, 50 |
| unit_of_measure | EA, BX, CS |

## Join Considerations

- **To PO_HEADERS_ALL**: Join on `po_header_id` (required to get vendor_id)
- **To AP_SUPPLIERS**: Chain join via PO_HEADERS_ALL.vendor_id
- **To Contracts (via RAG)**: Match `vendor_product_num` to contract SKUs
- **Commitment Tracking**: Compare `quantity` against contract volume commitments

## Notes

- **vendor_product_num** is the SKU for matching to contract items
- Use for volume commitment tracking (quantity vs contract commitment)
- Join via po_header_id to PO_HEADERS_ALL for vendor information
- **Key table for volume commitment analysis**

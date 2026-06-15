# IPRO_ORDERS

**Dataset:** ai_financial_dlp
**Purpose:** iProcurement purchase orders - **DIRECT spend (medical/dialysis)**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| **po_number** | STRING | Purchase order number (PK) | Order reference |
| vendor_id | INT64 | Vendor ID (FK) | Supplier reference |
| **vendor_name_normalized** | STRING | Normalized vendor name | **Supplier matching** |
| vendor_name | STRING | Vendor name | Supplier identification |
| **unit_price** | FLOAT64 | Unit price | **Price comparison** |
| **quantity_ordered** | INT64 | Quantity ordered | Volume analysis |
| quantity_received | INT64 | Quantity received | Fulfillment analysis |
| **amount_ordered** | FLOAT64 | Total amount (unit_price × quantity) | **Spend analysis** |
| amount_received | FLOAT64 | Total amount received | Fulfillment analysis |
| order_date | DATE | Order date | Date filtering |
| need_by_date | DATE | Need-by date | Lead time analysis |
| item_description | STRING | Item description | Item identification |
| **davita_item_number** | STRING | DaVita item number | **SKU match to IPRO_CATALOG** |
| product_number | STRING | Manufacturer part number | Product reference |
| manufacturer | STRING | Manufacturer name | Manufacturer reference |
| facility_id | STRING | Facility ID | Facility filtering |
| facility_name | STRING | Facility name | Facility identification |
| **category1** | STRING | Category level 1 | **Category matching** |
| category2 | STRING | Category level 2 | Category detail |
| category3 | STRING | Category level 3 | Category detail |
| product_category | STRING | Product category | Category reference |
| unit_of_measure | STRING | Unit of measure | UOM validation |
| eaches | INT64 | Individual units per case | UOM conversion |
| eaches_uom | STRING | UOM for individual units | UOM conversion |
| closed_code | STRING | Order closure status | Status filtering |
| year | INT64 | Order year | Date filtering |
| month | INT64 | Order month | Date filtering |
| year_month | STRING | Year-month (YYYY/MM) | Period filtering |

## Sample Query

```sql
-- Get orders for a supplier with pricing
SELECT
    po_number,
    vendor_name_normalized,
    item_description,
    unit_price,
    quantity_ordered,
    amount_ordered,
    order_date
FROM ai_financial_dlp.IPRO_ORDERS
WHERE vendor_name_normalized LIKE '%MEDLINE%'
  AND unit_price > 0
ORDER BY order_date DESC
LIMIT 100
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| po_number | 6089-24251, 95080-1113486 |
| vendor_name_normalized | CARSTENS CORPORATION, FRESENIUS USA INC |
| unit_price | 15.89, 12.15, 13.46 |
| quantity_ordered | 11, 15, 9 |
| amount_ordered | 174.79, 182.25, 121.14 |
| category1 | Office, Med Supplies |
| category2 | Binders & Binder Accessories, Dialysate |

## CRITICAL: Type Differences vs COUPA_INVOICES

**When writing UNION ALL between COUPA_INVOICES and IPRO_ORDERS, you MUST CAST columns to matching types:**

| Column Purpose | COUPA_INVOICES | IPRO_ORDERS | UNION ALL Safe Type |
|---------------|----------------|-------------|-------------------|
| ID | invoice_id (STRING) | po_number (STRING) | STRING ✅ |
| Supplier | supplier_name_normalized (STRING) | vendor_name_normalized (STRING) | STRING ✅ |
| Unit Price | unit_price (NUMERIC) | unit_price (FLOAT64) | **CAST both AS BIGNUMERIC** |
| Quantity | quantity (INT64) | quantity_ordered (INT64) | INT64 ✅ |
| Amount | invoice_amount (NUMERIC) | amount_ordered (FLOAT64) | **CAST both AS BIGNUMERIC** |
| Date | invoice_date (DATE) | order_date (DATE) | DATE ✅ |
| Description | item_description (STRING) | item_description (STRING) | STRING ✅ |
| Category | commodity_category (STRING) | category1 (STRING) | STRING ✅ |

## Join Considerations

- **To IPRO_CATALOG**: Join on `davita_item_number` for catalog-vs-invoice comparison
- **To AP_SUPPLIERS**: Join on `vendor_id` for complete vendor info
- **To XXC_GL_DIV_REG_FAC**: Join on `facility_id` for facility/division reporting
- **To PO_LINES_ALL**: Match `product_number` to `vendor_product_num`

## Notes

- **DIRECT spend** — medical supplies, dialysis equipment (vs COUPA = INDIRECT)
- 4.4M+ records — always use filters and LIMIT
- `unit_price` is FLOAT64 (not NUMERIC like COUPA) — **CAST in UNION ALL**
- `amount_ordered` is FLOAT64 — may need SAFE_CAST for calculations
- Use `vendor_name_normalized` for consistent supplier matching
- `davita_item_number` links to IPRO_CATALOG for catalog price comparison

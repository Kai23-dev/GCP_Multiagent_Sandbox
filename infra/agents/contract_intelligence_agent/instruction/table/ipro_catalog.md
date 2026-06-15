# IPRO_CATALOG

**Dataset:** ai_financial_dlp
**Purpose:** iProcurement catalog items - **Item master for SKU matching**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| **davita_item_number** | STRING | DaVita item number (PK) | **SKU matching** |
| item_description | STRING | Item description | Item identification |
| model_number | STRING | Model number | Product reference |
| **manufacturer_part_number** | STRING | Manufacturer part number | **Contract SKU match** |
| **price** | NUMERIC | Catalog price | **Price comparison** |
| unit_of_measure | STRING | Unit of measure | UOM validation |
| pack_factor | INT64 | Pack factor | UOM conversion |
| ndc_code | STRING | NDC code (pharmaceutical) | Drug reference |
| **po_category_1** | STRING | PO category level 1 | **Category matching** |
| **po_category_2** | STRING | PO category level 2 | **Category matching** |
| po_category_3 | STRING | PO category level 3 | Category detail |
| product_category | STRING | Product category | Category reference |
| **vendor_name_normalized** | STRING | Vendor name (normalized) | **Supplier matching** |
| vendor_site | STRING | Vendor site | Site reference |
| effective_date_from | DATE | Effective date from | Date filtering |
| effective_date_to | DATE | Effective date to | Date filtering |
| modality | STRING | Modality | Treatment type |

## Sample Query

```sql
-- Get catalog items for a supplier
SELECT
    davita_item_number,
    item_description,
    manufacturer_part_number,
    price,
    unit_of_measure,
    po_category_1,
    po_category_2
FROM ai_financial_dlp.IPRO_CATALOG
WHERE vendor_name_normalized LIKE '%MEDLINE%'
  AND effective_date_to >= CURRENT_DATE()
ORDER BY po_category_1, item_description
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| davita_item_number | DV-12345, DV-67890 |
| manufacturer_part_number | MED-GLV-001, FRE-IV-500 |
| price | 5.25, 12.99, 78.14 |
| unit_of_measure | EA, BX, CS |
| po_category_1 | Medical Supplies, Pharmaceuticals |
| po_category_2 | Gloves, IV Supplies |

## Join Considerations

- **To IPRO_ORDERS**: Join on `davita_item_number`
- **To PO_LINES_ALL**: Match `manufacturer_part_number` to `vendor_product_num`
- **To invoice_extracts**: Match `davita_item_number` or `manufacturer_part_number` to `sku_or_service`
- **To Contracts (RAG)**: Match `davita_item_number` or `manufacturer_part_number` to contract SKUs
- **Price Master**: Catalog `price` is the expected price; compare to invoice unit_price

## Price Comparison Pattern

```sql
-- Compare catalog price vs invoice price
SELECT
    cat.davita_item_number,
    cat.item_description,
    cat.price as catalog_price,
    ie.line_item.unit_price as invoice_price,
    (ie.line_item.unit_price - cat.price) as price_variance
FROM ai_financial_dlp.IPRO_CATALOG cat
JOIN sco_rage_invoice_extract_ds.invoice_extracts ie,
     UNNEST(ie.line_items) as line_item
  ON cat.manufacturer_part_number = line_item.sku_or_service
WHERE cat.vendor_name_normalized LIKE '%MEDLINE%'
  AND ie.line_item.unit_price > cat.price
```

## Notes

- **Item Master**: Primary source for DaVita item numbers and catalog prices
- Use `effective_date_from/to` to ensure item is currently valid
- `manufacturer_part_number` may match contract SKUs better than `davita_item_number`
- `modality` helps filter items by treatment type (dialysis, etc.)
- Contains pack_factor for UOM conversion calculations

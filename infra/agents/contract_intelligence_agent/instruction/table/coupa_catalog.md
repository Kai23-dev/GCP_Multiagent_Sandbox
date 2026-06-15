# COUPA_CATALOG

**Dataset:** ai_financial_dlp
**Purpose:** Coupa catalog items - **Item matching for contract compliance**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| **item_id** | STRING | Item ID | **SKU reference** |
| supplier_id | STRING | Supplier ID | Supplier reference |
| **commodity_id** | STRING | Commodity ID | **Category matching** |
| catalog_id | STRING | Catalog ID | Catalog reference |
| **item_description** | STRING | Item description | **Item matching** |
| **commodity_name** | STRING | Commodity name | **Category matching** |
| commodity_custom_field_3 | STRING | Custom field 3 | Additional categorization |
| commodity_custom_field_4 | STRING | Custom field 4 | Additional categorization |
| **supplier_name_normalized** | STRING | Supplier name (normalized) | **Supplier matching** |
| catalog_start_date | DATE | Catalog start date | Date filtering |
| catalog_end_date | DATE | Catalog end date | Date filtering |

## Sample Query

```sql
-- Get catalog items by supplier and commodity
SELECT
    item_id,
    item_description,
    commodity_name,
    supplier_name_normalized,
    catalog_start_date,
    catalog_end_date
FROM ai_financial_dlp.COUPA_CATALOG
WHERE supplier_name_normalized LIKE '%MEDLINE%'
  AND catalog_end_date >= CURRENT_DATE()
ORDER BY commodity_name, item_description
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| item_id | COUPA-12345, COUPA-67890 |
| item_description | Exam Gloves Large; Surgical Masks |
| commodity_name | Medical Supplies, PPE, Cleaning |
| supplier_name_normalized | MEDLINE INDUSTRIES LP |

## Join Considerations

- **To COUPA_INVOICES**: Match `item_id` or `item_description`
- **To COUPA_ORDERS**: Match on `item_description` or commodity
- **To Contracts (RAG)**: Match `commodity_name` to contract categories
- **Category Validation**: Verify invoice commodity matches catalog commodity

## Category Matching Pattern

```sql
-- Validate invoice categories against catalog
SELECT
    ci.invoice_id,
    ci.item_description as invoice_item,
    ci.commodity_category as invoice_category,
    cc.commodity_name as catalog_category,
    CASE WHEN ci.commodity_category = cc.commodity_name
         THEN 'MATCH' ELSE 'MISMATCH' END as category_status
FROM ai_financial_dlp.COUPA_INVOICES ci
LEFT JOIN ai_financial_dlp.COUPA_CATALOG cc
  ON ci.supplier_name_normalized = cc.supplier_name_normalized
  AND ci.item_description LIKE CONCAT('%', cc.item_description, '%')
WHERE ci.supplier_name_normalized LIKE '%MEDLINE%'
```

## Notes

- Use `catalog_end_date >= CURRENT_DATE()` for active catalog items
- `commodity_name` aligns with contract category hierarchies
- `item_description` may differ slightly from invoice descriptions (fuzzy match needed)
- Coupa catalogs are maintained by procurement team
- Contains supplier-catalog relationships for vendor management

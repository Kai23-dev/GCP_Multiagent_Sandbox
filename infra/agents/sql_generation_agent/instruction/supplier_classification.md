**Additional Instructions:**

When the user asks questions about a spend category, you must determine whether they are asking about an **L1, L2, L3, or L4** category to route the query correctly:
- **L1** (e.g., "Direct", "Corporate & Professional Services") and **L2** (e.g., "Pharma", "Advertising") categories: Query the `SPEND_TAXONOMY` table and join it to `XXC_GL_SUMMARY` using the `Account` field.
- **L3** (e.g., "6800 - R&M Dialysis Machine"): This corresponds to the `ACCOUNT` column in `XXC_GL_SUMMARY` and the `Account` field in `SPEND_TAXONOMY`.
- **L4** (e.g., "Dialysis Chairs", "Web Cameras", "Minor Equipment"): The parent agent will provide you with exact `PRISM Commodity Name` values via its hierarchical taxonomy tools (`get_taxonomy_categories` → `get_taxonomy_items`). Generate SQL against `invoice_extracts_prepared` filtering by `line_item.category IN (...)` with the exact values provided. Use `UNNEST(line_items) AS line_item` to access the nested line item data. **Do NOT query SPEND_TAXONOMY yourself** - the parent agent has already identified the relevant L4 categories.

**Special Case - Unknown/Uncategorized Spend:** If the user asks to identify suppliers or spend lines that don't fit any existing categories, simply filter `invoice_extracts_prepared` where `line_item.category = 'Unknown'`. 

Before you generate SQL, please check the value in the date-related columns and use the appropriate format.
For the `invoice_extracts_prepared` table, the `invoice_date` is already a DATE type. Use standard date filtering like `invoice_date BETWEEN '2024-01-01' AND '2024-12-31'`.
If the user asks for "2024/2025 spend", use `EXTRACT(YEAR FROM invoice_date) IN (2024, 2025)`.

When searching for specific vendors or suppliers, note that `vendor` in the `invoice_extracts_prepared` table is OCR-extracted text and may contain variations (e.g., "McKesson" vs "McKesson Inc"). For aggregated financial reporting, rely on `supplier_name` from `AP_SUPPLIERS` mapped through `AP_INVOICES_ALL` wherever possible to ensure normalized grouping.

**Important:** The `invoice_extracts_prepared` table uses a nested array structure for line items. Always use `UNNEST(line_items) AS line_item` to access line-level data like `line_item.category`, `line_item.amount`, `line_item.description`, `line_item.unit_price`, and `line_item.quantity`.

**CRITICAL - UNNEST Syntax Rules:**
When using `UNNEST(t1.line_items) AS line_item`, reference fields using ONLY the UNNEST alias:

✅ **CORRECT:**
- `line_item.amount`
- `line_item.category`
- `line_item.description`
- `WHERE line_item.category IN (...)`
- `SUM(SAFE_CAST(line_item.amount AS NUMERIC))`

❌ **INCORRECT - Will cause "Name line_item not found" error:**
- `t1.line_item.amount` (combining parent table alias with UNNEST alias)
- `t1.line_item.category`
- `WHERE t1.line_item.category IN (...)`
- `SUM(SAFE_CAST(t1.line_item.amount AS NUMERIC))`

The UNNEST alias (`line_item`) creates a new row context - you cannot prefix it with the parent table alias (`t1`).

Please use `SAFE_CAST` function for all number values (like `line_item.amount`, `total_amount`, `line_item.unit_price`) in the SQL to prevent execution errors on dirty parsed data.

**Dataset Mapping:**
Tables are distributed across the following datasets. Always use fully qualified names:
- **ai_financial_dlp**: XXC_GL_SUMMARY, XXC_GL_DIV_REG_FAC, AP_INVOICES_ALL, AP_SUPPLIERS, AP_INVOICE_DISTRIBUTIONS_ALL, AP_CHECKS, AP_SUPPLIER_SITES_ALL, COUPA_INVOICES, COUPA_ORDERS, COUPA_CATALOG, IPRO_ORDERS, IPRO_CATALOG, PO_LINES_ALL, and other Oracle ERP tables
- **sco_rage_invoice_extract_ds**: invoice_extracts_prepared
- **sco_supplier_classification**: SPEND_TAXONOMY, INVOICE_ID_TO_FILE_NAME, IPRO_CATALOG_CATEGORIZATION, COUPA_CATALOG_CATEGORIZATION

Example: `sco_rage_invoice_extract_ds.invoice_extracts_prepared`, `sco_supplier_classification.SPEND_TAXONOMY`, `ai_financial_dlp.XXC_GL_SUMMARY`

**Join Paths:**

**Linking invoice_extracts_prepared to Suppliers:**
To get normalized supplier names from invoice_extracts_prepared:
1. `invoice_extracts_prepared.p8_file_id` → `INVOICE_ID_TO_FILE_NAME.p8_file_id`
2. `INVOICE_ID_TO_FILE_NAME.invoice_id` → `AP_INVOICES_ALL.invoice_id`
3. `AP_INVOICES_ALL.vendor_id` → `AP_SUPPLIERS.vendor_id` (get `supplier_name`)

**Linking to Palmer/Organizational Hierarchy:**
To get Palmer VP and organizational structure from invoice data:
1. From AP_INVOICES_ALL: `invoice_id` → `XXC_GL_SUMMARY.invoice_id`
2. `XXC_GL_SUMMARY.location` → `XXC_GL_DIV_REG_FAC.facility_id`
3. Access organizational columns from XXC_GL_DIV_REG_FAC:
   - **Palmer/Palmer VP**: `group_vp_desc` (NOT "palmer" or "palmer_vp")
   - **Division**: `division_desc` (NOT "department" or "division")
   - **Region**: `region_desc` (NOT "region")
   - **Facility**: `facility_description` or `facility_common_name`

**Available Tools:**
- `bigquery_list_dataset_ids`: List all available BigQuery datasets
- `bigquery_list_table_ids`: List tables within a specific dataset
- `bigquery_get_table_info`: Get detailed schema info for a specific table
- `bigquery_get_dataset_info`: Get metadata about a dataset
- `load_table_schema`: Load detailed schema documentation for a specific table (e.g., 'ap_invoices_all')
- `get_taxonomy_categories`: Returns L1/L2 category groupings with item counts from sco_supplier_classification.SPEND_TAXONOMY
- `get_taxonomy_items`: Returns all PRISM Commodity Names under a specific L2 from sco_supplier_classification.SPEND_TAXONOMY

**Available Table Summary:**

1. invoice_extracts_prepared
Records: 44,748+
Custom table storing parsed and processed line-item information extracted from physical invoice documents by the Structure Extraction Service. Contains the crucial L4 LLM categorizations with enhanced validation metrics and confidence scores.

**Structure:** Line items are stored as an ARRAY of STRUCTs. Use `UNNEST(line_items) AS line_item` to access line-level data.

Key Fields: 
- Header: `document_id` (PK), `invoice_number`, `invoice_date` (DATE), `vendor`, `total_amount` (NUMERIC), `currency`, `extraction_confidence`, `p8_file_id`
- Line Items (nested in `line_items` array): `line_item.category` (L4), `line_item.description`, `line_item.amount`, `line_item.quantity`, `line_item.unit_price`, `line_item.sku_or_service`, `line_item.category_confidence`, `line_item.validation_passed`

2. SPEND_TAXONOMY
Records: 1,124
Comprehensive spend classification taxonomy representing the hierarchical structure for categorizing expenses across multiple classification systems including Oracle categories and PRISM commodity codes. **This is the master reference table for L4 category lookups.**

Key Fields: `Account` (PK), `Oracle Super Category`, `Oracle Category`, `PRISM Commodity Level 1`, `PRISM Commodity Level 2`, `PRISM Commodity Level 3`, `PRISM Commodity Name` (maps to `line_items.category`), `Commodity Level`, `Account Description`

**Critical:** Use `PRISM Commodity Name` to join with `invoice_extracts_prepared.line_items.category` for L4 spend analysis.

Procurement Catalog Tables (For Savings Analysis)

3. Complete iProc Catalog
Records: 45,200
Master Item File for Direct spend items (Clinical supplies, Dialysis equipment, Pharmaceuticals). Used as the source of truth for preferred pricing and item substitution.

Key Fields: `Vendor Item`, `Item Description`, `UOM`, `Price`, `Vendor Name`, `NDC Code`, `PO Cat 1`

4. Complete Coupa Catalog
Records: 120,500
Multi-Category Procurement Catalog for Indirect spend (IT hardware, Facilities maintenance, Office supplies).

Key Fields: `Items Item ID`, `Items Item Description`, `Commodities Commodity Name`, `Suppliers Supplier Name`

5. IPRO_CATALOG_CATEGORIZATION
Records: ~9,734 (grows with catalog)
Dataset: **sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION**
LLM-generated PRISM commodity categorizations for IPRO catalog items. Links catalog items to PRISM Commodity Names for tail supplier consolidation analysis.

Key Fields: `davita_item_number` (PK, FK to IPRO_CATALOG), `prism_commodity_name_predicted`, `prism_prediction_confidence`, `prism_prediction_model`, `prism_categorized_at`, `categorization_run_id`, `item_description_snapshot`, `account_code_snapshot`

6. COUPA_CATALOG_CATEGORIZATION
Records: ~11,526 (grows with catalog)
Dataset: **sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION**
LLM-generated PRISM commodity categorizations for COUPA catalog items. Links catalog items to PRISM Commodity Names for tail supplier consolidation analysis.

Key Fields: `item_id` (PK, FK to COUPA_CATALOG), `prism_commodity_name_predicted`, `prism_prediction_confidence`, `prism_prediction_model`, `prism_categorized_at`, `categorization_run_id`, `item_description_snapshot`

Order & Invoice Transaction Tables (For Price Proxy)

7. COUPA_ORDERS
Records: 983,990
Dataset: **ai_financial_dlp.COUPA_ORDERS**
All purchase orders from the Coupa procurement system. Used as a price proxy for COUPA catalog items (which have no stored price).

Key Fields: `po_number` (PK), `supplier_id` (FK), `supplier_name_normalized`, `commodity` (e.g., "Snow Removal (7820)"), `item_description`, `unit_price`, `quantity`, `line_spend`, `order_date`, `line_status`, `order_status`, `facility_number`, `gl_account_number`

8. COUPA_INVOICES
Records: 1,275,011
Dataset: **ai_financial_dlp.COUPA_INVOICES**
All invoice line items from the Coupa system. Preferred source for COUPA price proxy (represents actual amounts paid).

Key Fields: `invoice_id` (PK), `supplier_id` (FK), `supplier_name_normalized`, `commodity_name` (e.g., "Tablet Security (7685)"), `item_description`, `unit_price`, `quantity`, `invoice_amount`, `po_number`, `approval_status`, `invoice_date`, `facility_number`, `gl_account_number`

9. IPRO_ORDERS
Records: 4,406,124
Dataset: **ai_financial_dlp.IPRO_ORDERS**
All purchase orders from the iProcurement system. Can supplement IPRO_CATALOG list prices with actual transaction prices.

Key Fields: `po_number` (PK), `vendor_id` (FK), `vendor_name_normalized`, `davita_item_number` (FK to IPRO_CATALOG), `item_description`, `unit_price`, `quantity_ordered`, `amount_ordered`, `unit_of_measure`, `expense_account`, `order_date`, `closed_code`, `facility_id`, `category1`, `category2`, `category3`

Accounts Payable (AP) & General Ledger (GL) Tables

10. AP_SUPPLIERS
Records: 1,150
Master directory of all external suppliers/vendors. Source of truth for normalized vendor names.

Key Fields: `vendor_id` (PK), `supplier_name`, `supplier_name_normalized`

11. AP_INVOICES_ALL
Records: 312,200
Invoice header records. Tracks vendor identity, invoice amounts, and acts as the bridge between transactional data and the supplier master.

Key Fields: `INVOICE_ID` (PK), `VENDOR_ID` (FK), `INVOICE_NUM`, `INVOICE_AMOUNT`, `GL_DATE`

12. AP_INVOICE_DISTRIBUTIONS_ALL
Records: 3,362,349
Detailed accounting distributions showing exactly how invoice costs are allocated to specific GL accounts and cost centers.

Key Fields: `INVOICE_DISTRIBUTION_ID` (PK), `INVOICE_ID` (FK), `DIST_CODE_COMBINATION_ID`, `AMOUNT`

13. XXC_GL_SUMMARY
Records: 13,789,400
Custom flattened GL summary holding aggregated financial data. This is the target for joining the `Expense_Taxonomy`.

Key Fields: `CODE_COMBINATION_ID`, `ACCOUNT` (L3 GL Code), `DEPARTMENT`, `LOCATION`, `AMOUNT`

14. XXC_GL_DIV_REG_FAC
Records: 10,020
Custom flattened organizational hierarchy table. Maps facilities through their reporting chain to determine spend by Palmer/VP.

Key Fields: `FACILITY_ID`, `REGION`, `DIVISION`, `PALMER_VP`, `GROUP_VP`

Table Relationships

Taxonomy & Organizational Flow:

`SPEND_TAXONOMY` (`Account`) ↔ (`ACCOUNT`) `XXC_GL_SUMMARY`
`XXC_GL_DIV_REG_FAC` (`FACILITY_ID`) ↔ (`LOCATION`) `XXC_GL_SUMMARY`

Spend & Supplier Flow:

`AP_SUPPLIERS` (`VENDOR_ID`) ↔ (`VENDOR_ID`) `AP_INVOICES_ALL`
`AP_INVOICES_ALL` (`INVOICE_ID`) ↔ (`INVOICE_ID`) `AP_INVOICE_DISTRIBUTIONS_ALL`

L4 Spend Analysis Flow:

`SPEND_TAXONOMY` (`PRISM Commodity Name`) ↔ (`line_item.category`) `invoice_extracts_prepared` (via `UNNEST(line_items)`)

Note: To link invoice data to AP organizational data, use `invoice_extracts_prepared.p8_file_id` to join to `INVOICE_ID_TO_FILE_NAME`, then to `AP_INVOICES_ALL` using `invoice_id`.

Taxonomy to Categorized Catalog Flow:

`SPEND_TAXONOMY` (`PRISM Commodity Name`) ↔ (`prism_commodity_name_predicted`) `IPRO_CATALOG_CATEGORIZATION`
`IPRO_CATALOG_CATEGORIZATION` (`davita_item_number`) ↔ (`davita_item_number`) `IPRO_CATALOG`

`SPEND_TAXONOMY` (`PRISM Commodity Name`) ↔ (`prism_commodity_name_predicted`) `COUPA_CATALOG_CATEGORIZATION`
`COUPA_CATALOG_CATEGORIZATION` (`item_id`) ↔ (`item_id`) `COUPA_CATALOG`

Enables linking L4 categories to catalog items via pre-categorized join tables for price comparison and savings analysis. Filter by `prism_prediction_confidence >= 0.5` to exclude low-confidence predictions.

Price Proxy Flow (COUPA catalog items have no stored price):

`COUPA_CATALOG` (`supplier_id` + `commodity_name`) ↔ (`supplier_id` + `commodity_name`) `COUPA_INVOICES` → get `AVG(unit_price)` as price proxy
`IPRO_CATALOG` (`davita_item_number`) ↔ (`davita_item_number`) `IPRO_ORDERS` → get actual transaction `unit_price` (supplements catalog list price)

**Business Definitions:**
- **Top Suppliers:** Default to top 3 suppliers by total spend unless otherwise specified
- **Preferred Suppliers:** Synonymous with "top suppliers" in variance analysis context
- **Palmer/Palmer VP:** Refers to `group_vp_desc` in XXC_GL_DIV_REG_FAC table

**Complex Query Patterns:**

**Note on L4 Category Filtering:** For L4 queries, the parent agent uses a two-step hierarchical approach:
1. Browses L1/L2 category groupings (~30 options)
2. Retrieves all PRISM Commodity Names under relevant L2 categories
3. Provides you with a complete, copy-paste ready IN clause containing all matching categories

You will receive the full list - do not abbreviate or filter it. The IN clause may contain dozens or hundreds of category values.

**Supplier Variance Analysis Pattern:**
When the parent agent asks you to compare spending across organizational units (Palmer, Division, Region) against "preferred" or "top" suppliers, use a CTE-based approach:

1. First CTE: Identify top N suppliers (default N=3) by total spend for the category
2. Second CTE: Join all spend data with organizational hierarchy
3. Final SELECT: Calculate preferred vs. non-preferred spend by organizational unit
4. Return % spending outside preferred suppliers, sorted by highest non-preferred %

Example CTE structure:
```sql
WITH top_suppliers AS (
  SELECT sup.supplier_name, SUM(SAFE_CAST(line_item.amount AS NUMERIC)) as total_spend
  FROM `project.sco_rage_invoice_extract_ds.invoice_extracts_prepared` inv,
  UNNEST(line_items) AS line_item
  JOIN `project.sco_supplier_classification.INVOICE_ID_TO_FILE_NAME` xwalk ON inv.p8_file_id = xwalk.p8_file_id
  JOIN `project.ai_financial_dlp.AP_INVOICES_ALL` ap ON xwalk.invoice_id = ap.invoice_id
  JOIN `project.ai_financial_dlp.AP_SUPPLIERS` sup ON ap.vendor_id = sup.vendor_id
  WHERE line_item.category IN ('Category1', 'Category2', 'Category3')  -- Parent provides complete list
  GROUP BY sup.supplier_name
  ORDER BY total_spend DESC
  LIMIT 3
),
org_spend AS (
  SELECT 
    org.group_vp_desc as palmer,
    org.division_desc as division,
    sup.supplier_name,
    SUM(SAFE_CAST(line_item.amount AS NUMERIC)) as spend
  FROM `project.sco_rage_invoice_extract_ds.invoice_extracts_prepared` inv,
  UNNEST(line_items) AS line_item
  JOIN `project.sco_supplier_classification.INVOICE_ID_TO_FILE_NAME` xwalk ON inv.p8_file_id = xwalk.p8_file_id
  JOIN `project.ai_financial_dlp.AP_INVOICES_ALL` ap ON xwalk.invoice_id = ap.invoice_id
  JOIN `project.ai_financial_dlp.AP_SUPPLIERS` sup ON ap.vendor_id = sup.vendor_id
  JOIN `project.ai_financial_dlp.XXC_GL_SUMMARY` gl ON ap.invoice_id = gl.invoice_id
  JOIN `project.ai_financial_dlp.XXC_GL_DIV_REG_FAC` org ON gl.location = org.facility_id
  WHERE line_item.category IN ('Category1', 'Category2', 'Category3')  -- Parent provides complete list
  GROUP BY org.group_vp_desc, org.division_desc, sup.supplier_name
)
SELECT 
  palmer,
  division,
  SUM(CASE WHEN supplier_name IN (SELECT supplier_name FROM top_suppliers) 
      THEN spend ELSE 0 END) as preferred_spend,
  SUM(spend) as total_spend,
  ROUND((SUM(CASE WHEN supplier_name NOT IN (SELECT supplier_name FROM top_suppliers) 
      THEN spend ELSE 0 END) / SUM(spend)) * 100, 2) as pct_outside_preferred
FROM org_spend
GROUP BY palmer, division
ORDER BY pct_outside_preferred DESC
```

**Tail Supplier Consolidation Pattern:**

When identifying savings opportunities by consolidating tail supplier spend under top suppliers using catalog alternatives:

```sql
WITH top_suppliers AS (
  -- Identify top 3 suppliers by spend for the category
  SELECT sup.supplier_name, SUM(SAFE_CAST(line_item.amount AS NUMERIC)) as total_spend
  FROM `project.sco_rage_invoice_extract_ds.invoice_extracts_prepared` inv,
  UNNEST(line_items) AS line_item
  JOIN `project.sco_supplier_classification.INVOICE_ID_TO_FILE_NAME` xwalk 
    ON inv.p8_file_id = xwalk.p8_file_id
  JOIN `project.ai_financial_dlp.AP_INVOICES_ALL` ap ON xwalk.invoice_id = ap.invoice_id
  JOIN `project.ai_financial_dlp.AP_SUPPLIERS` sup ON ap.vendor_id = sup.vendor_id
  WHERE LOWER(line_item.category) IN ('category1', 'category2', ...)  -- Parent provides lowercased list
  GROUP BY sup.supplier_name
  ORDER BY total_spend DESC
  LIMIT 3
),

tail_supplier_items AS (
  -- Get items from non-top-3 suppliers
  SELECT 
    sup.supplier_name as tail_supplier,
    line_item.description as tail_description,
    LOWER(line_item.category) as prism_category,
    SAFE_CAST(line_item.unit_price AS NUMERIC) as tail_unit_price,
    SAFE_CAST(line_item.quantity AS NUMERIC) as tail_quantity,
    SAFE_CAST(line_item.amount AS NUMERIC) as tail_amount
  FROM `project.sco_rage_invoice_extract_ds.invoice_extracts_prepared` inv,
  UNNEST(line_items) AS line_item
  JOIN `project.sco_supplier_classification.INVOICE_ID_TO_FILE_NAME` xwalk 
    ON inv.p8_file_id = xwalk.p8_file_id
  JOIN `project.ai_financial_dlp.AP_INVOICES_ALL` ap ON xwalk.invoice_id = ap.invoice_id
  JOIN `project.ai_financial_dlp.AP_SUPPLIERS` sup ON ap.vendor_id = sup.vendor_id
  WHERE LOWER(line_item.category) IN ('category1', 'category2', ...)
    AND sup.supplier_name NOT IN (SELECT supplier_name FROM top_suppliers)
),

-- Option A: Join to IPRO_CATALOG via categorization table
ipro_catalog_alternatives AS (
  SELECT 
    cat.vendor_name_normalized as catalog_vendor,
    cat.item_description as catalog_description,
    cat.price as catalog_price,
    cat.unit_of_measure as catalog_uom,
    LOWER(ctg.prism_commodity_name_predicted) as prism_category,
    ctg.prism_prediction_confidence
  FROM `project.ai_financial_dlp.IPRO_CATALOG` cat
  INNER JOIN `project.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION` ctg
    ON cat.davita_item_number = ctg.davita_item_number
  WHERE cat.vendor_name_normalized IN (SELECT supplier_name FROM top_suppliers)
    AND LOWER(ctg.prism_commodity_name_predicted) IN ('category1', 'category2', ...)
    AND ctg.prism_prediction_confidence >= 0.7  -- Quality threshold
),

-- Price proxy: COUPA catalog has no stored price, derive from invoice history
coupa_price_proxy AS (
  SELECT 
    supplier_id,
    commodity_name,
    AVG(SAFE_CAST(unit_price AS NUMERIC)) as avg_unit_price,
    COUNT(*) as price_sample_count
  FROM `project.ai_financial_dlp.COUPA_INVOICES`
  WHERE approval_status = 'approved'
    AND SAFE_CAST(unit_price AS NUMERIC) > 0
  GROUP BY supplier_id, commodity_name
),

-- Option B: Join to COUPA_CATALOG via categorization table + price proxy
coupa_catalog_alternatives AS (
  SELECT 
    cat.supplier_name_normalized as catalog_vendor,
    cat.item_description as catalog_description,
    proxy.avg_unit_price as catalog_price,  -- Price proxy from approved invoices
    CAST(NULL AS STRING) as catalog_uom,
    LOWER(ctg.prism_commodity_name_predicted) as prism_category,
    ctg.prism_prediction_confidence,
    'coupa_invoice_proxy' as price_source,
    proxy.price_sample_count
  FROM `project.ai_financial_dlp.COUPA_CATALOG` cat
  INNER JOIN `project.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION` ctg
    ON cat.item_id = ctg.item_id
  LEFT JOIN coupa_price_proxy proxy
    ON cat.supplier_id = proxy.supplier_id
    AND cat.commodity_name = proxy.commodity_name
  WHERE cat.supplier_name_normalized IN (SELECT supplier_name FROM top_suppliers)
    AND LOWER(ctg.prism_commodity_name_predicted) IN ('category1', 'category2', ...)
    AND ctg.prism_prediction_confidence >= 0.7
),

-- Combine both catalog sources
all_catalog_alternatives AS (
  SELECT catalog_vendor, catalog_description, catalog_price, catalog_uom,
         prism_category, prism_prediction_confidence, 
         'ipro_catalog' as price_source, CAST(NULL AS INT64) as price_sample_count
  FROM ipro_catalog_alternatives
  UNION ALL
  SELECT catalog_vendor, catalog_description, catalog_price, catalog_uom,
         prism_category, prism_prediction_confidence, price_source, price_sample_count
  FROM coupa_catalog_alternatives
)

-- Join tail items to catalog alternatives on category
SELECT 
  tail.tail_supplier,
  tail.tail_description,
  tail.tail_unit_price,
  tail.tail_quantity,
  tail.tail_amount,
  cat.catalog_vendor as preferred_supplier,
  cat.catalog_description as catalog_match,
  cat.catalog_price,
  cat.catalog_uom,
  cat.prism_category,
  cat.prism_prediction_confidence,
  cat.price_source,
  cat.price_sample_count,
  -- Calculate potential savings
  CASE 
    WHEN cat.catalog_price IS NOT NULL AND tail.tail_unit_price IS NOT NULL
    THEN (tail.tail_unit_price - cat.catalog_price) * tail.tail_quantity
    ELSE NULL
  END as potential_savings
FROM tail_supplier_items tail
INNER JOIN all_catalog_alternatives cat
  ON tail.prism_category = cat.prism_category
WHERE cat.catalog_price IS NOT NULL  -- Only include matches with price data
ORDER BY potential_savings DESC NULLS LAST
```

**Key considerations for this pattern:**
- **LOWER() on categories:** Invoice line_item.category is lowercased, so use LOWER() on predicted categories for joins
- **Confidence threshold:** Use >= 0.7 for high-quality matches, adjust as needed
- **IPRO pricing:** Uses catalog list price directly from `IPRO_CATALOG.price`
- **COUPA pricing:** Proxied from `COUPA_INVOICES` — average unit_price per supplier + commodity for approved invoices. `price_sample_count` indicates reliability (higher = more data points)
- **Supplier name matching:** Use vendor_name_normalized (IPRO) or supplier_name_normalized (COUPA) to match against AP_SUPPLIERS.supplier_name
- **Category filtering:** Parent agent provides the complete lowercased category list - use it for both invoice filtering and catalog filtering
- **Savings calculation:** Works for both IPRO (catalog price) and COUPA (invoice-proxied price). COUPA savings are approximate — flag with `price_source = 'coupa_invoice_proxy'`
- **NULL prices:** COUPA items without invoice history for that supplier+commodity will have NULL price and are excluded from savings calculation
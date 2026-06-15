# XXC_GL_SUMMARY

**Dataset:** ai_financial_dlp
**Purpose:** Oracle GL summary - **PRIMARY denormalized spend view**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| journal_header_id | INT64 | Journal header ID | Unique identifier |
| invoice_id | INT64 | Related invoice ID | Join to invoices |
| invoice_number | STRING | Related invoice number | Invoice reference |
| **vendor_name** | STRING | Vendor name | Supplier identification |
| vendor_id | INT64 | Vendor ID | FK to AP_SUPPLIERS |
| **amount** | NUMERIC | Journal amount | **Spend analysis** |
| **category** | STRING | Spend category | **Category matching** |
| super_category | STRING | Spend super-category | High-level category |
| **commodity** | STRING | Commodity | **Category matching** |
| account | STRING | Account segment | GL account |
| account_name | STRING | Account name | Account identification |
| effective_date | DATE | Effective date | Date filtering |
| period_name | STRING | GL period name | Period filtering |
| po_number | STRING | PO number | PO reference |

## Sample Query

```sql
-- Aggregate spend by supplier and category
SELECT
    vendor_name,
    category,
    commodity,
    SUM(amount) as total_spend,
    COUNT(DISTINCT invoice_id) as invoice_count
FROM ai_financial_dlp.XXC_GL_SUMMARY
WHERE vendor_name LIKE '%MEDLINE%'
  AND EXTRACT(YEAR FROM effective_date) = 2025
GROUP BY vendor_name, category, commodity
ORDER BY total_spend DESC
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| vendor_name | Medline Industries, LP; Accenture LLP |
| category | Medical Supplies, IT Services, Facilities Maintenance |
| commodity | Gloves, Consulting Services, Janitorial |
| amount | 525.00, 15000.00, 2000.00 |
| period_name | OCT-25, NOV-25, DEC-25 |

## Join Considerations

- **Denormalized**: No joins typically needed - contains vendor, category, amount
- **To AP_SUPPLIERS**: Use `vendor_id` if normalized matching needed
- **To Contracts (via RAG)**: Match on `vendor_name` or `category/commodity`
- **Spend Analysis**: Primary table for aggregating spend by supplier/category

## Notes

- **Denormalized view** - already joins vendor, category, amount
- Use for spend aggregation and trend analysis
- Contains both vendor_name and category/commodity for matching
- **Primary table for gap analysis** (suppliers with spend but no contract)

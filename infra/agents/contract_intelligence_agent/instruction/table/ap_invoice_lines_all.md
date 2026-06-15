# AP_INVOICE_LINES_ALL

**Dataset:** ai_financial_dlp
**Purpose:** Oracle invoice line items - **Backup for item description matching**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| invoice_id | INT64 | FK to AP_INVOICES_ALL | Join to invoice header |
| line_number | INT64 | Line number | Line identification |
| line_type | STRING | Line type code | Type filtering |
| line_amount | NUMERIC | Line amount | Amount validation |
| description | STRING | Line description | Context |
| **item_description** | STRING | Item description | **Item matching** |
| inventory_item_id | INT64 | Inventory item ID | Item reference |
| accounting_date | DATE | Accounting date | Date filtering |
| period_name | STRING | GL period name | Period filtering |
| **po_header_id** | INT64 | Related PO header | **PO linkage** |
| **po_line_id** | INT64 | Related PO line | **PO line linkage** |
| discarded_flag | STRING | Discarded flag (Y/N) | Active filtering |
| cancelled_flag | STRING | Cancelled flag (Y/N) | Active filtering |

## Sample Query

```sql
-- Get invoice lines with item descriptions
SELECT
    l.invoice_id,
    l.line_number,
    l.item_description,
    l.line_amount,
    s.supplier_name
FROM ai_financial_dlp.AP_INVOICE_LINES_ALL l
JOIN ai_financial_dlp.AP_INVOICES_ALL i ON l.invoice_id = i.invoice_id
JOIN ai_financial_dlp.AP_SUPPLIERS s ON i.vendor_id = s.vendor_id
WHERE s.supplier_name_normalized LIKE '%MEDLINE%'
  AND l.cancelled_flag = 'N'
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| item_description | Exam Gloves Large; Surgical Masks; IV Supplies |
| line_type | ITEM, TAX, FREIGHT |
| line_amount | 525.00, 50.00, 25.00 |

## Join Considerations

- **To AP_INVOICES_ALL**: Join on `invoice_id` (required for vendor_id)
- **To AP_INVOICE_DISTRIBUTIONS_ALL**: Join on `invoice_id` + `line_number` (maps to `invoice_line_number`)
- **To PO_LINES_ALL**: Join on `po_line_id` for PO-matched lines
- **Backup Source**: Use when invoice_extracts doesn't have item details

## Notes

- Use `item_description` as backup for matching when invoice_extracts unavailable
- Filter `cancelled_flag = 'N'` and `discarded_flag = 'N'` for active lines
- `po_line_id` links to PO for three-way match (PO → Invoice → Contract)
- Primary Key: `(invoice_id, line_number)`

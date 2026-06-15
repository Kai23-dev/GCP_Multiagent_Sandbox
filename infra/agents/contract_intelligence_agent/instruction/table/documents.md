# DOCUMENTS

**Dataset:** ai_financial_dlp
**Purpose:** Merged document view - **CRITICAL for invoice PDF reconciliation**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| document_id | INT64 | Document ID | **Link to invoice_extracts** |
| media_id | INT64 | Media ID | Content reference |
| **attached_entity_type** | STRING | Entity type | **Filter: 'AP_INVOICES'** |
| **attached_entity_id** | STRING | Entity PK value | **Join to invoice_id** |
| document_type | STRING | Document type name | Type filtering |
| document_type_display | STRING | Display name | UI display |
| **file_name** | STRING | File name | **PDF name matching** |
| **document_url** | STRING | Document URL | **P8 file reference** |
| document_content | STRING | Text content | Content search |
| usage_type | STRING | Usage type | Classification |

## Sample Query

```sql
-- Link AP invoices to their attached documents (PDFs)
SELECT
    i.invoice_id,
    i.invoice_number,
    s.supplier_name,
    d.document_id,
    d.file_name,
    d.document_url
FROM ai_financial_dlp.AP_INVOICES_ALL i
JOIN ai_financial_dlp.AP_SUPPLIERS s ON i.vendor_id = s.vendor_id
JOIN ai_financial_dlp.DOCUMENTS d
    ON d.attached_entity_type = 'AP_INVOICES'
    AND CAST(d.attached_entity_id AS INT64) = i.invoice_id
WHERE s.supplier_name_normalized LIKE '%MEDLINE%'
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| attached_entity_type | AP_INVOICES, PO_HEADERS, AP_SUPPLIERS |
| attached_entity_id | 59452126, 7379139 |
| file_name | INV_2025_001.pdf, Medline_Invoice_Jan2025.pdf |
| document_url | https://p8.davita.com/docs/INV_2025_001.pdf |
| document_type | INVOICE, ATTACHMENT, MISC |

## Join Considerations

- **To AP_INVOICES_ALL**: Join on `attached_entity_id = invoice_id` WHERE `attached_entity_type = 'AP_INVOICES'`
- **To PO_HEADERS_ALL**: Join on `attached_entity_id = po_header_id` WHERE `attached_entity_type = 'PO_HEADERS'`
- **To invoice_extracts**: Match `document_url` or `file_name` to P8 document references
- **Reconciliation**: Use to validate extracted invoice data against source documents

## Reconciliation Query Pattern

```sql
-- Reconcile invoice_extracts with AP invoice documents
SELECT
    ie.document_id as extract_doc_id,
    ie.invoice_number as extracted_invoice_num,
    ie.vendor as extracted_vendor,
    ie.total_amount as extracted_total,
    i.invoice_number as ap_invoice_num,
    i.invoice_amount as ap_invoice_amount,
    d.file_name,
    d.document_url
FROM sco_rage_invoice_extract_ds.invoice_extracts ie
LEFT JOIN ai_financial_dlp.DOCUMENTS d
    ON d.document_url LIKE CONCAT('%', ie.document_id, '%')
    OR d.file_name LIKE CONCAT('%', ie.invoice_number, '%')
LEFT JOIN ai_financial_dlp.AP_INVOICES_ALL i
    ON d.attached_entity_type = 'AP_INVOICES'
    AND CAST(d.attached_entity_id AS INT64) = i.invoice_id
WHERE ie.extraction_confidence > 0.8
```

## Notes

- **Merged View** - Combines 5 FND_* tables into single queryable view
- Use `attached_entity_type` filter to scope to specific entity (AP_INVOICES, PO_HEADERS)
- `attached_entity_id` is STRING - cast to INT64 when joining to invoice_id
- `document_url` contains P8 FileNet URL for accessing original PDF
- **Key for Citation** - Provides source document reference for AI-generated answers
- **Reconciliation** - Validates invoice_extracts against Oracle AP records

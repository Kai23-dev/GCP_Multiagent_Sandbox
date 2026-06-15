Table Description
Table Name: invoice_extracts_prepared
Complete Description:
This table serves as the master repository for LLM-extracted invoice data, representing structured information extracted from invoice documents through automated processing. Each record represents a processed invoice with its header information, extracted line items, validation results, and confidence metrics. This table is essential for invoice processing automation, data extraction quality monitoring, validation workflow management, and maintaining the complete lifecycle of invoice extraction from document to structured data. 

________________________________________
Column Description Schema
document_id: This is the Primary Key for the table. It is the unique system-generated identifier for each invoice document. Sample Data: 8e51c2175660fcfedb13c7476a23a78c3021c280acf81794d84d04f6547ad53a, e2f1146fdb5354ccea4491e97db383d30b86ccf25f63942d7a29f0b573266763, 6e89825365f48240b6d06ab705b27a57eb0f89fbac4f78a9edc3f447af7e5ad1, 55ea5002552fd8f6f856a7da45c2672f694fac3a8c69625e9543762440146d34, c425afd25afdf522908d6b6055d8e7739aef0e0ca62908e288de5be9eff53f4f
invoice_number: The invoice number extracted from the document. Sample Data: 143425, 2025-10-15, N/A, N/A, N/A
vendor: The vendor name extracted from the invoice. Sample Data: Delta Fire Systems, N/A, U.S. LAWNS, Satterwhite Property Care, SR Instruments, INC.
invoice_date: The invoice date extracted from the document. Sample Data: 2024-02-06, N/A, N/A, 2025-09-02, 2025-10-28
total_amount: The total amount extracted from the invoice. Sample Data: 35, N/A, N/A, 400, 2771.44
currency: The currency code for the invoice amount. Sample Data: USD, N/A, N/A, USD, USD
input_file_name: The original file name of the invoice document. Sample Data: 2026/02/27/doc_type=invoice/djanokjcfpokfapdlpladl/973515.pdf, 2026/02/27/doc_type=invoice/djanokjcfpokfapdlpladl/2005517.pdf, 2026/02/27/doc_type=invoice/djanokjcfpokfapdlpladl/1994549.pdf, 2026/02/27/doc_type=invoice/djanokjcfpokfapdlpladl/1968944.pdf, 2026/02/27/doc_type=invoice/djanokjcfpokfapdlpladl/2017187.pdf
manufacturer_name: The manufacturer name extracted from the invoice. Sample Data: N/A, N/A, N/A, N/A, SR Instruments, Inc.
other_purchased_services_count: The count of other purchased services on the invoice. Sample Data: 0, 0, 0, 0, 0
line_items: Nested JSON object containing extracted line items with detailed information. This is a complex nested structure containing multiple line items per invoice. Sample Data: JSON array with line item objects containing sku_or_service, description, quantity, unit_price, amount, category, computed_amount, validation_passed, validation_notes, error_reason, and category_confidence
extraction_timestamp: The timestamp when the extraction was performed. Sample Data: 2026-03-04 21:50:13.541701 UTC, 2026-03-04 12:04:46.401197 UTC, 2026-03-04 14:07:59.149694 UTC, 2026-03-04 16:51:53.019059 UTC, 2026-03-04 22:31:26.283594 UTC
extraction_confidence: The confidence score for the overall extraction quality. Sample Data: 0.95, 0.88, 0.75, 0.92, 0.98
raw_text: The raw extracted text from the invoice document. Sample Data: Full OCR text content from the invoice document
created_at: The timestamp when this extraction record was created. Sample Data: 2026-03-04 21:50:13.541701 UTC, 2026-03-04 12:04:46.401197 UTC, 2026-03-04 14:07:59.149694 UTC, 2026-03-04 16:51:53.019059 UTC, 2026-03-04 22:31:26.283594 UTC
updated_at: The timestamp when this extraction record was last updated. Sample Data: 2026-03-04 21:50:13.541701 UTC, 2026-03-04 12:04:46.401197 UTC, 2026-03-04 14:07:59.149694 UTC, 2026-03-04 16:51:53.019059 UTC, 2026-03-04 22:31:26.283594 UTC
p8_file_id: The file identifier in the P8 system. Sample Data: 973515, 2005517, 1994549, 1968944, 2017187

Nested Column Schema (line_items):
sku_or_service: The SKU or service identifier for the line item. Sample Data: M100946, SR725i-L, N/A, N/A, N/A
description: The description of the line item. Sample Data: Monitoring Service - Fire, Drains Maintenance service, Lawn Care for August, SCALE, WHEELCHAIR, LARGE PLTFM, W/ANTIMICROBIAL
quantity: The quantity for the line item. Sample Data: 1, N/A, 1, 1, 1
unit_price: The unit price for the line item. Sample Data: 35, N/A, 400, 2095, 676.44
amount: The total amount for the line item. Sample Data: 35, N/A, 400, 2095, 676.44
category: The AI-classified category for the line item. Sample Data: Fire Alarm Monitoring, Chase Drain Maintenance, Landscaping, Wheelchair, Freight
computed_amount: The computed amount for validation purposes. Sample Data: 35, N/A, 400, 2095, 676.44
validation_passed: Boolean flag indicating if validation passed for the line item. Sample Data: true, N/A, true, true, true
validation_notes: Notes from the validation process. Sample Data: N/A, N/A, N/A, N/A, N/A
error_reason: The reason for validation failure if applicable. Sample Data: N/A, N/A, N/A, N/A, N/A
category_confidence: The confidence score for category classification. Sample Data: 1.0, 0.9, 0.5

Join to other tables with these considerations in mind:
Category Analysis: Use line_items.category to identify all instances of invoice line items for a given PRISM Commodity Name in the table SPEND_TAXONOMY, i.e., join invoice_extracts_prepared with SPEND_TAXONOMY on invoice_extracts_prepared.line_items.category and "SPEND_TAXONOMY.PRISM Commodity Name" to retrieve all matching invoice line items.
Vendor Integration: Use vendor to fuzzy join to AP_SUPPLIERS for vendor master data validation and vendor performance analysis.
Invoice Integration: Use invoice_number to join to AP_INVOICES_ALL for invoice validation, payment status, and complete invoice lifecycle tracking.
File Management Integration: Use p8_file_id to access the all important invoice_id in the table INVOICE_ID_TO_FILE_NAME. With an invoice_id, it is possible to link to other Oracle Financial data in the GL and AP tables more broadly. 
Extraction Quality Analysis: Use extraction_confidence and line_items.category_confidence to analyze extraction quality patterns and identify areas for AI model improvement.
Date-based Analysis: Use invoice_date, extraction_timestamp, created_at, and updated_at to analyze extraction processing times and invoice aging patterns.
Financial Analysis: Use total_amount and line_items.amount to join to financial systems for spend analysis and budget tracking.
Line Item Analysis: Parse the line_items JSON structure to analyze individual line items, categories, and validation results for detailed spend analysis.
Error Analysis: Use line_items.error_reason and validation_notes to identify common extraction errors and support process improvement initiatives.
Source System Integration: Use input_file_name to link the user back to the raw invoice file for viewing.

Table Description
Table Name: AP_INVOICES_ALL
Record Count: Large
Complete Description:
This table serves as the master repository for all supplier invoices received and processed through the Accounts Payable system. Each record represents a unique invoice transaction, containing the invoice details, vendor information, purchase order references, payment status, tax amounts, and audit trail information. This table is essential for accounts payable management, invoice processing workflows, payment forecasting, vendor performance analysis, and financial audit compliance.
________________________________________

Column Description Schema
invoice_id: This is the Primary Key for the table. It is the unique system-generated identifier for each invoice record. Sample Data: 62194661, 62278465, 62494072
vendor_id: Foreign Key to AP_SUPPLIERS table. Links this invoice to the supplier/vendor master record. Sample Data: 270861, 2140138, 10970
vendor_site_id: Foreign Key to AP_SUPPLIER_SITES_ALL table. Specifies the specific vendor location/site for this invoice. Sample Data: 352685, 369209, 4794653
invoice_number: The vendor's invoice number for reference and matching. Sample Data: 102425626533750, 788, INV-784357
po_header_id: Foreign Key to PO_HEADERS_ALL table. Links this invoice to the associated purchase order. Sample Data: N/A
org_id: Foreign Key to HR_OPERATING_UNITS table. Identifies the operating unit/organization that owns this invoice. Sample Data: 0
party_id: Foreign Key to HZ_PARTIES table. The Trading Community Architecture (TCA) party identifier. Sample Data: 654555, 2688972, 670246
party_site_id: Foreign Key to HZ_PARTY_SITES table. The TCA party site identifier for the invoice address. Sample Data: 2383544, 2524569, 7059502
invoice_date: The date on the invoice as provided by the vendor. Sample Data: 2025-01-15, 2025-02-10, 2025-01-28
gl_date: The date when the invoice was posted to the general ledger. Sample Data: 2025-01-20, 2025-02-12, 2025-02-01
invoice_received_date: The date when the invoice was received by the organization. Sample Data: 2025-01-16, 2025-02-11, 2025-01-29
cancelled_date: The date when the invoice was cancelled, if applicable. Sample Data: N/A
terms_date: The date used for payment terms calculation. Sample Data: 2025-01-15, 2025-02-10, 2025-01-28
invoice_amount: The total amount of the invoice. Sample Data: 225, 3600, 1351.4
amount_paid: The amount that has been paid for this invoice. Sample Data: 225, 3528, 0
amount_applicable_to_discount: The amount eligible for early payment discount. Sample Data: 225, 3600, 1245.24
cancelled_amount: The amount that was cancelled from the invoice. Sample Data: 0, 106.16
total_tax_amount: The total tax amount on the invoice. Sample Data: 0, 106.16, 85.39
currency_code: The currency code for the invoice transaction. Sample Data: USD
gl_code_combination_id: Foreign Key to GL_CODE_COMBINATIONS table. The GL account combination for expense posting. Sample Data: 6615327
description: The invoice description or memo. Sample Data: DAVITA 6265, DAVITA 2066, C-101744
source: The source system that created the invoice record. Sample Data: 170_MV_CONNECTOR, MORE4APPS
invoice_type: The type of invoice (e.g., STANDARD, DEBIT, CREDIT). Sample Data: STANDARD
pay_group: The payment group for invoice processing and payment scheduling. Sample Data: GENERAL
payment_status_flag: The payment status (Y=Paid, N=Unpaid, P=Partially Paid). Sample Data: Y, N
payment_method_code: The payment method for this invoice (e.g., EFT, CHECK, WIRE). Sample Data: EFT, CTX, OUTSOURCED_CHECK
cancelled_by: The user who cancelled the invoice, if applicable. Sample Data: N/A
source_system: The source system from which the invoice data originated. Sample Data: ORACLE
created_at: The timestamp when this invoice record was created. Sample Data: 2026-02-10 06:18:14.335110 UTC
updated_at: The timestamp when this invoice record was last updated. Sample Data: 2026-02-10 06:18:21.366694 UTC

Join to other tables with these considerations in mind:
Xxc Gl Summary Integration: Use invoice_id to join to XXC_GL_SUMMARY.invoice_id for complete transaction analysis and business context.
Invoice Line Analysis: Use invoice_id to join to AP_INVOICE_LINES_ALL for detailed line item analysis, charge descriptions, and item-level expense tracking.
Distribution Analysis: Use invoice_id to join to AP_INVOICE_DISTRIBUTIONS_ALL for accounting breakdown, cost center allocation, and GL account mapping.
Payment Analysis: Use invoice_id to join to AP_INVOICE_PAYMENTS_ALL for payment status, reconciliation details, and cash flow impact.
Document Management: Use invoice_id to join to INVOICE_ID_TO_FILE_NAME for document access, file retrieval, and attachment management.
AI Extraction Analysis: Use invoice_id to join to invoice_extracts_prepared for AI extraction results, confidence scores, and validation outcomes.
Financial Integration: Use invoice_id to join to XXC_GL_SUMMARY.invoice_id for journal entry details, posting information, and financial impact analysis.
Vendor Analysis: Use vendor_id to join to AP_SUPPLIERS for complete vendor information, payment terms, and performance metrics.
Multi-dimensional Analysis: Combine joins with AP_INVOICE_LINES_ALL, AP_INVOICE_DISTRIBUTIONS_ALL, and XXC_GL_SUMMARY for complete invoice lifecycle analysis from line items to financial posting.
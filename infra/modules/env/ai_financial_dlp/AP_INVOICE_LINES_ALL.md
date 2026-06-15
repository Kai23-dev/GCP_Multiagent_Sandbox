Table Description
Table Name: AP_INVOICE_LINES_ALL
Record Count: Large
Complete Description:
This table serves as the master repository for all individual line items that make up supplier invoices. Each record represents a specific line on an invoice, containing the line details, amounts, descriptions, item information, and accounting allocations. This table is essential for detailed invoice analysis, item-level expense tracking, purchase order matching, inventory management, and financial audit compliance. It provides the granular breakdown of invoice totals into individual charge lines.
________________________________________

Column Description Schema
invoice_id: Foreign Key to AP_INVOICES_ALL table. Links this line to the parent invoice record. Sample Data: 60012248
line_number: The line number on the invoice that identifies this specific line item. Sample Data: 5332, 12065, 8077
line_type: The type of line (e.g., ITEM, FREIGHT, TAX, MISCELLANEOUS, CHARGE). Sample Data: ITEM, FREIGHT, TAX
line_source: The source system or method that created this invoice line. Sample Data: IMPORTED
line_amount: The monetary amount for this specific invoice line. Sample Data: 1.75, 4.25
description: The description of the line item as it appears on the invoice. Sample Data: MEDICAL SUPPLIES EFAX TRANSMISSION, LABORATORY EQUIPMENT EFAX PROCESSING, SURGICAL INSTRUMENTS EFAX DOCUMENTATION
item_description: The detailed description of the item being invoiced, often including catalog information. Sample Data: MEDICAL SUPPLIES CATALOG #440763, LAB EQUIPMENT CATALOG #805374, SURGICAL INSTRUMENTS CATALOG #522924
inventory_item_id: Foreign Key to MTL_SYSTEM_ITEMS_B table. The inventory item identifier for stocked items. Sample Data: 440763, 805374, 522924
accounting_date: The date when this line was posted to the general ledger. Sample Data: 2025-04-15
period_name: The GL period name for this invoice line. Sample Data: APR-25
gl_code_combination_id: Foreign Key to GL_CODE_COMBINATIONS table. The GL account combination for this line. Sample Data: 7158805, 9157100, 19995952
po_header_id: Foreign Key to PO_HEADERS_ALL table. Links this line to the associated purchase order header. Sample Data: N/A
po_line_id: Foreign Key to PO_LINES_ALL table. Links this line to the associated purchase order line. Sample Data: N/A
po_distribution_id: Foreign Key to PO_DISTRIBUTIONS_ALL table. Links this line to the associated PO distribution. Sample Data: N/A
receipt_transaction_id: Foreign Key to RCV_TRANSACTIONS table. Links this line to the receiving transaction. Sample Data: N/A
discarded_flag: Indicates if this line has been discarded or excluded from processing. Sample Data: N
cancelled_flag: Indicates if this line has been cancelled. Sample Data: N
source_system: The source system from which the line data originated. Sample Data: ORACLE
created_at: The timestamp when this invoice line record was created. Sample Data: 2026-02-10 06:18:14.345489 UTC
updated_at: The timestamp when this invoice line record was last updated. Sample Data: 2026-02-10 06:18:20.986307 UTC

Join to other tables with these considerations in mind:
Invoice Header Integration: Use invoice_id to join to AP_INVOICES_ALL for complete invoice information including vendor details, totals, and payment status.
Distribution Integration: Use invoice_id to join to AP_INVOICE_DISTRIBUTIONS_ALL for accounting allocation, cost center assignment, and expense categorization.
Financial Integration: Use invoice_id to join to XXC_GL_SUMMARY.invoice_id for GL posting details, account analysis, and financial impact assessment.
PO Matching Analysis: Use po_header_id and po_line_id to join to PO_HEADERS_ALL and PO_LINES_ALL for three-way matching validation and procurement analysis.
Receiving Integration: Use receipt_transaction_id to analyze receiving patterns (when available) and goods receipt validation.
Line Item Analysis: Combine line_type, line_amount, and description fields for detailed expense categorization and anomaly detection.
Period Analysis: Use accounting_date and period_name to join with financial periods for time-based analysis and reporting cycles.
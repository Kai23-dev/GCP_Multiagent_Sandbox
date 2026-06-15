Table Description
Table Name: AP_INVOICE_DISTRIBUTIONS_ALL
Record Count: Large
Complete Description:
This table serves as the master repository for all invoice distribution lines that represent the accounting breakdown of invoice amounts across different general ledger accounts. Each record represents a specific distribution line that allocates a portion of an invoice amount to a particular GL account combination, department, or cost center. This table is essential for detailed expense analysis, cost center reporting, project accounting, budget variance analysis, and financial audit compliance. The high record count indicates granular accounting detail for every invoice transaction.
________________________________________

Column Description Schema
distribution_id: This is the Primary Key for the table. It is the unique system-generated identifier for each invoice distribution line. Sample Data: 784965753, 830678637, 830695796
invoice_id: Foreign Key to AP_INVOICES_ALL table. Links this distribution to the parent invoice record. Sample Data: 58297496, 61155208, 61155128
invoice_line_number: The line number on the invoice that this distribution corresponds to. Sample Data: 7, 1
po_distribution_id: Foreign Key to PO_DISTRIBUTIONS_ALL table. Links this distribution to the associated purchase order distribution. Sample Data: 76977193, 79798225, 79885985
gl_code_combination_id: Foreign Key to GL_CODE_COMBINATIONS table. The GL account combination for expense posting. Sample Data: 31861442, 9965716, 9970048
accts_pay_code_combination_id: Foreign Key to GL_CODE_COMBINATIONS table. The AP liability account combination for this distribution. Sample Data: N/A
distribution_amount: The amount allocated to this distribution line. Sample Data: -5.46, -80.11, 17.5
base_amount: The amount in the base currency for this distribution line. Sample Data: -5.46, -80.11, 17.5
total_dist_amount: The total amount for this distribution including any adjustments. Sample Data: N/A
unit_price: The unit price for the item being invoiced. Sample Data: N/A
quantity_invoiced: The quantity of items being invoiced in this distribution. Sample Data: N/A
accounting_date: The date when this distribution was posted to the general ledger. Sample Data: 2024-11-15, 2025-07-20, 2025-08-10
period_name: The GL period name for this distribution. Sample Data: NOV-24, JUL-25, AUG-25
line_type: The type of distribution line (e.g., ITEM, FREIGHT, TAX, MISCELLANEOUS). Sample Data: IPV
distribution_class: The classification of this distribution for reporting purposes. Sample Data: PERMANENT
description: The description of the item or service being invoiced. Sample Data: "#97025 - 5 GAL CARBOY 3/4\" MOLDED DRAIN NATURAL", "-1_BX_50/BX_TEGADERM TRANSPARENT DRESSING_4X4.75_7779551", "-7_CA_NPMLC201_ACID
posted_flag: Indicates if this distribution has been posted to the general ledger (Y/N). Sample Data: Y
cancelled_flag: Indicates if this distribution has been cancelled (Y/N). Sample Data: N/A
source_system: The source system from which the distribution data originated. Sample Data: ORACLE
created_at: The timestamp when this distribution record was created. Sample Data: 2026-02-10 06:18:14.289426 UTC
updated_at: The timestamp when this distribution record was last updated. Sample Data: 2026-02-10 06:18:21.938662 UTC

Join to other tables with these considerations in mind:
Invoice Integration: Use invoice_id to join to AP_INVOICES_ALL for complete invoice header information, vendor details, and invoice totals.
Line Integration: Use invoice_id to join to AP_INVOICE_LINES_ALL for detailed line item information, charge descriptions, and item details.
Financial Integration: Use invoice_id to join to XXC_GL_SUMMARY.invoice_id for financial transaction analysis, GL account validation, and posting confirmation.
Requisition Integration: Use req_distribution_id to join to PO_REQ_DISTRIBUTIONS_ALL for purchase requisition tracking and budget validation.
Cost Center Analysis: Use distribution information for departmental expense analysis and budget variance reporting.
Accrual Management: Use accrued_flag and accrual_account_id for accrual analysis and month-end close validation.
Variance Analysis: Use variance_account_id for purchase price variance tracking and cost analysis.
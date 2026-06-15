Table Description
Table Name: XXC_GL_SUMMARY
Record Count: Very Large
Complete Description:
This table serves as the comprehensive general ledger summary repository, representing all financial transactions posted to the general ledger with detailed account breakdowns, transaction references, and business context. Each record represents a specific journal entry line with complete GL account details, amounts, reference information, and transaction attributes. This table is essential for financial reporting, expense analysis, budget tracking, audit compliance, and maintaining the complete financial transaction history for the organization. The extremely high record count indicates comprehensive financial transaction coverage across all business operations and accounting periods.
________________________________________

Column Description Schema
journal_header_id: Foreign Key to GL_JE_HEADERS table. The unique identifier for the journal header. Sample Data: 9376105, 9377988, 9370645
journal_line_number: The line number within the journal entry. Sample Data: 1984, 5401, 1489
invoice_id: Foreign Key to AP_INVOICES_ALL table. The unique identifier for the invoice if applicable. Sample Data: 61661352, 61788589, 61766796
invoice_number: The invoice number for reference. Sample Data: 0204212400, 0204231560, 43988171
gl_code_combination_id: Foreign Key to GL_CODE_COMBINATIONS table. The GL account combination identifier. Sample Data: 6595958, 15618837, 8744849
legal_entity: The legal entity code for the transaction. Sample Data: 100101, 200022, 200762
location: The location code for the transaction. Sample Data: 00552, 00562, 00575
department: The department code for the transaction. Sample Data: 0400
account: The account code for the transaction. Sample Data: 6604, 6800, 6606
sub_account: The sub-account code for the transaction. Sample Data: 300
account_name: The name of the account. Sample Data: Acid Expense, R&M Dialysis Machine, Saline Expense
sub_account_name: The name of the sub-account. Sample Data: In-Center Hemo
amount: The transaction amount in the specified currency. Sample Data: -7.5, 4.1, -2.1
stat_amount: The statistical amount for the transaction. Sample Data: N/A
currency_code: The currency code for the transaction. Sample Data: USD
ledger_id: The ledger identifier for the transaction. Sample Data: 1
effective_date: The effective date of the transaction. Sample Data: 2025-10-31
period_name: The accounting period name. Sample Data: OCT-25
journal_posted_date: The date when the journal was posted. Sample Data: 2025-11-01
journal_category: The category of the journal entry. Sample Data: Payments
journal_source: The source of the journal entry. Sample Data: Payables
line_description: The description of the journal line. Sample Data: Journal Import Created
batch_name: The batch name for the journal entry. Sample Data: DVAAPNP Payables A 20012023 86396417, DVAAPNP Payables A 20013024 86460914, DVAAPNP Payables A 20009045 86299418
category: The expense category for the transaction. Sample Data: Direct Medical Supply Expense, Machine MTN & Repair
super_category: The super category for the transaction. Sample Data: Medical Supplies, Other Controllable
commodity: The commodity classification for the transaction. Sample Data: N/A
vendor_name: The name of the vendor for the transaction. Sample Data: FRESENIUS USA INC, VANTIVE US HEALTHCARE LLC
vendor_id: Foreign Key to AP_SUPPLIERS table. The unique identifier for the vendor. Sample Data: 6406, 8175038
po_number: The purchase order number if applicable. Sample Data: 95080-1083884, 95080-1103644, 158773-151439
check_id: Foreign Key to AP_CHECKS_ALL table. The unique identifier for the check. Sample Data: 23524414, 23578054, 23475817
check_number: The check number for reference. Sample Data: 913052, 914171, 50027522
source_system: The source system that created this transaction. Sample Data: ORACLE
created_at: The timestamp when this transaction record was created. Sample Data: 2026-02-10 06:18:14.416371 UTC
updated_at: The timestamp when this transaction record was last updated. Sample Data: 2026-02-10 06:18:24.895326 UTC

Join to other tables with these considerations in mind:
Primary Ap Invoices All Integration: Always join invoice_id to AP_INVOICES_ALL.invoice_id to get complete Ap Invoices All information and establish the core relationship.
Primary Ap Suppliers Integration: Always join vendor_id to AP_SUPPLIERS.vendor_id to get complete Ap Suppliers information and establish the core relationship.
Primary Ap Checks All Integration: Always join check_id to AP_CHECKS_ALL.check_id to get complete Ap Checks All information and establish the core relationship.
Invoice Integration: Use invoice_id to join to AP_INVOICES_ALL for invoice details, validation, and complete transaction context.
Check Integration: Use check_id to join to AP_CHECKS_ALL for payment instrument details and cash transaction reconciliation.
Vendor Integration: Use vendor_id and vendor_name to join to AP_SUPPLIERS for supplier performance analysis and payment pattern validation.
Comprehensive Financial Analysis: Use account, sub_account, and account_name for detailed expense analysis by account segments and hierarchical reporting.
Time Series Analysis: Use period_name, effective_date, and journal_posted_date for trend analysis, seasonal patterns, and financial forecasting.
Business Context Integration: Combine with invoice_id, check_id, and vendor_id for complete business transaction analysis from source to GL posting.
Category Analysis: Use category and super_category for expense categorization, management reporting, and cost center analysis.
Multi-dimensional Reporting: Combine legal_entity, location, and department for organizational reporting and responsibility accounting.
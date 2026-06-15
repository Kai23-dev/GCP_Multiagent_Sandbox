Table Description
Table Name: XXC_GL_SUMMARY
Record Count: 13,789,400
Complete Description:
This table serves as the comprehensive general ledger summary repository, representing all financial transactions posted to the general ledger with detailed account breakdowns, transaction references, and business context. Each record represents a specific journal entry line with complete GL account details, amounts, reference information, and transaction attributes. This table is essential for financial reporting, expense analysis, budget tracking, audit compliance, and maintaining the complete financial transaction history for the organization. The extremely high record count indicates comprehensive financial transaction coverage across all business operations and accounting periods.
Natural representation description:
This table acts as the central financial transaction repository for the general ledger, containing every journal entry line with detailed account information, transaction references, and business context. It provides the foundation for complete financial analysis, expense tracking, budget management, and compliance reporting across all organizational financial activities.
________________________________________
Column Description Schema
journal_header_id: Foreign Key to GL_JE_HEADERS table. The unique identifier for the journal header. Sample Data: 9376105, 9377988, 9370645, 9370670, 9376105
journal_line_number: The line number within the journal entry. Sample Data: 1984, 5401, 1489, 3693, 2646
invoice_id: Foreign Key to AP_INVOICES_ALL table. The unique identifier for the invoice if applicable. Sample Data: 61661352, 61788589, 61766796, -1, -1
invoice_number: The invoice number for reference. Sample Data: 0204212400, 0204231560, 43988171, Multiple, Multiple
gl_code_combination_id: Foreign Key to GL_CODE_COMBINATIONS table. The GL account combination identifier. Sample Data: 6595958, 15618837, 8744849, 15928760, 8770631
legal_entity: The legal entity code for the transaction. Sample Data: 100101, 100101, 200022, 200762, 200022
location: The location code for the transaction. Sample Data: 00552, 00562, 00575, 00547, 00583
department: The department code for the transaction. Sample Data: 0400, 0400, 0400, 0400, 0400
account: The account code for the transaction. Sample Data: 6604, 6800, 6606, 6800, 6604
sub_account: The sub-account code for the transaction. Sample Data: 300, 300, 300, 300, 300
account_name: The name of the account. Sample Data: Acid Expense, R&M Dialysis Machine, Saline Expense, R&M Dialysis Machine, Acid Expense
sub_account_name: The name of the sub-account. Sample Data: In-Center Hemo, In-Center Hemo, In-Center Hemo, In-Center Hemo, In-Center Hemo
amount: The transaction amount in the specified currency. Sample Data: -7.5, 4.1, -2.1, -25.66, -15
stat_amount: The statistical amount for the transaction. Sample Data: N/A, N/A, N/A, N/A, N/A
currency_code: The currency code for the transaction. Sample Data: USD, USD, USD, USD, USD
ledger_id: The ledger identifier for the transaction. Sample Data: 1, 1, 1, 1, 1
effective_date: The effective date of the transaction. Sample Data: 2025-10-31, 2025-10-31, 2025-10-31, 2025-10-31, 2025-10-31
period_name: The accounting period name. Sample Data: OCT-25, OCT-25, OCT-25, OCT-25, OCT-25
journal_posted_date: The date when the journal was posted. Sample Data: 2025-11-01, 2025-11-01, 2025-11-01, 2025-11-01, 2025-11-01
journal_category: The category of the journal entry. Sample Data: Payments, Payments, Payments, Payments, Payments
journal_source: The source of the journal entry. Sample Data: Payables, Payables, Payables, Payables, Payables
line_description: The description of the journal line. Sample Data: Journal Import Created, Journal Import Created, Journal Import Created, Journal Import Created, Journal Import Created
batch_name: The batch name for the journal entry. Sample Data: DVAAPNP Payables A 20012023 86396417, DVAAPNP Payables A 20013024 86460914, DVAAPNP Payables A 20009045 86299418, DVAAPNP Payables A 20009034 86299425, DVAAPNP Payables A 20012023 86396417
category: The expense category for the transaction. Sample Data: Direct Medical Supply Expense, Machine MTN & Repair, Direct Medical Supply Expense, Machine MTN & Repair, Direct Medical Supply Expense
super_category: The super category for the transaction. Sample Data: Medical Supplies, Other Controllable, Medical Supplies, Other Controllable, Medical Supplies
commodity: The commodity classification for the transaction. Sample Data: N/A, N/A, N/A, N/A, N/A
vendor_name: The name of the vendor for the transaction. Sample Data: FRESENIUS USA INC, FRESENIUS USA INC, VANTIVE US HEALTHCARE LLC, FRESENIUS USA INC, FRESENIUS USA INC
vendor_id: Foreign Key to AP_SUPPLIERS table. The unique identifier for the vendor. Sample Data: 6406, 6406, 8175038, 6406, 6406
po_number: The purchase order number if applicable. Sample Data: 95080-1083884, 95080-1103644, 158773-151439, N/A, N/A
check_id: Foreign Key to AP_CHECKS_ALL table. The unique identifier for the check. Sample Data: 23524414, 23578054, 23475817, 23475823, 23524414
check_number: The check number for reference. Sample Data: 913052, 914171, 50027522, 910773, 913052
source_system: The source system that created this transaction. Sample Data: ORACLE, ORACLE, ORACLE, ORACLE, ORACLE
created_at: The timestamp when this transaction record was created. Sample Data: 2026-02-10 06:18:14.416371 UTC, 2026-02-10 06:18:14.416371 UTC
updated_at: The timestamp when this transaction record was last updated. Sample Data: 2026-02-10 06:18:24.895326 UTC, 2026-02-10 06:18:24.895326 UTC

Join to other tables with these considerations in mind:
Primary GL Integration: Always join gl_code_combination_id to GL_CODE_COMBINATIONS to get readable account segments for detailed financial reporting and analysis.
Invoice Integration: Join invoice_id to AP_INVOICES_ALL to get complete invoice information including vendor details, line items, and approval status.
Vendor Integration: Join vendor_id to AP_SUPPLIERS to get complete vendor information including contact details, payment terms, and performance metrics.
Check Integration: Join check_id to AP_CHECKS_ALL to get complete check information including payment details, bank information, and status.
PO Integration: Join po_number to PO_HEADERS_ALL to get complete purchase order information and analyze procurement-to-payment cycles.
Journal Header Integration: Join journal_header_id to GL_JE_HEADERS to get complete journal header information including approval status and posting details.
Account Analysis: Use account, account_name, sub_account, and sub_account_name to analyze spending patterns by account and support detailed expense analysis.
Department Analysis: Use department to join to department tables for departmental spending analysis and budget variance reporting.
Location Analysis: Use location to join to location tables for geographic spending analysis and regional reporting.
Legal Entity Analysis: Use legal_entity to join to legal entity tables for multi-entity financial reporting and compliance analysis.
Period Analysis: Use period_name and effective_date to analyze spending patterns over time and support period-based financial reporting.
Currency Analysis: Use currency_code to join to currency tables for multi-currency financial analysis and foreign exchange impact assessment.
Journal Category Analysis: Use journal_category and journal_source to analyze transaction patterns by source and support process optimization.
Expense Category Analysis: Use category and super_category to analyze spending patterns by expense category and support cost management initiatives.
Performance Considerations: Due to the extremely high record count (13.7M+), consider partitioning strategies and indexing on gl_code_combination_id, vendor_id, and effective_date for optimal query performance.
Audit Trail: Use created_at and updated_at to track transaction record lifecycle for compliance reporting and change management analysis.
Financial Analysis: Use amount and stat_amount to analyze financial trends, identify anomalies, and support financial planning and analysis activities.

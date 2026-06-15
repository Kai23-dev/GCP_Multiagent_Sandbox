Table Description
Table Name: AP_INVOICE_PAYMENTS_ALL
Record Count: Large
Complete Description:
This table serves as the master repository for all payment-to-invoice relationships, representing the specific allocation of payments to individual invoices. Each record represents a payment transaction that pays a specific invoice, containing the payment amount, discount information, accounting details, and audit trail. This table is essential for payment reconciliation, invoice payment tracking, discount analysis, cash management, and financial audit compliance. It provides the critical link between payments and the invoices they settle.
________________________________________

Column Description Schema
payment_id: This is the Primary Key for the table. It is the unique system-generated identifier for each payment-to-invoice relationship. Sample Data: 64083131, 65824071, 61294819
invoice_id: Foreign Key to AP_INVOICES_ALL table. Links this payment to the specific invoice being paid. Sample Data: 60670088, 62256548, 58507234
check_id: Foreign Key to AP_CHECKS_ALL table. Links this payment to the check or payment instrument used. Sample Data: 23039656, 23871859, 21634870
payment_num: The payment sequence number for this invoice (useful for partial payments). Sample Data: 1
payment_amount: The amount of this payment applied to the invoice. Sample Data: 41.53, 39.27, 0
discount_lost: The amount of discount that was lost due to late payment. Sample Data: 0
discount_taken: The amount of early payment discount taken. Sample Data: 0
accounting_date: The date when this payment was posted to the general ledger. Sample Data: 2025-07-15, 2025-12-20, 2024-12-15
period_name: The GL period name for this payment transaction. Sample Data: JUL-25, DEC-25, DEC-24
posted_flag: Indicates if this payment has been posted to the general ledger (Y/N). Sample Data: Y
accrual_posted_flag: Indicates if the accrual accounting has been posted (Y/N). Sample Data: Y
remit_to_supplier_name: The name of the supplier receiving this payment. Sample Data: RENTOKIL PEST CONTROL, STATE OF WASHINGTON DEPARTMENT OF REVENUE, EASTERN VIDEO SERVICE LLC
remit_to_supplier_id: Foreign Key to AP_SUPPLIERS table. The vendor ID of the supplier being paid. Sample Data: 256138, 15615, 910922
org_id: Foreign Key to HR_OPERATING_UNITS table. Identifies the operating unit/organization that owns this payment. Sample Data: 0
source_system: The source system from which the payment data originated. Sample Data: ORACLE
created_at: The timestamp when this payment record was created. Sample Data: 2026-02-10 06:18:14.435764 UTC
updated_at: The timestamp when this payment record was last updated. Sample Data: 2026-02-10 06:18:20.519776 UTC

Join to other tables with these considerations in mind:
Invoice Integration: Use invoice_id to join to AP_INVOICES_ALL for complete invoice information, payment status, and vendor details.
Check Integration: Use check_id to join to AP_CHECKS_ALL for payment instrument details, clearing information, and bank reconciliation.
Financial Integration: Use invoice_id to join to XXC_GL_SUMMARY.invoice_id for cash impact analysis and payment transaction validation.
Payment Analysis: Combine payment information with invoice details for payment cycle analysis, cash flow forecasting, and vendor payment patterns.
Reconciliation Analysis: Use payment dates and amounts to match with bank transactions and support treasury management.
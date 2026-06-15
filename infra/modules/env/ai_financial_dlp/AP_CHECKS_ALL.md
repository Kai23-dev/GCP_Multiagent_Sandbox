Table Description
Table Name: AP_CHECKS_ALL
Record Count: Regular
Complete Description:
This table serves as the master repository for all payment records (checks, electronic transfers, and other payment instruments) issued to suppliers and vendors through the Accounts Payable system. Each record represents a unique payment transaction, containing the payment amount, vendor details, remittance address, clearing and voiding status, and audit trail information. This table is essential for cash management, payment reconciliation, bank clearing analysis, vendor payment history, and financial audit compliance.
________________________________________

Column Description Schema
check_id: This is the Primary Key for the table. It is the unique system-generated identifier for each payment record. Sample Data: 23014680, 23480250, 22019574
vendor_id: Foreign Key to AP_SUPPLIERS table. Links this payment to the supplier/vendor master record. Sample Data: 7751981, 7746730, 7764241
vendor_site_id: Foreign Key to AP_SUPPLIER_SITES_ALL table. Specifies the specific vendor location/site for this payment. Sample Data: 4812559, 5636331, 4827654
check_number: The payment instrument number (check number, EFT reference, etc.) used for tracking and reconciliation. Sample Data: 151618595, 151701598, 151470419
check_date: The date the payment was issued. Sample Data: (dates corresponding to checkrun batches)
checkrun_name: The name of the payment batch run that generated this payment. Sample Data: 070825ZEROALL-OS, 100225ZEROALL-OS, 013025ZEROALL-OS
check_amount: The total amount of the payment. Sample Data: 0, 120.08
cleared_amount: The amount that has been cleared by the bank. Sample Data: (cleared amounts post-reconciliation)
currency_code: The currency code for the payment transaction. Sample Data: USD
cleared_date: The date the payment was cleared by the bank. Sample Data: (dates when bank confirms clearing)
void_date: The date the payment was voided, if applicable. Sample Data: (void dates for cancelled payments)
status_lookup_code: The current status of the payment (e.g., NEGOTIABLE, VOIDED, CLEARED, RECONCILED). Sample Data: NEGOTIABLE, VOIDED
payment_type_flag: A code indicating the type of payment (A=Automatic, M=Manual, Q=Quick, R=Refund). Sample Data: A
payment_method_code: The method used for the payment (e.g., OUTSOURCED_CHECK, EFT, WIRE). Sample Data: OUTSOURCED_CHECK
party_id: Foreign Key to HZ_PARTIES table. The Trading Community Architecture (TCA) party identifier. Sample Data: 8101343, 8088049, 8135301
party_site_id: Foreign Key to HZ_PARTY_SITES table. The TCA party site identifier for the payment address. Sample Data: 7082750, 7598039, 7103197
remit_to_supplier_name: The name of the supplier or payee on the payment instrument. Sample Data: MEDLINE INDUSTRIES INC, "TUBURAN, APRIL"
address_line1: The first line of the remittance address. Sample Data: 1500 MEADOW DR, 742 EVERGREEN TERRACE, 200 MAIN ST
city: The city of the remittance address. Sample Data: MUNDELEIN, DENVER, ATLANTA
state: The state of the remittance address. Sample Data: IL, CO, GA
zip: The postal code of the remittance address. Sample Data: 60060, 80202, 30301
country: The country code of the remittance address. Sample Data: US
org_id: Foreign Key to HR_OPERATING_UNITS table. Identifies the operating unit/organization that owns this payment. Sample Data: 0
legal_entity_id: Foreign Key to XLE_ENTITY_PROFILES table. Identifies the legal entity issuing the payment. Sample Data: 0
source_system: The source system from which the payment data originated. Sample Data: ORACLE
created_at: The timestamp when this payment record was created. Sample Data: 2026-02-10 06:18:14.377355 UTC
updated_at: The timestamp when this payment record was last updated. Sample Data: 2026-02-10 06:18:19.772973 UTC

Join to other tables with these considerations in mind:
Xxc Gl Summary Integration: Use check_id to join to XXC_GL_SUMMARY.check_id for complete transaction analysis and business context.
Payment Integration: Use check_id to join to AP_INVOICE_PAYMENTS_ALL for invoice payment relationships, payment allocations, and reconciliation details.
Financial Integration: Use check_id to join to XXC_GL_SUMMARY.check_id for journal entry details, cash account impact, and financial transaction analysis.
Vendor Integration: Use vendor_id to join to AP_SUPPLIERS for complete vendor information, payment patterns, and supplier performance analysis.
Bank Reconciliation: Use cleared_amount and cleared_date for bank statement reconciliation and cash management analysis.
Payment Analysis: Combine checkrun_name, payment_method_code, and status_lookup_code for payment processing efficiency analysis.
Audit Trail: Use created_at and updated_at for payment lifecycle tracking and compliance reporting.

Table Description
Table Name: ap_checks
Record Count: 43,100
Complete Description:
This table is the primary transactional table for all payments made to suppliers, employees, or other parties. It stores the header-level information for a payment document. While the name implies "Checks," it records all payment instruments including physical checks, Electronic Funds Transfers (EFT), Wire Transfers, and Clearing payments (Zero-dollar payments). It bridges the gap between the Accounts Payable liability (Invoices) and the Cash Management banking activity.
Natural representation description:
This table represents the organization's "Checkbook" or "Payment Register." It answers the core financial questions: "Who was paid?", "How much was the payment?", "When was the payment issued?", "What method was used (Paper vs. Electronic)?", and "Has the payment cleared the bank?"
________________________________________
Column Description Schema
AMOUNT: The total monetary value of the payment. This amount may represent the sum of multiple invoices being paid by a single check/payment. Sample Data: 2400, 0, 93.17
CHECK_DATE: The date the payment was officially issued/printed. This is the accounting date used for crediting the Cash account in the General Ledger. Sample Data: 26-FEB-2025 00:00:00, 25-FEB-2025 00:00:00
CHECK_ID: This is the Primary Key for the table. It is the unique system-generated identifier for the payment. Other tables (like AP_INVOICE_PAYMENTS_ALL) use this ID to join to this record. Sample Data: 22166678, 22174564, 22171151
CHECK_NUMBER: The public-facing document number. This is the number printed on the physical check stock or the transaction reference number generated for electronic transfers. Sample Data: 840113, 151493059, 842358
CURRENCY_CODE: The code representing the currency in which the payment was issued. This joins to the Currencies table. Sample Data: USD
LAST_UPDATED_BY: An audit Foreign Key linking to the Users table, identifying the user who performed the last modification to this record. Sample Data: 162252, 164935
LAST_UPDATE_DATE: An audit timestamp indicating when this record was last modified in the system. Sample Data: 24-FEB-2025 10:39:14, 25-FEB-2025 16:29:16
PAYMENT_TYPE_FLAG: A code indicating the type of payment, such as 'M' for Manual, 'Q' for Quick, or 'A' for Automated. Sample Data: A, A, A
ADDRESS_LINE1: The first line of the supplier's address at the time of payment printing. This is a snapshot and does not update if the supplier's master address changes later. Sample Data: addresses
ADDRESS_LINE2: The second line of the supplier's address snapshot. Sample Data: addresses
ADDRESS_LINE3: The third line of the supplier's address snapshot. Sample Data: N/A, address
CHECKRUN_NAME: The name assigned to the payment batch (Check Run) that generated this payment. Useful for grouping payments processed together. Sample Data: ACH022425GEN, 022525ZEROALL-OS
CITY: The city name for the supplier's address snapshot. Sample Data: city names
COUNTRY: The country code for the supplier's address snapshot. Sample Data: country’s name
CREATED_BY: An audit Foreign Key linking to the Users table, identifying the user who originally created this payment record. Sample Data: 162252, 164935
CREATION_DATE: An audit timestamp indicating when this record was first created. Sample Data: 24-FEB-2025 10:39:14, 25-FEB-2025 16:29:16
STATUS_LOOKUP_CODE: A status code indicating the current state of the payment. Common values include 'NEGOTIABLE' (Valid), 'VOIDED' (Cancelled), or 'CLEARED'. Sample Data: NEGOTIABLE
ZIP: The postal code for the supplier's address snapshot. Sample Data: US zip codes
CLEARED_AMOUNT: The actual amount that was cleared by the bank. If the payment has not cleared, this is often NULL or N/A. Sample Data: N/A, amount
CLEARED_DATE: The date the payment was recognized and processed by the bank. Used for Bank Reconciliation. Sample Data: N/A, date
STATE: The state or province for the supplier's address snapshot. Sample Data: USA state name
RELEASED_AT: If the payment was previously stopped or held, this timestamp records when it was released. Sample Data: N/A, dates
RELEASED_BY: The User ID of the person who released the payment from a hold. Sample Data: N/A, userID
STOPPED_AT: Timestamp recording when a "Stop Payment" request was issued on this document. Sample Data: N/A, dates
STOPPED_BY: The User ID of the person who initiated the stop payment. Sample Data: N/A, userID
VOID_DATE: The date on which the payment was voided. If this column has a value, the payment is invalid and the accounting has likely been reversed. Sample Data: N/A, dates
ADDRESS_LINE4: The fourth line of the supplier's address snapshot. Sample Data: N/A, if address too big.
COUNTY: The county for the supplier's address snapshot. Sample Data: N/A, county name
ORG_ID: The Operating Unit identifier. This partitions data by business unit for security and reporting. Links to HR_OPERATING_UNITS. Sample Data: 0 (Note: Value depends on system configuration)
VENDOR_ID: A Foreign Key linking to the AP_SUPPLIERS table. Identifies the supplier legal entity being paid. Sample Data: 7736757, 7756292, 969922
VENDOR_SITE_ID: A Foreign Key linking to AP_SUPPLIER_SITES_ALL. Identifies the specific location/branch of the supplier receiving the payment. Sample Data: 4831711, 5505458, 1154226
CHECKRUN_ID: A system ID linking to the payment batch definition. Useful for joining to AP_INV_SELECTION_CRITERIA_ALL. Sample Data: 301393, 301500, 301482
PAYMENT_METHOD_CODE: Indicates the specific method used to transfer funds (e.g., Check, Electronic, Outsourced). Sample Data: EFT, OUTSOURCED_CHECK
PARTY_ID: A Foreign Key to the Trading Community Architecture (TCA) table HZ_PARTIES. Represents the party in the global address book. Sample Data: 7969459, 8114217, 1590104
PARTY_SITE_ID: A Foreign Key to HZ_PARTY_SITES. Represents the specific address ID in the TCA registry. Sample Data: 7108323, 7556123, 3453617
PAYMENT_PROFILE_ID: A Foreign Key linking to the Oracle Payments (IBY) setup, defining rules for formatting and transmission. Sample Data: 302, 502
LEGAL_ENTITY_ID: A Foreign Key identifying the internal Legal Entity (Company) that owns the bank account issuing the funds. Sample Data: number representing entity
PAYMENT_DOCUMENT_ID: A Foreign Key identifying the specific check stock or payment document configuration used (e.g., "Check Stock A"). Sample Data: 203, 422
PAYMENT_ID: The internal identifier for the payment within the Oracle Payments (IBY) module. This links AP_CHECKS to the IBY_PAYMENTS_ALL table. Sample Data: 16461553, 16467844, 16465193
PAYMENT_INSTRUCTION_ID: An identifier grouping payments into a specific instruction file sent to the bank (common in EFT/Wire batches). Sample Data: 296710, 296775, 296771
REMIT_TO_SUPPLIER_NAME: The name of the supplier to whom the payment is actually remitted. This is the "Payee Name" printed on the check. Sample Data: BATTLE BUGS PEST CONTROL, BIRMINGHAM REALTY COMPANY
REMIT_TO_SUPPLIER_ID: The Vendor ID of the remit-to supplier. Usually matches VENDOR_ID unless it is a third-party payment relationship. Sample Data: 7736757, 7756292, 969922
REMIT_TO_SUPPLIER_SITE: The name of the specific site/address code for the remit-to supplier. Sample Data: RAVENNA1, HOME1, BIRMINGHAM1
REMIT_TO_SUPPLIER_SITE_ID: The Site ID for the remit-to supplier location. Sample Data: 4831711, 5505458, 1154226
________________________________________
Join to other tables with these considerations in mind:
Linking to Invoices (The "Bridge" Required): There is no direct link between AP_CHECKS and AP_INVOICES_ALL because a single check can pay multiple invoices, and a single invoice can be paid by partial checks. You must use the bridge table AP_INVOICE_PAYMENTS_ALL.
•	Join Path: AP_CHECKS.CHECK_ID = AP_INVOICE_PAYMENTS_ALL.CHECK_ID, then AP_INVOICE_PAYMENTS_ALL.INVOICE_ID = AP_INVOICES_ALL.INVOICE_ID.
Supplier Identity (VENDOR_ID vs. REMIT_TO): Use VENDOR_ID to join to AP_SUPPLIERS for reporting the supplier's history. However, if you are reproducing a check copy or need the exact name printed on the document, use REMIT_TO_SUPPLIER_NAME from this table, as the master supplier name may have changed since the check was printed.
Excluding Voided Payments: When calculating "Total Cash Spent," you must filter out voided checks. A record is effectively void if STATUS_LOOKUP_CODE = 'VOIDED' or if VOID_DATE is NOT NULL. Often, voided checks are excluded from standard reports, or shown separately.
Bank Reconciliation (CLEARED_DATE): The CHECK_DATE is when the company recorded the payment. The CLEARED_DATE is when the bank recorded the withdrawal. If CLEARED_DATE is NULL, the funds are still "In Transit" (Float).
Oracle Payments Integration (IBY): Modern Oracle versions use a separate module (Oracle Payments) to handle the formatting and transmission. Columns like PAYMENT_ID, PAYMENT_INSTRUCTION_ID, and PAYMENT_PROFILE_ID are used to join to the IBY schema (e.g., IBY_PAYMENTS_ALL) for technical details on XML transmission or bank file status.
Address Snapshots: Do not join to AP_SUPPLIER_SITES_ALL to get the address if you need historical accuracy. Use ADDRESS_LINE1, CITY, ZIP on this table, as they represent the address frozen at the moment of payment creation.

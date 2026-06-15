Table Description
Table Name: ap_invoice_payments_all
Record Count: 334,450
Complete Description:
This is the critical "bridge" table (association entity) that links Invoices (AP_INVOICES_ALL) to Payments (AP_CHECKS_ALL). Because a single check can pay multiple invoices, and a single invoice can be paid by multiple partial payments, this table is necessary to resolve the Many-to-Many relationship. It stores the specific portion of a payment amount applied to a specific invoice, along with any discounts taken or lost during that specific transaction.
Natural representation description:
This table represents the "Remittance Advice" or "Payment Application" detail. It answers the questions: "Which specific invoices were paid by Check #100?", "How much of the total check amount was applied to Invoice A vs. Invoice B?", and "Did we take a prompt payment discount on this specific transaction?"
________________________________________
Column Description Schema
INVOICE_PAYMENT_ID: This is the Primary Key for the table. It is the unique system-generated identifier for this specific application of funds to an invoice. Sample Data: 62097028, 61823328, 61906620
INVOICE_ID: A Foreign Key linking to AP_INVOICES_ALL. It identifies the invoice being paid. Sample Data: 59009050
CHECK_ID: A Foreign Key linking to AP_CHECKS_ALL. It identifies the payment document (check/EFT) used to pay the invoice. Sample Data: 22059812, 21965823, 21979992
AMOUNT: The specific monetary amount from the check applied to this invoice. This is the "Paid Amount" for this transaction. Sample Data: 152.13, 302.06, 29.02
PAYMENT_NUM: Identifies the installment number of the invoice being paid. If an invoice has split payment terms, this indicates which split is being covered. Sample Data: 1, integer number
ACCOUNTING_DATE: The date this payment application is recognized in the General Ledger (GL Date). Sample Data: ######## (Date Format), 23-JAN-2025 00:00:00
PERIOD_NAME: The name of the accounting period corresponding to the Accounting Date. Sample Data: feb-25, JAN-25
ACCRUAL_POSTED_FLAG: A flag indicating if the accrual accounting entry for this payment has been posted to the General Ledger. Sample Data: Y, N
POSTED_FLAG: A flag indicating if the cash basis accounting entry has been posted to the General Ledger. Sample Data: Y, N
SET_OF_BOOKS_ID: A Foreign Key linking to GL_SETS_OF_BOOKS (or GL_LEDGERS). Identifies the financial ledger. Sample Data: 1
ACCTS_PAY_CODE_COMBINATION_ID: A Foreign Key linking to GL_CODE_COMBINATIONS. Represents the Liability account (Accounts Payable) being relieved (debited) by this payment. Sample Data: N/A, numerical ID
ASSET_CODE_COMBINATION_ID: A Foreign Key linking to GL_CODE_COMBINATIONS. Represents the Cash or Asset account (Bank Account) being credited. Sample Data: 16022939
DISCOUNT_TAKEN: The amount of discount actually taken on this specific payment. This reduces the cash paid but clears the full invoice liability. Sample Data: 4.71, N/A
DISCOUNT_LOST: The amount of discount available that was not taken (usually because the payment was late). Sample Data: 0, any other number 
CREATED_BY: An audit Foreign Key linking to the Users table, identifying who created the record. Sample Data: 163436, 163441
CREATION_DATE: An audit timestamp indicating when the record was created. Sample Data: ######## (Date Format), 21-JAN-2025 11:22:47
LAST_UPDATED_BY: An audit Foreign Key linking to the Users table, identifying who last modified the record. Sample Data: 19910
LAST_UPDATE_DATE: An audit timestamp indicating when the record was last modified. Sample Data: ######## (Date Format), 21-JAN-2025 20:45:31
ORG_ID: The Operating Unit identifier. Partitions data by business unit. Sample Data: 0
INVOICING_PARTY_ID: A Foreign Key to HZ_PARTIES. Identifies the supplier party on the invoice. Sample Data: 774066, 7913470, 737586
INVOICING_PARTY_SITE_ID: A Foreign Key to HZ_PARTY_SITES. Identifies the specific supplier address on the invoice. Sample Data: 210023, 7004097, 156668
INVOICING_VENDOR_SITE_ID: A Foreign Key to AP_SUPPLIER_SITES_ALL. Legacy link to the supplier site. Sample Data: 73656, 4754955, 88704
REMIT_TO_SUPPLIER_NAME: The name of the supplier to whom the payment was sent. Matches the Check header. Sample Data: FRESENIUS USA INC, ASD HEALTHCARE, FEDERAL EXPRESS
REMIT_TO_SUPPLIER_ID: The Vendor ID of the payee. Sample Data: 6406, 7706267, 5942
REMIT_TO_SUPPLIER_SITE: The site name where the payment was sent. Sample Data: DORCHESTER, CHICAGO, PITTSBURGH1
REMIT_TO_SUPPLIER_SITE_ID: The Site ID where the payment was sent. Sample Data: 73656, 4754955, 88704
________________________________________
Join to other tables with these considerations in mind:
The "Bridge" Function:
This is the most important table for joining the Payables module together.
•	To see what check paid an invoice: Join AP_INVOICES_ALL.INVOICE_ID = AP_INVOICE_PAYMENTS_ALL.INVOICE_ID, then AP_INVOICE_PAYMENTS_ALL.CHECK_ID = AP_CHECKS_ALL.CHECK_ID.
•	You cannot reliably skip this table.
Calculating "Amount Paid" on an Invoice:
Do not look at AP_INVOICES_ALL.AMOUNT_PAID for real-time calculation if you are auditing. Instead, sum the AMOUNT column in AP_INVOICE_PAYMENTS_ALL grouped by INVOICE_ID.
•	Note: Ensure you include DISCOUNT_TAKEN in your summation if you are trying to determine how much Liability was relieved, vs AMOUNT if you only care about Cash Outflow.
Reversals and Voids:
When a check is voided, Oracle typically creates a new row in this table with the same INVOICE_ID and CHECK_ID but a negative AMOUNT.
•	When summing data, a simple SUM(AMOUNT) works well because the original positive payment and the subsequent negative void line will net to zero.
Accounting (Cash vs. Liability):
•	ACCTS_PAY_CODE_COMBINATION_ID represents the Liability account (Credit Invoice / Debit Payment).
•	ASSET_CODE_COMBINATION_ID represents the Bank/Cash account (Debit Cash Receipt / Credit Payment).
•	Use these columns joined to GL_CODE_COMBINATIONS to generate "Cash Basis" accounting reports.
Partial Payments:
If AP_INVOICE_PAYMENTS_ALL.AMOUNT < AP_INVOICES_ALL.INVOICE_AMOUNT, the invoice was only partially paid. You can track the remaining balance by comparing the sum of these payments against the invoice header total.


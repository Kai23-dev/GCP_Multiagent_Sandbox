Table Description
Table Name: ap_invoice_distributions_all
Record Count: 3,362,349
Complete Description:
This table contains the detailed accounting distributions for invoice lines. It represents the lowest level of detail for an invoice. While the Invoice Header contains the supplier and total amount, and the Invoice Line describes what was purchased (e.g., "10 Laptops"), the Distribution determines how that cost is allocated in the General Ledger (e.g., "50% to IT Dept Cost Center, 50% to HR Dept Cost Center"). It holds the specific General Ledger (GL) accounts, tax distributions, and links to Purchase Orders or Receipts for matching.
Natural representation description:
This table represents the "Coding" or "Allocation" of the invoice. It answers the questions: "Which department budget gets charged?", "What is the specific Expense or Asset account?", "How much tax was calculated on this specific line item?", and "Is this cost matched to a specific PO Receipt?"
________________________________________
Column Description Schema
INVOICE_DISTRIBUTION_ID: This is the Primary Key for the table. It is the unique system-generated identifier for this specific accounting line. Sample Data: 8.1E+08 (Scientific notation in sample, represents numeric ID like 810000000)
INVOICE_ID: A Foreign Key linking to the AP_INVOICES_ALL table. It identifies the parent invoice to which this distribution belongs. Sample Data: 59895360
INVOICE_LINE_NUMBER: A Foreign Key (partially) linking to AP_INVOICE_LINES_ALL. It identifies which specific line item on the invoice this distribution belongs to. Sample Data: 6
DISTRIBUTION_LINE_NUMBER: The sequence number of the distribution within the invoice line (e.g., Split 1, Split 2). Sample Data: 2, 3, 4
DIST_CODE_COMBINATION_ID: A Foreign Key linking to GL_CODE_COMBINATIONS. This is the "Debit" account (Expense, Asset, or Tax account) where the cost will be booked in the General Ledger. Sample Data: 19910
AMOUNT: The monetary value of this specific distribution line in the invoice currency. Sample Data: 0, or any given amount
ACCOUNTING_DATE: The GL Date. This determines the accounting period in which this expense or liability will be recorded. Sample Data: ######## (Date Format)
PERIOD_NAME: The name of the accounting period corresponding to the Accounting Date. Sample Data: mar-25
ACCRUAL_POSTED_FLAG: A flag indicating if the accrual entry has been posted to the General Ledger. 'Y' means it has been processed. Sample Data: Y, N
SET_OF_BOOKS_ID: A Foreign Key linking to GL_SETS_OF_BOOKS (or GL_LEDGERS). Identifies the financial ledger this transaction belongs to. Sample Data: 1, internal ID
ACCTS_PAY_CODE_COMBINATION_ID: A Foreign Key to GL_CODE_COMBINATIONS. It represents the Liability (Credit) account, though this is often derived from the header. Sample Data: N/A, internal ID
BASE_AMOUNT: The amount converted to the functional (base) currency of the ledger. Used if the invoice is in a foreign currency. Sample Data: 0 or any amount
BATCH_ID: A Foreign Key linking to GL_JE_BATCHES (if posted) or an AP Batch ID, grouping these records for processing. Sample Data: 7386964
CREATED_BY: An audit Foreign Key linking to the Users table, identifying who created the record. Sample Data: 19910
CREATION_DATE: An audit timestamp indicating when the record was created. Sample Data: ######## (Date Format)
DESCRIPTION: A text description of the distribution, often copied from the invoice line or PO line. Sample Data: SALES TAX
MATCH_STATUS_FLAG: Indicates the validation status of the distribution (e.g., 'A' for Approved/Validated). Sample Data: A
POSTED_FLAG: A flag indicating if the expense/liability journal entry has been transferred to the General Ledger. Sample Data: Y, N
PO_DISTRIBUTION_ID: A Foreign Key linking to PO_DISTRIBUTIONS_ALL. If this invoice is matched to a Purchase Order, this links to the specific PO funding line. Sample Data: 78954495, 78954496, 78954497
PROGRAM_APPLICATION_ID: Audit column identifying the application ID of the concurrent program that last updated the record. Sample Data: 20026
PROGRAM_ID: Audit column identifying the specific concurrent program execution ID. Sample Data: 192516
PROGRAM_UPDATE_DATE: Audit timestamp of the last concurrent program update. Sample Data: ######## (Date Format)
QUANTITY_INVOICED: The quantity of items associated with this distribution (e.g., matching 5 units). Sample Data: N/A, number of items
REVERSAL_FLAG: A flag indicating if this line is a reversal of another line. Sample Data: N/A, Y, N
TYPE_1099: The income tax type associated with this distribution (e.g., MISC7), used for 1099 reporting. Sample Data: N/A, tax codes
UNIT_PRICE: The price per unit for the items in this distribution. Sample Data: N/A, price
ORG_ID: The Operating Unit identifier. This partitions data by business unit. Sample Data: 0, other ID
DIST_MATCH_TYPE: Indicates how the distribution was matched (e.g., 'NOT_MATCHED', 'MATCH_PO', 'MATCH_RECEIPT'). Sample Data: NOT_MATCHED
RCV_TRANSACTION_ID: A Foreign Key linking to RCV_TRANSACTIONS. Used for 3-way matching to link the invoice cost to a specific goods receipt. Sample Data: N/A, any other ID
ACCOUNTING_EVENT_ID: A Foreign Key linking to the Subledger Accounting (SLA) engine (XLA_EVENTS). Used to trace how the accounting entries were generated. Sample Data: 2.92E+08 (Numeric ID)
CANCELLATION_FLAG: A flag indicating if the distribution has been cancelled. Sample Data: N, Y
CORRECTED_INVOICE_DIST_ID: If this line is a correction, this Foreign Key points to the original INVOICE_DISTRIBUTION_ID being corrected. Sample Data: N/A, corrected ID
RELATED_ID: Used for Tax lines. It points to the INVOICE_DISTRIBUTION_ID of the Item line that generated this tax line. Sample Data: N/A, numerical IDs
DISTRIBUTION_CLASS: Categorizes the distribution (e.g., 'PERMANENT', 'TAX'). Sample Data: PERMANENT
TAX_ALREADY_DISTRIBUTED_FLAG: A flag used by the tax engine to indicate if tax has been calculated and allocated. Sample Data: N/A, Y, N
TOTAL_DIST_AMOUNT: The total amount for the distribution, including any related tax or freight allocations. Sample Data: 0, any amount
TOTAL_DIST_BASE_AMOUNT: The total functional currency amount for the distribution. Sample Data: 0, any amount
CANCELLED_FLAG: A boolean flag (Y/N) usually synced with CANCELLATION_FLAG to indicate if the line is void. Sample Data: N/A, Y, N
LAST_UPDATED_BY: An audit Foreign Key linking to the Users table (FND_USER), identifying who last modified the record. Sample Data: 19910
LAST_UPDATE_DATE: An audit timestamp indicating when the record was last modified. Sample Data: ######## (Date Format)
LINE_TYPE_LOOKUP_CODE: Describes the type of cost (e.g., 'ITEM', 'TAX', 'FREIGHT', 'NONREC_TAX'). Sample Data: NONREC_TAX
________________________________________
Join to other tables with these considerations in mind:
Hierarchy Navigation (Parent-Child):
•	To Invoice Header: Join INVOICE_ID to AP_INVOICES_ALL.INVOICE_ID.
•	To Invoice Lines: Join INVOICE_ID and INVOICE_LINE_NUMBER to AP_INVOICE_LINES_ALL. Note that in older versions of Oracle, distributions could exist without lines, but in modern schemas, the Line is the intermediate parent.
General Ledger Coding (DIST_CODE_COMBINATION_ID):
This is the most critical join for financial reporting. Join DIST_CODE_COMBINATION_ID to GL_CODE_COMBINATIONS.CODE_COMBINATION_ID. This allows you to retrieve the concatenated segments (e.g., "01-100-5000-00") to see which Company, Department, and Account is being charged.
Purchase Order Matching (PO_DISTRIBUTION_ID):
To see what Purchase Order corresponds to this cost, join PO_DISTRIBUTION_ID to PO_DISTRIBUTIONS_ALL.PO_DISTRIBUTION_ID. From there, you can navigate up to PO_HEADERS_ALL. This is essential for "PO vs. Invoice" variance analysis.
Subledger Accounting (SLA) vs. Distributions:
In modern Oracle (R12 and Cloud), AP_INVOICE_DISTRIBUTIONS_ALL is the source of truth for the invoice module, but the final accounting is stored in the SLA tables (XLA_AE_LINES). Join ACCOUNTING_EVENT_ID to XLA_EVENTS to trace the final posted journal entries, especially if complex accounting rules override the default distribution codes.
Tax Association:
If LINE_TYPE_LOOKUP_CODE is 'TAX' or 'NONREC_TAX', the RELATED_ID column often points to the INVOICE_DISTRIBUTION_ID of the 'ITEM' line that triggered the tax. This allows you to group the cost of an item plus its associated tax.
Filtering Cancelled/Reversed Lines:
When summing amounts for reports, ensure you check REVERSAL_FLAG and CANCELLATION_FLAG. Often, a reversal creates a new line with a negative amount and REVERSAL_FLAG = 'Y'. Simply summing AMOUNT usually works (as they net out), but for counting transactions, you may want to exclude them.


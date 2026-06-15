Table Description
Table Name: XXC_GL_SUMMARY_OCT_2025
Record Count: 13,789,400
Complete Description:
This is a high-volume custom "Fact" or "Snapshot" table designed for financial reporting. It represents a flattened view of the General Ledger (GL) for a specific period (October 2025). It bridges the gap between high-level GL Balances and detailed Subledger transactions. It joins data from the General Ledger (GL_JE_LINES), Subledger Accounting (XLA_AE_LINES), and Accounts Payable (AP_INVOICES, AP_CHECKS) into a single record per transaction line. This eliminates the need for complex, resource-intensive joins during month-end reporting.
Natural representation description:
This table acts as the "Detailed General Ledger" for October 2025. It answers questions like: "What specific invoices make up the $50,000 balance in the Office Supplies account?" or "Which payments were cleared in this GL period?" It provides the full lineage of a financial transaction from the Journal Entry back to the original Purchase Order or Check.
________________________________________
Column Description Schema
PERIOD_DATE: The end date of the financial period. Used for aging and reporting buckets. Sample Data: 31-OCT-2025 *format may change
CODE_COMBINATION_ID: A Foreign Key to GL_CODE_COMBINATIONS. This is the unique ID for the full Chart of Accounts string (the GL Account). Sample Data: 16465810
LEGAL_ENTITY: The segment representing the registered legal company. Sample Data: 200466
LOCATION: The segment representing the physical location or facility. Sample Data: 5384
DEPARTMENT: The segment representing the cost center. Sample Data: 0000, 0400,1100
ACCOUNT: The natural account segment (Assets, Liabilities, Expenses). Sample Data: 1600
ACCOUNT_NAME: The human-readable description of the Account segment. Sample Data: New Oracle Intercompany
SUB_ACCOUNT: A sub-classification segment for the account. Sample Data: 000, 310, 315
SUB_ACCOUNT_NAME: The description of the sub-account. Sample Data: N/A, CAPD Training, Disaster Related Expenditures
FINANCIAL_CLASS: A reporting classification used to group accounts for statements. Sample Data: 000, 050, 070
SPECIAL_REPORTING: A flexible segment used for specific statutory or internal reporting needs. Sample Data: 00822, 00035
FUTURE2: A placeholder segment reserved for future use. Sample Data: 000000
PO_NUMBER: The Purchase Order number associated with the invoice (if applicable). This links to the Procurement system. Sample Data: N/A, 95080-1119942, DVA-01270755
JE_CATEGORY: The category of the Journal Entry (e.g., 'Purchase Invoices', 'Payments'). Sample Data: Purchase Invoices
JE_CATEGORY_NAME: The user-facing name of the journal category. Sample Data: Purchase Invoices
USER_JE_CATEGORY_NAME: The translated or user-specific name for the category. Sample Data: Purchase Invoices
JE_SOURCE: The origin of the transaction (e.g., 'Payables', 'Spreadsheet'). Sample Data: Payables
JE_SOURCE_NAME: The user-facing name of the source. Sample Data: Payables
USER_JE_SOURCE_NAME: The translated or user-specific name for the source. Sample Data: Payables
LINE_DESCRIPTION: The text description entered on the journal line, often explaining the expense. Sample Data: Intracompany Line
VENDOR_NAME: The name of the supplier (derived from AP_SUPPLIERS). Sample Data: VANTIVE US HEALTHCARE LLC
CATEGORY: A high-level grouping of the expense or asset (e.g., 'Interco Rev'). Sample Data: Interco Rev Fr Unconsolidated Part.
SUPER_CATEGORY: A broad financial aggregation category (e.g., 'Current Assets'). Sample Data: Current Assets
AMOUNT: The monetary value of the transaction line in the functional currency. Sample Data: -8.85, -21.42, -25, 7903
EFFECTIVE_DATE: The date the transaction impacts the GL balance. Sample Data: 10/31/2025
VENDOR_ID: A Foreign Key linking to AP_SUPPLIERS. Identifies the unique supplier record. Sample Data: 8175038
VENDOR_SITE_ID: A Foreign Key linking to AP_SUPPLIER_SITES_ALL. Identifies the specific supplier address used. Sample Data: 5208324
STAT_AMOUNT: Statistical quantity associated with the line (e.g., headcount, square footage), if applicable. Sample Data: N/A, 23.24, -124.3
GLRPT_REPORT_TYPE: A custom classification for specific GL Reports (Balance Sheet vs P&L). Sample Data: BS ASSETS
GLRPT_CATEGORY: Custom reporting category hierarchy Level 1. Sample Data: CURRENT ASSETS
GLRPT_SUB_CATEGORY: Custom reporting category hierarchy Level 2. Sample Data: INTERCO RECV FR UNCONSOL PART
GLRPT_LINE_ITEM: Specific line item mapping for financial statements. Sample Data: 9376870
JE_HEADER_ID: A Foreign Key to GL_JE_HEADERS. The specific Journal Entry group this line belongs to. Sample Data: 7335, 7336, 7337
JE_LINE_NUM: The specific line number within the Journal Entry. Sample Data: 325740, 242856
JE_POSTED_DATE: The audit timestamp when the journal was posted to the GL. Sample Data: 10/17/2025 1:15:12 AM
XXC_SUMM_CREATED: Audit timestamp indicating when this summary record was generated. Sample Data: N/A, 10/11/2025 1:15:13 AM
AP_ATTRB7_AFE: Descriptive flexfield from AP, often used for "Authority for Expenditure" or project codes. Sample Data: DVAAPNP, N/A
BATCH_NAME: The name of the Journal Entry batch. Sample Data: Payables A 20012953 86453375 2025-09-02_43894391
INV_DESCRIPTION: The description from the original Invoice Header. Sample Data: TRAVEL REIMB_HOMEFa Class, TRAVEL REIMB_HOME1Travel PCT 9/24-10/20
INV_CREATION_DATE: The date the invoice was created in the system. Sample Data: 10/22/2025 12:11:17 PM
AE_HEADER_ID: A Foreign Key to XLA_AE_HEADERS. Links to the Subledger Accounting engine, the bridge between AP and GL. Sample Data: 3, 7, 8
AE_LINE_NUM: The specific line number in the Subledger Accounting entry. Sample Data: 62049764, 62049872
INVOICE_ID: A Foreign Key to AP_INVOICES_ALL. This allows a direct join to the invoice transaction. Sample Data: 611
INTERCOMPANY: A segment or flag indicating if the transaction is between internal entities. Sample Data: 611
CURRENCY_CODE: The currency of the transaction. Sample Data: USD
LEDGER_ID: A Foreign Key to GL_LEDGERS. Identifies the set of books (Currency, Calendar, COA). Sample Data: 23741830, 23578041
CHECK_ID: A Foreign Key to AP_CHECKS_ALL. If paid, this links to the payment record. Sample Data: 923575, 914163
CHECK_NUMBER: The physical or electronic check number. Sample Data: 11/14/2025 (Data mismatch - usually numeric), 10/24/2025
CHECK_DATE: The date the payment was issued. Sample Data: 10/22/2025 12:11:17 PM
CHK_CREATION_DATE: The audit date when the check record was created. Sample Data: 10/22/2025 12:11:17 PM
API_ATTRB3_LOC: Descriptive flexfield from the AP Invoice, likely capturing a location code. Sample Data: N/A
REFERENCE_2: Generic reference column, often storing the Invoice ID or old legacy system ID. Sample Data: N/A
REFERENCE_3: Generic reference column, often storing distribution IDs. Sample Data: N/A
COMMODITY: A classification code for the type of goods purchased. Sample Data: N/A, Wireless Headsets & Accessories (7685), Wireless Headsets & Accessories (7685)
________________________________________
Join to other tables with these considerations in mind:
Snapshot Table Warning: This table (XXC_GL_SUMMARY_OCT_2025) is likely a static "snapshot" table created specifically for October 2025 reporting. It will not contain live updates. If you need real-time data or data for a different month (e.g., November), you must look for the table corresponding to that period (e.g., XXC_GL_SUMMARY_NOV_2025).
General Ledger Reconciliation (CODE_COMBINATION_ID): To validate balances against the official GL, join CODE_COMBINATION_ID to GL_BALANCES. Remember that this table contains detailed lines, so you must SUM(AMOUNT) and group by CODE_COMBINATION_ID to match the GL_BALANCES figures.
Drill-Back to AP (INVOICE_ID): Use INVOICE_ID to join to AP_INVOICES_ALL for granular invoice headers. Do not rely solely on the INVOICE_NUMBER column (seen in sample data but not attribute list) for joins, as invoice numbers are not unique across different vendors. Always use the numeric INVOICE_ID.
Payment Details (CHECK_ID): If CHECK_ID is populated, the invoice has been paid. Join to AP_CHECKS_ALL to see payment status (Cleared, Voided, Negotiable). If CHECK_ID is NULL, the liability is likely still open (unpaid).
Subledger Accounting (AE_HEADER_ID): This is the most accurate link between the GL and the Subledger. Joining AE_HEADER_ID to XLA_AE_HEADERS and XLA_AE_LINES provides the exact accounting rules used to generate the debits and credits.
Vendor Information: While VENDOR_NAME is present here, it is denormalized text. For official supplier details (Tax ID, current address), always join VENDOR_ID to AP_SUPPLIERS.
Sample Data Mismatch Note: The provided sample data contained data shifts (e.g., Dates appearing in ID columns or descriptions). When querying, ensure you validate data types. For example, JE_LINE_NUM should be numeric, but sample data showed a timestamp. Trust the column name logic (IDs are numbers, Dates are dates) over the specific sample row alignment.


Table Description
Table Name: ap_invoice_lines_all
Record Count: 1,650,850
Complete Description:
This table stores the line-item details of an invoice. While the invoice header (AP_INVOICES_ALL) represents the document (the "envelope"), this table represents the actual contents. It defines what was purchased (e.g., specific goods, services, tax charges, or freight) and provides the link between the invoice and the Purchase Order or Receipt at the detailed level. It is the parent of the AP_INVOICE_DISTRIBUTIONS_ALL table.
Natural representation description:
This table represents the "Itemized Bill." It answers the questions: "What specific items are listed on this invoice?", "Is this line for a product, a tax charge, or a shipping fee?", "Which specific line on the Purchase Order does this bill correspond to?", and "How much does this specific line-item cost?"
________________________________________
Column Description Schema
INVOICE_ID: This is part of the Composite Primary Key. It is a Foreign Key linking to AP_INVOICES_ALL. It identifies the invoice document to which this line belongs. Sample Data: 59932374
LINE_NUMBER: This is the second part of the Composite Primary Key. It is the unique sequence number of the line within the specific invoice. Sample Data: 8, 9, 10
LINE_TYPE_LOOKUP_CODE: A classification code describing the nature of the line item (e.g., 'ITEM' for goods/services, 'TAX' for tax lines, 'FREIGHT'). Sample Data: ITEM
DESCRIPTION: The detailed text description of the line item, often copied from the Purchase Order or entered manually. Sample Data: 4_TR_102408_CURITY ALLPUR SPONGE 2X2 4PLY 25/TR____, 2_TR_900166_GAUZE VERSALON 4X4...
LINE_SOURCE: Indicates the origin of the invoice line (e.g., 'MANUAL' for user entry, 'IMPORTED' for lines coming from external systems or matching processes). Sample Data: IMPORTED
ORG_ID: The Operating Unit identifier. This partitions data by business unit. Sample Data: ######## (Numeric Value)
LINE_GROUP_NUMBER: A grouping identifier used to associate related lines together (e.g., an Item line and its specific Tax line might share a group number). Sample Data: N/A, 0
INVENTORY_ITEM_ID: A Foreign Key linking to MTL_SYSTEM_ITEMS. It identifies the specific Master Item being billed. Sample Data: N/A, internal ID
ITEM_DESCRIPTION: A snapshot of the item description at the time of invoice creation. Sample Data: N/A, description of product
ACCOUNT_SEGMENT: Used to override the natural account segment of the General Ledger code, though rarely used in standard matching. Sample Data: N/A, general ledger code, numeric
DEFAULT_DIST_CCID: A Foreign Key linking to GL_CODE_COMBINATIONS. It represents the default Expense/Asset account (Code Combination ID) assigned to this line. Sample Data: 8409730
PRORATE_ACROSS_ALL_ITEMS: A flag (Y/N) often used for Freight or Misc lines to indicate if this cost should be allocated proportionally across the other Item lines. Sample Data: N/A, Y, N
ACCOUNTING_DATE: The GL Date for the line. This determines the financial period in which the expense is recognized. Sample Data: 03-APR-2025 00:00:00
PERIOD_NAME: The name of the accounting period corresponding to the Accounting Date. Sample Data: APR-25
SET_OF_BOOKS_ID: A Foreign Key linking to the Ledger (GL_SETS_OF_BOOKS or GL_LEDGERS). Sample Data: 1, or any other identifier
AMOUNT: The monetary value of this specific line item. Sample Data: 4.08, 2.12, 5.76
DISCARDED_FLAG: A boolean flag (Y/N) indicating if this specific line was discarded (effectively deleted/voided without removing the record). Sample Data: N, Y
CANCELLED_FLAG: A boolean flag (Y/N) indicating if the entire invoice (and thus this line) was cancelled. Sample Data: N, Y
PO_HEADER_ID: A Foreign Key linking to PO_HEADERS_ALL. Used if the invoice line is matched to a Purchase Order. Sample Data: N/A, numeric Ids
PO_LINE_ID: A Foreign Key linking to PO_LINES_ALL. Identifies the specific line on the PO being billed. Sample Data: N/A, numeric Ids
PO_RELEASE_ID: A Foreign Key linking to PO_RELEASES_ALL. Used for Blanket Purchase Agreements releases. Sample Data: N/A, numeric Ids
PO_LINE_LOCATION_ID: A Foreign Key linking to PO_LINE_LOCATIONS_ALL. Identifies the specific shipment schedule being billed. Sample Data: N/A, numeric Ids
PO_DISTRIBUTION_ID: A Foreign Key linking to PO_DISTRIBUTIONS_ALL. Identifies the specific funding line on the PO. Sample Data: N/A, numeric Ids
RCV_TRANSACTION_ID: A Foreign Key linking to RCV_TRANSACTIONS. Used for 3-way matching to link the invoice cost to a specific goods receipt transaction. Sample Data: N/A, numeric Ids
CREATION_DATE: An audit timestamp indicating when this record was created. Sample Data: 03-APR-2025 06:24:52
CREATED_BY: An audit Foreign Key linking to the Users table, identifying who created the record. Sample Data: 19910
LAST_UPDATED_BY: An audit Foreign Key linking to the Users table, identifying who last modified the record. Sample Data: 19910
LAST_UPDATE_DATE: An audit timestamp indicating when the record was last modified. Sample Data: 03-APR-2025 20:38:04
ATTRIBUTE8: A Descriptive Flexfield (DFF) segment used to store custom, client-specific data. Sample Data: P
SHIP_TO_LOCATION_ID: A Foreign Key linking to HR_LOCATIONS (or HZ_LOCATIONS). Defines the physical location where goods were shipped. Sample Data: 10575
________________________________________
Join to other tables with these considerations in mind:
Primary Key Structure:
Unlike the Header or Check tables, this table uses a Composite Primary Key. You must uniquely identify a record using a combination of INVOICE_ID AND LINE_NUMBER.
Linking Down to Distributions (Allocations):
To see how a specific line is accounted for in the GL, join to AP_INVOICE_DISTRIBUTIONS_ALL.
•	Join Path: AP_INVOICE_LINES_ALL.INVOICE_ID = AP_INVOICE_DISTRIBUTIONS_ALL.INVOICE_ID AND AP_INVOICE_LINES_ALL.LINE_NUMBER = AP_INVOICE_DISTRIBUTIONS_ALL.INVOICE_LINE_NUMBER.
Linking Up to Headers (Vendor/Total):
To get the Vendor name or the total Invoice status, join to AP_INVOICES_ALL.
•	Join Path: AP_INVOICE_LINES_ALL.INVOICE_ID = AP_INVOICES_ALL.INVOICE_ID.
Purchase Order Matching (The "2-Way" or "3-Way" Match):
•	PO Header: Use PO_HEADER_ID to join to PO_HEADERS_ALL.
•	PO Line: Use PO_LINE_ID to join to PO_LINES_ALL.
•	If PO_HEADER_ID is populated, this line is "Matched." If it is NULL, this is likely a "Direct" or "Manual" invoice line not backed by a PO.
Inventory Items:
If INVENTORY_ITEM_ID is populated, join to MTL_SYSTEM_ITEMS_B (using INVENTORY_ITEM_ID and ORG_ID) to get standardized product codes and descriptions, rather than relying on the free-text DESCRIPTION column.
Discarded vs. Cancelled Lines:
When summing AMOUNT to calculate total spend, you must exclude invalid lines.
•	Filter out lines where DISCARDED_FLAG = 'Y'.
•	Filter out lines where CANCELLED_FLAG = 'Y'.
•	Note: A "Discarded" line is specific to the line itself being removed. A "Cancelled" line usually happens when the header is cancelled.
Default Account (DEFAULT_DIST_CCID):
While this column exists (DEFAULT_DIST_CCID), it is effectively a "suggestion" for the distribution. The actual accounting happens in AP_INVOICE_DISTRIBUTIONS_ALL. Do not use DEFAULT_DIST_CCID for final financial reporting; use the Distribution table instead.

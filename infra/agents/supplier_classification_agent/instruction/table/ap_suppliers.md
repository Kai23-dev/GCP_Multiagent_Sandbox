Table Description
Table Name: ap_suppliers
Record Count: 1,150
Complete Description:
This table serves as the master repository for all external suppliers (vendors) with whom the business conducts trade. It contains the legal entity details, unique system identifiers, payment preferences, tax compliance status (1099), and operational states (active/inactive or on hold). Use this table to resolve Vendor IDs to names, look up Oracle Vendor Numbers (Segment1), and validate if a supplier is eligible to receive payments or purchase orders.
Natural representation description:
This table acts as the master directory for all external suppliers and vendors. It contains the core identity information (Names, Tax IDs), financial settings (Currencies, Payment Terms), and operational status (Active/Inactive, Holds) for entities the business pays.
________________________________________
 Column Description Schema
VENDOR_ID: This is the Primary Key for the table. It is the unique system-generated identifier for the supplier. Other tables (such as Invoices, Purchase Orders, and Payments) use this ID to join to this record. Sample Data: 1820128, 69200, 6710528
SEGMENT1: This serves as the public "Supplier Number." It is a unique business key used by human operators to search for suppliers, though it is not the system’s primary key. Sample Data: 191097, 65495, 332221 
VENDOR_NAME: The full legal name of the supplier entity or individual. Sample Data: 489Z+)s$$8V, UMASS MEMORIAL MEDICAL GROUP INC, WALGREENS-STORE 12365 
VENDOR_TYPE_LOOKUP_CODE: A classification code describing the type of vendor (e.g., "VENDOR", "EMPLOYEE", "CONTRACTOR"). This is likely joining a Lookup or QuickCode table for validation. Sample Data: VENDOR, Rents and Fees, Rents and Fees 
ENABLED_FLAG: A boolean indicator (Y/N) specifying if the vendor is currently enabled for use in the system. Sample Data: Y, N 
START_DATE_ACTIVE: The date when the vendor relationship became active. Sample Data: 05-DEC-2012 00:00:00, 16-MAY-2005 00:00:00, 18-APR-2019 00:00:00 
END_DATE_ACTIVE: The date when the vendor relationship ceased. If this is NULL, the vendor is still considered active. Sample Data: N/A, DATES 
ORGANIZATION_TYPE_LOOKUP_CODE: A code defining the legal structure of the supplier (e.g., "CORPORATION", "INDIVIDUAL", "GOVERNMENT"). This joins to a Lookup table. Sample Data: INDIVIDUAL, CORPORATION, CORPORATION 
NUM_1099: The Tax Identification Number (TIN), Social Security Number, or VAT ID used for tax reporting purposes. Sample Data: N/A, 04-2911067, 36-1924025 
TYPE_1099: The specific tax form type required for this vendor (e.g., "MISC", "INT"). Sample Data: MISC7, MISC6, N/A 
TAX_REPORTING_NAME: The specific name to be printed on government tax documents if it differs from the VENDOR_NAME. Sample Data: 489Z+)s$$8V, UMASS MEMORIAL MEDICAL GROUP INC, WALGREEN CO 
FEDERAL_REPORTABLE_FLAG: A boolean flag (Y/N) indicating if payments to this vendor must be reported to the federal tax authority (IRS). Sample Data: Y, N, N/A
STATE_REPORTABLE_FLAG: A boolean flag (Y/N) indicating if payments to this vendor must be reported to state tax authorities. Sample Data: Y, N, N/A 
TAX_VERIFICATION_DATE: The date on which the vendor's tax identification information was verified against government records. Sample Data: 07-FEB-2024 00:00:00, 08-NOV-2021 00:00:00, 18-APR-2019 00:00:00 
NAME_CONTROL: The first four characters of the surname or company name, used specifically for IRS B-Notice name matching. Sample Data: BAST, UMAS, WALG 
INVOICE_CURRENCY_CODE: The default currency code (e.g., "USD") assigned to new invoices created for this vendor. This joins to the Currencies table. Sample Data: USD
PAYMENT_CURRENCY_CODE: The default currency code used for issuing payments to this vendor. This joins to the Currencies table. Sample Data: USD 
TERMS_ID: A Foreign Key that links to the Payment Terms table. It defines the default payment schedule (e.g., "Net 30") applied to this vendor's invoices. Sample Data: 10032, 10032, 10032 
TERMS_DATE_BASIS: A rule defining what date triggers the start of payment terms (e.g., the Invoice Date vs. the Goods Receipt Date). Sample Data: Invoice 
PAYMENT_PRIORITY: A numerical value (1-99) used to prioritize this vendor during payment batch processing (e.g., paying high-priority vendors first when cash is low). Sample Data: 50, 65, 60 
HOLD_ALL_PAYMENTS_FLAG: A critical control flag (Y/N). If 'Y', the system prevents any payments from being issued to this vendor. Sample Data: N, Y 
HOLD_FUTURE_PAYMENTS_FLAG: A control flag (Y/N). If 'Y', the system prevents new invoices for this vendor from being selected for payment. Sample Data: N, Y
HOLD_FLAG: A general status flag indicating if the vendor is currently on hold. Sample Data: N, Y 
HOLD_REASON: A text description explaining why a payment hold was placed on the vendor. Sample Data: text description or null
PURCHASING_HOLD_REASON: A text description explaining why a hold was placed preventing new Purchase Orders. Sample Data: text description or null
HOLD_BY: The User ID of the person who placed the hold. This acts as a Foreign Key to the Users/Employees table. Sample Data: UserID or text description 
HOLD_DATE: The date the hold was applied. Sample Data: Date or null 
ATTRIBUTE8: A descriptive flexfield used to store custom, client-specific data not covered by standard columns. Sample Data: null 
ATTRIBUTE11: A descriptive flexfield used to store custom, client-specific data not covered by standard columns. Sample Data: DIRECT REFERRAL SOURCE, DIRECT REFERRAL SOURCE, REFERRAL SOURCE 
CREATION_DATE: An audit timestamp indicating when this record was first created. Sample Data: 05-DEC-2012 13:35:34, 16-MAY-2005 12:32:12, 18-APR-2019 15:05:44 
CREATED_BY: An audit Foreign Key linking to the Users table, identifying the user who created the record. Sample Data: 48811, 5362, 106439 
LAST_UPDATE_DATE: An audit timestamp indicating when this record was last modified. Sample Data: 15-JAN-2025 17:26:30, 15-JAN-2025 12:46:06, 04-FEB-2021 19:15:15 
LAST_UPDATED_BY: An audit Foreign Key linking to the Users table, identifying the user who performed the last modification. Sample Data: 150303, 149118, -1

Join to other tables with these considerations in mind:
Primary Transactional Join (VENDOR_ID): Always use VENDOR_ID as the absolute source of truth when joining to transactional tables like Invoices (e.g., AP_INVOICES_ALL), Purchase Orders (e.g., PO_HEADERS_ALL), and Payments (e.g., AP_CHECKS_ALL). Do not use VENDOR_NAME for joins, as names can change or contain special characters that cause mismatches. 
Human-Readable Search (SEGMENT1): If a user query refers to a specific "Vendor Number" or "Supplier Number" (e.g., "Find details for Supplier 191097"), query the SEGMENT1 column. However, once the record is found, switch immediately to VENDOR_ID to retrieve related financial records from other tables. 
Active Status Filtering: When joining to generate a list of "Current" or "Valid" suppliers for reports, you must apply filters. A vendor is only considered effectively active if ENABLED_FLAG = 'Y' AND (END_DATE_ACTIVE is NULL or greater than the current date). Ignoring these columns will result in retrieving obsolete or blacklisted vendors. 
Lookup Codes vs. IDs: Columns ending in _LOOKUP_CODE (like VENDOR_TYPE_LOOKUP_CODE and ORGANIZATION_TYPE_LOOKUP_CODE) usually join to a centralized "Lookups" or "QuickCodes" table on a string code basis, not a numeric ID. Use these to retrieve the verbose descriptions of the vendor type (e.g., turning "CORP" into "Corporation"). 
Payment Terms (TERMS_ID): Use TERMS_ID to join to the Payment Terms table. This is essential for calculating due dates on invoices. If TERMS_ID is NULL on the vendor record, the system often defaults to a system-wide setting, so the join should be treated as a Left Outer Join. 
Audit and User Tracking: Columns like CREATED_BY, LAST_UPDATED_BY, and HOLD_BY contain User IDs. Join these to the Users or Employees directory table (often FND_USER or PER_ALL_PEOPLE) to display the actual name of the person who modified the record or placed a hold. 
Currency Consistency: When joining to Invoice or Payment tables, compare the INVOICE_CURRENCY_CODE on this table against the actual transaction currency. A mismatch here usually triggers specific cross-currency exchange rate logic in the joining tables.

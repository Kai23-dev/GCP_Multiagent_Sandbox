Table Description
Table Name: ap_invoices_all
Record Count: 312,200
Complete Description:
This table contains records for invoices entering the Accounts Payable system. It serves as the header-level repository for all vendor invoices, expense reports, and credit memos. It stores the core details of the financial obligation, including the vendor identity, invoice amount, currency, payment status, and relevant dates (invoice date, GL date). This table is the parent record for invoice lines and distributions and is essential for liability reporting and payment processing.
Natural representation description:
This table represents the actual "Bill" received from a supplier. It acts as the central financial obligation record, linking the external supplier (Who we pay) to the internal liability (How much we owe). It tracks the lifecycle of the invoice from the moment it is entered, through validation and approval, to its final payment status.
________________________________________
Column Description Schema
INVOICE_ID: This is the Primary Key for the table. It is the unique system-generated identifier for the invoice. Other tables (such as Invoice Lines, Payments, and Holds) use this ID to join to this record. Sample Data: 59452126, 59452648, 59453060
LAST_UPDATE_DATE: An audit timestamp indicating when this record was last modified. Sample Data: feb-25
VENDOR_ID: A Foreign Key linking to the AP_SUPPLIERS table. This identifies the supplier who submitted the invoice. Sample Data: 8175038
INVOICE_NUM: The alphanumeric number assigned to the invoice by the supplier. This is the "Bill Number" used for reference and duplicate checking. Sample Data: VANCAP_TAXSUM__42516697, VANCAP_TAXSUM__42454665, VANCAP_TAXSUM__42423380
INVOICE_CURRENCY_CODE: The currency code (e.g., "USD") denoting the currency of the invoice amount. This joins to the Currencies table. Sample Data: USD
INVOICE_AMOUNT: The total monetary value of the invoice header. This usually equals the sum of the invoice lines and tax. Sample Data: 6.52, 6.87, 30.6
VENDOR_SITE_ID: A Foreign Key linking to AP_SUPPLIER_SITES_ALL. It specifies the specific location or address of the vendor where the invoice originated. Sample Data: 5208324
AMOUNT_PAID: The cumulative amount paid against this invoice to date. If this equals INVOICE_AMOUNT, the invoice is fully paid. Sample Data: 6.52, 6.87, 30.6
INVOICE_DATE: The date printed on the invoice provided by the supplier. This is used for aging and payment term calculations. Sample Data: 2025-01-31, 2025-01-22, 2025-01-16
SOURCE: A code indicating where the invoice originated (e.g., entered manually, imported via EDI, or from an external system). Sample Data: MORE4APPS
INVOICE_TYPE_LOOKUP_CODE: A classification code describing the nature of the invoice. This joins to a Lookup table (AP_INVOICE_TYPE). Sample Data: STANDARD
DESCRIPTION: Free text description of the invoice content or purpose. Sample Data: 2025-01-31_42516697, 2025-01-22_42454665, 2025-01-16_42423380
BATCH_ID: A Foreign Key identifying the batch group this invoice belongs to, used for batch processing or controls. Sample Data: 7379139
AMOUNT_APPLICABLE_TO_DISCOUNT: The portion of the invoice amount that is eligible for early payment discounts. Sample Data: 0, or any other numeric discount
TERMS_ID: A Foreign Key linking to the AP_TERMS table. It defines the payment schedule (e.g., "Net 30") applied to this invoice. Sample Data: 10032
TERMS_DATE: The baseline date from which payment terms are calculated. Sample Data: ########, date format
PAY_GROUP_LOOKUP_CODE: A grouping code used to categorize invoices for payment runs (e.g., separating employee expenses from trade vendors). Sample Data: GENERAL
ACCTS_PAY_CODE_COMBINATION_ID: A Foreign Key to the General Ledger (GL) Code Combinations table. This represents the Liability Account credited when the invoice is posted. Sample Data: 6615327
PAYMENT_STATUS_FLAG: A flag indicating the payment state: 'Y' (Fully Paid), 'N' (Not Paid), or 'P' (Partially Paid). Sample Data: Y, N
CREATION_DATE: An audit timestamp indicating when this record was first created in the system. Sample Data: ########, date format
CREATED_BY: An audit Foreign Key linking to the Users table, identifying the user who entered the invoice. Sample Data: 149189
PO_HEADER_ID: A Foreign Key linking to PO_HEADERS_ALL. If populated, this links the invoice to a specific Purchase Order. Sample Data: N/A, numeric ID
INVOICE_RECEIVED_DATE: The date the invoice was physically received by the accounts payable department. Sample Data: ######## date format
ATTRIBUTE3: A descriptive flexfield used to store custom, client-specific data. Sample Data: 5375, 5384, 5431
ATTRIBUTE4: A descriptive flexfield used to store custom, client-specific data. Sample Data: N/A
ATTRIBUTE5: A descriptive flexfield used to store custom, client-specific data. Sample Data: PA
ATTRIBUTE6: A descriptive flexfield used to store custom, client-specific data. Sample Data: BSWAMINATHA
CANCELLED_DATE: The date the invoice was cancelled. If NULL, the invoice is active. Sample Data: N/A, date format
CANCELLED_BY: A Foreign Key linking to the Users table, identifying who cancelled the invoice. Sample Data: N/A, given the userID
CANCELLED_AMOUNT: The amount of the invoice that was cancelled. Sample Data: N/A, any numeric amount when applicable
ORG_ID: A Foreign Key identifying the Operating Unit (OU) to which this invoice belongs. This is crucial for Multi-Org access control. Sample Data: 0, other numeric ID
GL_DATE: The accounting date used to post the liability to the General Ledger. Sample Data: ######## date format
TOTAL_TAX_AMOUNT: The total amount of tax calculated or entered for this invoice. Sample Data: 6.52, 6.87, 30.6
PAYMENT_METHOD_CODE: The method by which the invoice is to be paid (e.g., Check, Electronic, Wire). Sample Data: EFT
DELIVERY_CHANNEL_CODE: Additional details regarding the payment delivery method. Sample Data: Do not route
PARTY_ID: A Foreign Key to the Trading Community Architecture (TCA) HZ_PARTIES table. This links the invoice to the party registry. Sample Data: 9615646
PARTY_SITE_ID: A Foreign Key to the TCA HZ_PARTY_SITES table. This links the invoice to a specific party address. Sample Data: 7414962
________________________________________
Join to other tables with these considerations in mind:
Supplier Identification (VENDOR_ID): Always join to AP_SUPPLIERS using VENDOR_ID. Do not rely on VENDOR_NAME or SEGMENT1 (Supplier Number) for joins, as these can change. The VENDOR_ID is the immutable link between the invoice and the supplier master data.
Location Specifics (VENDOR_SITE_ID): Use VENDOR_SITE_ID to join to AP_SUPPLIER_SITES_ALL. This ensures you are paying the correct address/branch of the supplier. A single supplier (Vendor ID) can have multiple sites (Site IDs), and payment terms may differ by site.
Purchase Order Linkage (PO_HEADER_ID): To match an invoice to a Purchase Order, use PO_HEADER_ID to join to PO_HEADERS_ALL. Note that not all invoices are PO-matched; if this column is NULL, it is a "Non-PO" invoice.
Payment Details (INVOICE_ID): To see how an invoice was paid, join INVOICE_ID to AP_INVOICE_PAYMENTS_ALL. This bridging table links the Invoice Header to the Check/Payment (AP_CHECKS_ALL) tables.
Invoice Lines (INVOICE_ID): The INVOICE_AMOUNT in this table is a header total. For line-level details (Item descriptions, specific tax lines, freight), join INVOICE_ID to the child table AP_INVOICE_LINES_ALL.
Lookup Validations: Columns ending in _LOOKUP_CODE (e.g., INVOICE_TYPE_LOOKUP_CODE, SOURCE, PAYMENT_METHOD_CODE) should be joined to AP_LOOKUP_CODES or FND_LOOKUP_VALUES to retrieve the user-friendly meaning (Meaning/Description) rather than displaying the raw code.
Multi-Org Security (ORG_ID): This table is partitioned by Operating Unit. When joining to other transactional tables (like POs or Payments), ensure you include ORG_ID in your join conditions or filter criteria to prevent cross-organization data leakage in reports.


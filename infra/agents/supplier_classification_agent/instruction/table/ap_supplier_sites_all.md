Table Description
Table Name: ap_supplier_sites_all
Record Count: 3,100
Complete Description:
This table stores the specific location details and business rules for each supplier. While the parent table (AP_SUPPLIERS) defines who the supplier is, this table defines where the business takes place. It contains address details, site-specific settings (such as "Pay To" or "Ship To" designations), financial defaults (tax codes, liability accounts, payment terms), and operating unit assignments (ORG_ID). A single supplier can have multiple sites (e.g., "HEADQUARTERS", "ATLANTA_OFFICE"), allowing the business to send purchase orders to one location and payments to another.
Natural representation description:
This table acts as the "Address Book and Policy Center" for suppliers. It establishes the specific points of contact for ordering and payment. It answers questions like: "Where do we mail the check?", "Is this specific office allowed to receive Purchase Orders?", and "Which General Ledger account tracks liabilities for this specific office?"
________________________________________
Column Description Schema
VENDOR_SITE_ID: This is the Primary Key for the table. It is the unique system-generated identifier for the specific supplier site. Transactional tables (Invoices, POs) link to this ID to pinpoint the exact location used. Sample Data: 11234, 99821
LAST_UPDATE_DATE: An audit timestamp indicating when this record was last modified. Sample Data: 22-AUG-2015 09:40:41, 10-JAN-2017 10:58:02
LAST_UPDATED_BY: An audit Foreign Key linking to the Users table, identifying the user who performed the last modification. Sample Data: 61123
VENDOR_ID: A Foreign Key linking to the parent table AP_SUPPLIERS. It identifies which supplier owns this site. Sample Data: 104903, 104903, 61123
VENDOR_SITE_CODE: The user-defined name for the site. This is how human operators distinguish between addresses (e.g., "OFFICE", "REMIT-TO"). Sample Data: An internal code for displaying vendor site
CREATION_DATE: An audit timestamp indicating when this record was first created. Sample Data: 29-DEC-2006 06:51:15
CREATED_BY: An audit Foreign Key linking to the Users table, identifying the user who created the record. Sample Data: 5362, 61123
PURCHASING_SITE_FLAG: A boolean indicator (Y/N). If 'Y', Purchase Orders can be issued to this site. Sample Data: Y, N
RFQ_ONLY_SITE_FLAG: A boolean indicator (Y/N). If 'Y', this site is only used for Requests for Quotation and cannot receive actual POs. Sample Data: N, Y
PAY_SITE_FLAG: A boolean indicator (Y/N). If 'Y', the system allows invoices to be paid to this site address. Sample Data: Y, N
ADDRESS_LINE1: The first line of the physical or mailing address. Sample Data: Recipient Name, 123 Main St Apt 4B, Anytown, CA 90210
ADDRESS_LINE2: The second line of the address. Sample Data: N/A, Recipient Name, 123 Main St Apt 4B, Anytown, CA 90210
ADDRESS_LINE3: The third line of the address. Sample Data: Recipient Name, 123 Main St Apt 4B, Anytown, CA 90210
CITY: The city name for the site address. Sample Data: Salt Lake City, Rochester
STATE: The state or region code. Sample Data: California, Michigan
ZIP: The postal code for the address. Sample Data: 74843, 98204
PROVINCE: The province (typically for non-US addresses). Sample Data: N/A
COUNTRY: The country code for the address. Sample Data: N/A, US, MX, GER
AREA_CODE: The phone number area code. Sample Data: N/A, 770, 212
PHONE: The phone number associated with this site. Sample Data: 45612456,23456724
CUSTOMER_NUM: A reference number used to identify the buying organization within the supplier's system. Sample Data: 101, 3273
SHIP_TO_LOCATION_ID: A Foreign Key to HR_LOCATIONS. It defines the default location where goods ordered from this supplier site should be delivered. Sample Data: 22-AUG-2015 00:00:00, 10-JAN-2017 00:00:00
BILL_TO_LOCATION_ID: A Foreign Key to HR_LOCATIONS. It defines the default location where invoices from this supplier site should be sent. Sample Data: N/A
INACTIVE_DATE: The date this site becomes inactive. If NULL, the site is active. Sample Data: N/A, 10-JAN-2017 00:00:00
FAX: The fax number for this site. Sample Data: CHECK (Data appears displaced in sample, usually numeric/text), N/A, 124556346
FAX_AREA_CODE: The area code for the fax number. Sample Data: 6615327, 6615249
PAYMENT_METHOD_LOOKUP_CODE: A code indicating the default method of payment (e.g., CHECK, ELECTRONIC, WIRE). Sample Data: CHECK, N/A
ACCTS_PAY_CODE_COMBINATION_ID: A Foreign Key to the General Ledger (GL_CODE_COMBINATIONS). This represents the Liability Account credited when an invoice is entered for this site. Sample Data: 6615327, N/A
PREPAY_CODE_COMBINATION_ID: A Foreign Key to the General Ledger representing the Prepayment account. Sample Data: 6615249, N/A
PAY_GROUP_LOOKUP_CODE: A code used to group suppliers for payment runs (e.g., "EMPLOYEE", "DOMESTIC"). Sample Data: N/A
PAYMENT_PRIORITY: A numerical value (1-99) determining the priority of payment during batch processing. Sample Data: 30, 50
TERMS_ID: A Foreign Key to the AP_TERMS table. Defines the payment terms (e.g., Net 30, Immediate) for invoices received at this site. Sample Data: 10032
PAY_DATE_BASIS_LOOKUP_CODE: Determines which date triggers the payment term clock (e.g., Invoice Date or Goods Received Date). Sample Data: DUE
ALWAYS_TAKE_DISC_FLAG: A boolean flag (Y/N). If 'Y', the system will always take the early payment discount regardless of payment date. Sample Data: N, Y
INVOICE_CURRENCY_CODE: The default currency for invoices entered for this site. Sample Data: USD
PAYMENT_CURRENCY_CODE: The default currency for payments made to this site. Sample Data: USD
HOLD_ALL_PAYMENTS_FLAG: A boolean control flag (Y/N). If 'Y', all payments to this specific site are suspended. Sample Data: N, Y
HOLD_FUTURE_PAYMENTS_FLAG: A boolean control flag (Y/N). If 'Y', prevents unpaid invoices from being selected in future payment runs. Sample Data: N, Y
HOLD_REASON: A text description explaining why a hold was placed on the site. Sample Data: N/A
AP_TAX_ROUNDING_RULE: Defines how tax amounts should be rounded for this site. Sample Data: N, Y
AMOUNT_INCLUDES_TAX_FLAG: A boolean flag (Y/N). If 'Y', invoice lines entered for this site default to inclusive of tax. Sample Data: N, Y
EXCLUSIVE_PAYMENT_FLAG: A boolean flag (Y/N). If 'Y', payments to this site are generated on a separate payment document (check) from other sites/invoices. Sample Data: Y, N/A, N
TAX_REPORTING_SITE_FLAG: A boolean flag (Y/N). If 'Y', this site is the primary address used for tax reporting (1099) purposes. Sample Data: N, Y
ORG_ID: Crucial Attribute. The Foreign Key to HR_OPERATING_UNITS. It partitions the data, ensuring this site is only visible and usable by a specific business unit within the organization. Sample Data: 0 (likely masked or default), 101, 3273
PRIMARY_PAY_SITE_FLAG: A boolean flag (Y/N). Indicates if this is the preferred site for making payments for this vendor. Sample Data: N/A, Y, N
LOCATION_ID: A Foreign Key to HR_LOCATIONS, often used for internal sites or integration mapping. Sample Data: 208696, 208692, 458855
PARTY_SITE_ID: A Foreign Key to the TCA (Trading Community Architecture) table HZ_PARTY_SITES. Links this ERP vendor site to the centralized address model. Sample Data: 190548, 190551, 2464373
LEGAL_BUSINESS_NAME: The legal name of the business operating at this site, often used if different from the parent vendor name. Sample Data: Innovix Solutions, Neon Harbor, Medical Insurance.
________________________________________
Join to other tables with these considerations in mind:
Parent Join (VENDOR_ID): Join to the parent table AP_SUPPLIERS using VENDOR_ID. This is a mandatory One-to-Many relationship (One Supplier has Many Sites).
Operating Unit Partitioning (ORG_ID): unlike AP_SUPPLIERS (which is global), AP_SUPPLIER_SITES_ALL is partitioned by Operating Unit. When joining, you must filter by ORG_ID or join to the user's security profile. Failing to do so will result in duplicate rows if the same Vendor exists in multiple Operating Units (e.g., US Ops and UK Ops).
Financial Defaults (ACCTS_PAY...): The ACCTS_PAY_CODE_COMBINATION_ID determines the GL liability account. Join this to GL_CODE_COMBINATIONS to get the readable account string (e.g., "01-000-2000-000"). If this is NULL on the site, the system typically looks at the Financial Options system setup, not the parent Vendor.
Address Master (PARTY_SITE_ID): Modern Oracle versions use TCA (Trading Community Architecture). Join PARTY_SITE_ID to HZ_PARTY_SITES and HZ_LOCATIONS if you need standardized, deep address validation or geocodes that aren't stored in the flat ADDRESS_LINE columns of this table.
Site Usage Flags: When querying for a "Remit To" address, filter for PAY_SITE_FLAG = 'Y'. When querying for an ordering address, filter for PURCHASING_SITE_FLAG = 'Y'. A site can be both, but using the wrong one can cause transaction validation errors.
Payment Terms (TERMS_ID): Similar to the parent table, join to AP_TERMS. Note that the Site level terms override the Supplier level terms. If TERMS_ID is present here, it takes precedence over the AP_SUPPLIERS.TERMS_ID.


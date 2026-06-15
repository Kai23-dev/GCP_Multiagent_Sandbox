Table Description
Table Name: AP_SUPPLIER_SITES_ALL
Record Count: Small
Complete Description:
This table serves as the master repository for all supplier site locations, representing the specific addresses, locations, and operational settings for each vendor. Each record represents a unique vendor site with its own address, payment preferences, purchasing capabilities, and site-specific configurations. This table is essential for multi-site vendor management, payment processing, purchasing operations, tax reporting, and location-based analysis. It provides the granular detail needed to manage vendors with multiple locations, each with different operational characteristics.
________________________________________

Column Description Schema
vendor_site_id: This is the Primary Key for the table. It is the unique system-generated identifier for each supplier site. Sample Data: 138773, 165536, 217894
vendor_id: Foreign Key to AP_SUPPLIERS table. Links this site to the parent supplier record. Sample Data: 100657, 102719, 103102
vendor_site_code: The unique code identifying this specific supplier site. Sample Data: RANCHOCUCA(EXP), HOUSTON1(EXP), VEROBEACH2(EXP)
party_site_id: Foreign Key to HZ_PARTY_SITES table. The TCA party site identifier for this location. Sample Data: 141942, 166452, 193138
is_purchasing_site: Boolean flag (Y/N) indicating if this site can be used for purchasing. Sample Data: Y
is_rfq_only_site: Boolean flag (Y/N) indicating if this site is used only for RFQs. Sample Data: N
is_pay_site: Boolean flag (Y/N) indicating if payments can be made to this site. Sample Data: Y
is_primary_pay_site: Boolean flag (Y/N) indicating if this is the primary payment site for the vendor. Sample Data: N/A
is_tax_reporting_site: Boolean flag (Y/N) indicating if this site is used for tax reporting. Sample Data: N
address_line1: The first line of the site address. Sample Data: 1234 MAIN STREET, 4567 BUSINESS PARKWAY, 7890 COMMERCIAL BLVD
address_line2: The second line of the site address. Sample Data: SUITE 100, BUILDING 2, FLOOR 3
address_line3: The third line of the site address. Sample Data: N/A
city: The city for this site address. Sample Data: RANCHO CUCAMONGA, HOUSTON, VERO BEACH
state: The state or province for this site address. Sample Data: CA, TX, FL
zip: The postal code for this site address. Sample Data: 91730, 77001, 32960
province: The province for international addresses. Sample Data: N/A
country: The country code for this site address. Sample Data: US
ship_to_location_id: Foreign Key to HR_LOCATIONS table. The default ship-to location for this site. Sample Data: 101
bill_to_location_id: Foreign Key to HR_LOCATIONS table. The default bill-to location for this site. Sample Data: 101, 212130, 212128
location_id: Foreign Key to HR_LOCATIONS table. The internal location identifier. Sample Data: 162442, 186099, 212130
payment_method: The default payment method for this site (e.g., CHECK, EFT, WIRE). Sample Data: CHECK
pay_group: The payment group for this site used in payment processing. Sample Data: N/A
payment_priority: The payment priority level for this site (lower numbers = higher priority). Sample Data: 50, 30
terms_id: Foreign Key to AP_TERMS table. The payment terms for this site. Sample Data: 10029, 10032
pay_date_basis: The basis for payment date calculation (e.g., DUE, RECEIPT). Sample Data: DUE
always_take_discount: Boolean flag (Y/N) indicating if discounts are always taken. Sample Data: N
is_exclusive_payment: Boolean flag (Y/N) indicating if payments are exclusive to this site. Sample Data: N, Y
invoice_currency_code: The default currency for invoices from this site. Sample Data: USD
payment_currency_code: The default currency for payments to this site. Sample Data: USD
hold_all_payments: Boolean flag (Y/N) indicating if all payments to this site are held. Sample Data: N
hold_future_payments: Boolean flag (Y/N) indicating if future payments to this site are held. Sample Data: N
hold_reason: The reason for payment holds, if applicable. Sample Data: N/A
accts_pay_code_combination_id: Foreign Key to GL_CODE_COMBINATIONS table. The AP liability account for this site. Sample Data: 6615327
customer_number: The customer number if this vendor is also a customer. Sample Data: N/A
org_id: Foreign Key to HR_OPERATING_UNITS table. The operating unit for this site. Sample Data: 0
legal_business_name: The legal business name for this site. Sample Data: UNITED SECURITY SYSTEMS INC, HOUSTON SECURITY MD, INDIAN RIVER COUNTY TAX COLLECTOR
inactive_date: The date when this site became inactive. Sample Data: N/A
source_system: The source system from which the site data originated. Sample Data: ORACLE
created_at: The timestamp when this site record was created. Sample Data: 2026-02-10 06:18:14.329320 UTC
updated_at: The timestamp when this site record was last updated. Sample Data: 2026-02-10 06:18:17.959074 UTC

Join to other tables with these considerations in mind:
Po Headers All Integration: Use vendor_site_id to join to PO_HEADERS_ALL.vendor_site_id for complete transaction analysis and business context.
Po Requisition Lines All Integration: Use vendor_site_id to join to PO_REQUISITION_LINES_ALL.vendor_site_id for complete transaction analysis and business context.
Supplier Integration: Use vendor_id to join to AP_SUPPLIERS for complete supplier master information and corporate details.
Invoice Integration: Use vendor_site_id to join to AP_INVOICES_ALL for site-specific invoice analysis and payment patterns.
Payment Integration: Use vendor_site_id to join to AP_CHECKS_ALL for site-specific payment analysis and cash flow management.
PO Integration: Use vendor_site_id to join to PO_HEADERS_ALL for site-specific order analysis and delivery performance.
Requisition Integration: Use vendor_site_id to join to PO_REQUISITION_LINES_ALL for site-specific purchase request analysis.
Table Description
Table Name: AP_SUPPLIERS
Record Count: Small
Complete Description:
This table serves as the master repository for all external suppliers (vendors) with whom the business conducts trade. It contains the legal entity details, unique system identifiers, payment preferences, tax compliance status, and operational states (active/inactive or on hold). Use this table to resolve Vendor IDs to names, look up vendor numbers, and validate if a supplier is eligible to receive payments or purchase orders. This table is the foundation for all vendor-related transactions in the procurement and accounts payable systems.
________________________________________

Column Description Schema
vendor_id: This is the Primary Key for the table. It is the unique system-generated identifier for the supplier. Other tables use this ID to join to this record. Sample Data: 15490, 9348030, 7743055
vendor_number: The public vendor number used by human operators to search for suppliers. This is a unique business key. Sample Data: 15490, 422497, 376894
supplier_name: The full legal name of the supplier entity or individual. Sample Data: MEDICAL SUPPLIES INC, TECHNOLOGY SOLUTIONS LLC, U S DISTRICT CLERK OF THE COURT
supplier_name_normalized: The normalized version of the supplier name for consistent searching and matching. Sample Data: MEDICAL SUPPLIES INC, TECHNOLOGY SOLUTIONS LLC, U S DISTRICT CLERK OF THE COURT
vendor_type: A classification code describing the type of vendor (e.g., VENDOR, EMPLOYEE, CONTRACTOR). Sample Data: VENDOR
organization_type: A code defining the legal structure of the supplier (e.g., CORPORATION, INDIVIDUAL, GOVERNMENT AGENCY). Sample Data: CORPORATION, GOVERNMENT AGENCY
enabled_flag: A boolean indicator (Y/N) specifying if the vendor is currently enabled for use in the system. Sample Data: Y
is_active: A boolean indicator (true/false) for the current active status of the vendor. Sample Data: false
start_date_active: The date when the vendor relationship became active. Sample Data: 2020-01-15, 2018-03-10, 2015-06-20
end_date_active: The date when the vendor relationship ceased. If this is NULL, the vendor is still considered active. Sample Data: N/A
hold_flag: A boolean flag (Y/N) indicating if the vendor is currently on hold. Sample Data: N
hold_reason: The reason why the vendor is on hold, if applicable. Sample Data: N/A
hold_all_payments_flag: A boolean flag (Y/N) indicating if all payments to this vendor are held. Sample Data: N
hold_future_payments_flag: A boolean flag (Y/N) indicating if future payments to this vendor are held. Sample Data: N
payment_terms_id: Foreign Key to AP_TERMS table. The payment terms identifier for this vendor. Sample Data: 10032
payment_priority: The payment priority level for this vendor (lower numbers = higher priority). Sample Data: 10, 20, 25
invoice_currency_code: The default currency code for invoices from this vendor. Sample Data: USD
payment_currency_code: The default currency code for payments to this vendor. Sample Data: USD
num_1099: The Tax Identification Number (TIN) or Social Security Number used for tax reporting. Sample Data: 91-2154439, 95-3372911
type_1099: The specific tax form type required for this vendor (e.g., MISC, INT). Sample Data: MISC6
tax_reporting_name: The specific name to be printed on government tax documents if it differs from supplier_name. Sample Data: MEDICAL SUPPLIES INC
source_system: The source system from which the supplier data originated. Sample Data: ORACLE
created_at: The timestamp when this supplier record was created. Sample Data: 2026-02-10 06:18:14.423229 UTC
updated_at: The timestamp when this supplier record was last updated. Sample Data: 2026-02-10 06:18:17.858638 UTC

Join to other tables with these considerations in mind:
Po Headers All Integration: Use vendor_id to join to PO_HEADERS_ALL.vendor_id for complete transaction analysis and business context.
Po Requisition Lines All Integration: Use vendor_id to join to PO_REQUISITION_LINES_ALL.vendor_id for complete transaction analysis and business context.
Xxc Gl Summary Integration: Use vendor_id to join to XXC_GL_SUMMARY.vendor_id for complete transaction analysis and business context.
Site Integration: Use vendor_id to join to AP_SUPPLIER_SITES_ALL for complete supplier location and contact information.
Invoice Integration: Use vendor_id to join to AP_INVOICES_ALL for invoice history, payment patterns, and spending analysis.
Payment Integration: Use vendor_id to join to AP_CHECKS_ALL for payment history, clearing patterns, and cash flow analysis.
PO Integration: Use vendor_id to join to PO_HEADERS_ALL for order history, contract compliance, and supplier performance.
GL Integration: Use vendor_id to join to XXC_GL_SUMMARY for financial transaction analysis and spend validation.
Requisition Integration: Use vendor_id to join to PO_REQUISITION_LINES_ALL for purchase request patterns and demand analysis.
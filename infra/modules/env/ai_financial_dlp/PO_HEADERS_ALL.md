Table Description
Table Name: PO_HEADERS_ALL
Record Count: Small
Complete Description:
This table serves as the master repository for purchase order headers, representing the main information for each purchase order in the Oracle E-Business Suite. Each record represents a complete purchase order with vendor information, payment terms, delivery details, and approval status. This table is essential for procurement management, supplier relationship management, financial tracking, approval workflow monitoring, and maintaining the complete lifecycle of purchase orders from creation to completion. The moderate record count indicates comprehensive purchase order management across the organization's procurement operations.
________________________________________

Column Description Schema
po_header_id: This is the Primary Key for the table. It is the unique system-generated identifier for each purchase order. Sample Data: 9323833, 9319896, 9292968
vendor_id: Foreign Key to AP_SUPPLIERS table. The unique identifier for the vendor. Sample Data: 7747220
vendor_site_id: Foreign Key to AP_SUPPLIER_SITES_ALL table. The unique identifier for the vendor site. Sample Data: 4807014
buyer_id: Foreign Key to employee/user tables. The unique identifier for the buyer who created the PO. Sample Data: 244
po_number: The purchase order number used for business reference. Sample Data: 170903, 170692, 169142
po_type: The type of purchase order (e.g., STANDARD, BLANKET, CONTRACT). Sample Data: STANDARD
ship_to_location_id: Foreign Key to HR_LOCATIONS table. The location where items will be shipped. Sample Data: 101
bill_to_location_id: Foreign Key to HR_LOCATIONS table. The location for billing purposes. Sample Data: 3273
payment_terms_id: Foreign Key to AP_TERMS table. The payment terms for this purchase order. Sample Data: 10029
currency_code: The currency code for the purchase order. Sample Data: USD
exchange_rate: The exchange rate if the currency is different from the functional currency. Sample Data: 1.0
blanket_total_amount: The total amount for blanket purchase orders. Sample Data: 0
amount_limit: The amount limit for the purchase order. Sample Data: 0
min_release_amount: The minimum release amount for blanket purchase orders. Sample Data: 0
start_date: The start date for the purchase order validity. Sample Data: 2025-01-01
end_date: The end date for the purchase order validity. Sample Data: 2025-12-31
approved_date: The date when the purchase order was approved. Sample Data: 2025-01-15
authorization_status: The current authorization status of the purchase order. Sample Data: INCOMPLETE
is_cancelled: Boolean flag (Y/N) indicating if the purchase order is cancelled. Sample Data: N
org_id: Foreign Key to HR_OPERATING_UNITS table. The operating unit for this purchase order. Sample Data: 0
source_system: The source system that created or manages this purchase order. Sample Data: ORACLE
created_at: The timestamp when this purchase order record was created. Sample Data: 2026-02-10 06:18:14.323816 UTC
updated_at: The timestamp when this purchase order record was last updated. Sample Data: 2026-02-10 06:18:18.425778 UTC

Join to other tables with these considerations in mind:
Primary Ap Suppliers Integration: Always join vendor_id to AP_SUPPLIERS.vendor_id to get complete Ap Suppliers information and establish the core relationship.
Primary Ap Supplier Sites All Integration: Always join vendor_site_id to AP_SUPPLIER_SITES_ALL.vendor_site_id to get complete Ap Supplier Sites All information and establish the core relationship.
Po Distributions All Integration: Use po_header_id to join to PO_DISTRIBUTIONS_ALL.po_header_id for complete transaction analysis and business context.
Po Lines All Integration: Use po_header_id to join to PO_LINES_ALL.po_header_id for complete transaction analysis and business context.
Vendor Integration: Use vendor_id to join to AP_SUPPLIERS for complete supplier information, contract details, and performance analysis.
Site Integration: Use vendor_site_id to join to AP_SUPPLIER_SITES_ALL for location-specific supplier information and delivery analysis.
Line Integration: Use po_header_id to join to PO_LINES_ALL for complete order details, line items, and specification information.
Distribution Integration: Use po_header_id to join to PO_DISTRIBUTIONS_ALL for accounting allocation and cost center analysis.
Financial Integration: Use order information to join with AP_INVOICES_ALL for order-to-invoice reconciliation and procurement cycle analysis.
Approval Integration: Use approval information to analyze procurement workflows and cycle time performance.
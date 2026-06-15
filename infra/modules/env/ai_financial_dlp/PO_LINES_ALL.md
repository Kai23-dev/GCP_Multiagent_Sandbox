Table Description
Table Name: PO_LINES_ALL
Record Count: Small
Complete Description:
This table serves as the master repository for purchase order line items, representing the detailed line information for each purchase order in the Oracle E-Business Suite. Each record represents a specific line item on a purchase order with product details, pricing information, quantities, and line status. This table is essential for detailed procurement analysis, product tracking, price management, inventory planning, and maintaining the complete breakdown of purchase order contents. The moderate record count indicates comprehensive line item tracking for purchase orders across the organization's procurement operations.
________________________________________

Column Description Schema
po_line_id: This is the Primary Key for the table. It is the unique system-generated identifier for each purchase order line. Sample Data: 10302048, 9978297, 10218577
po_header_id: Foreign Key to PO_HEADERS_ALL table. The unique identifier for the purchase order header. Sample Data: 9473835, 8950795, 9405908
item_id: Foreign Key to item master tables. The unique identifier for the item being purchased. Sample Data: N/A
category_id: Foreign Key to category tables. The unique identifier for the item category. Sample Data: 1403
line_number: The line number on the purchase order. Sample Data: 1
item_description: The detailed description of the item being purchased. Sample Data: CARBON BLOCK FILTER P/N: FE52000, HEADSETS, NEW PO IN CASE PARTS ARE NOT RETURNED WITHIN 30 DAYS
vendor_product_num: The vendor's product number or part number. Sample Data: FE52000, 108113, 2210-100
unit_price: The unit price for the item. Sample Data: 0
base_unit_price: The base unit price in functional currency. Sample Data: 0
list_price: The list price for the item. Sample Data: 0
unit_of_measure: The unit of measure for pricing and ordering. Sample Data: 12PACK
quantity: The quantity of items ordered. Sample Data: 8, 2, 1
quantity_committed: The quantity committed for this line. Sample Data: N/A
order_type: The type of order (e.g., QUANTITY, AMOUNT). Sample Data: QUANTITY
purchase_basis: The basis for purchase (e.g., GOODS, SERVICES). Sample Data: GOODS
matching_basis: The basis for matching (e.g., QUANTITY, AMOUNT). Sample Data: QUANTITY
allow_price_override: Boolean flag (Y/N) indicating if price can be overridden. Sample Data: N
closed_status: The closed status of the line item. Sample Data: N/A
expiration_date: The expiration date for the line item. Sample Data: N/A
source_system: The source system that created or manages this purchase order line. Sample Data: ORACLE
created_at: The timestamp when this purchase order line record was created. Sample Data: 2026-02-10 06:18:12.098185 UTC
updated_at: The timestamp when this purchase order line record was last updated. Sample Data: 2026-02-10 06:18:15.731122 UTC

Join to other tables with these considerations in mind:
Primary Po Headers All Integration: Always join po_header_id to PO_HEADERS_ALL.po_header_id to get complete Po Headers All information and establish the core relationship.
Po Distributions All Integration: Use po_line_id to join to PO_DISTRIBUTIONS_ALL.po_line_id for complete transaction analysis and business context.
Header Integration: Use po_header_id to join to PO_HEADERS_ALL for complete order information, vendor details, and approval status.
Distribution Integration: Use po_line_id to join to PO_DISTRIBUTIONS_ALL for accounting allocation and charge analysis.
Invoice Integration: Use po_line_id to join with AP_INVOICE_LINES_ALL for three-way matching and receipt validation.
Catalog Integration: Use item information to join with catalog systems for specification validation and price comparison.
Receiving Integration: Use line information to join with receiving systems for goods receipt validation and quantity reconciliation.
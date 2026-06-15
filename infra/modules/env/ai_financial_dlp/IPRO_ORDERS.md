Table Description
Table Name: IPRO_ORDERS
Record Count: Very Large
Complete Description:
This table serves as the master repository for all purchase orders processed through the iProcurement system, representing comprehensive procurement transactions for healthcare and dialysis operations. Each record represents a specific purchase order line item with detailed vendor information, facility details, product specifications, pricing, and order status. This table is essential for procurement analysis, supplier performance tracking, spend management, inventory planning, and operational reporting for healthcare facilities. The extremely high record count indicates comprehensive procurement coverage across the organization's healthcare operations, providing complete visibility into the procurement lifecycle from requisition to order fulfillment.
________________________________________

Column Description Schema
po_number: This is the Primary Key for the table. It is the unique purchase order number used to identify each order. Sample Data: 6089-24251, 6089-24016, 95080-1113486
vendor_id: Foreign Key to supplier master tables. The unique identifier for the vendor receiving this order. Sample Data: 2855, 6406
requisition_id: Foreign Key to requisition tables. The unique identifier for the requisition that generated this order. Sample Data: 16756768, 16589317, 16994068
line_number: The line number on the purchase order. Sample Data: 1, 3, 5
davita_item_number: Foreign Key to IPRO_CATALOG. The Davita item number from the catalog. Sample Data: 1045199, 1045201, 1046400
product_number: The product number or manufacturer part number. Sample Data: 1737-3R, 2640-00, 08-3301-2
facility_id: The unique identifier for the facility where the order is being delivered. Sample Data: 05018, 03671, 11450
facility_name: The name of the facility where the order is being delivered. Sample Data: BARRINGTON CREEK DIALYSIS, CHARLOTTESVILLE NORTH DIALYSIS, PLATTE VALLEY DIALYSIS
city: The city where the facility is located. Sample Data: CHICAGO, CHARLOTTESVILLE, BRIGHTON
state: The state where the facility is located. Sample Data: IL, VA, CO
phone: The phone number for the facility. Sample Data: 773-555-1234, 434-555-5678, 303-555-9012
po_creation_date: The timestamp when the purchase order was created. Sample Data: 2025-07-16 19:16:01.000000 UTC, 2025-05-21 12:55:59.000000 UTC
order_date: The date when the order was placed. Sample Data: 2025-07-16, 2025-05-21, 2025-10-01
need_by_date: The date when the items are needed by. Sample Data: 2025-07-21, 2025-05-26, 2025-10-06
item_description: The detailed description of the item being ordered. Sample Data: BINDER, PATIENT CHART 3-RING 3" SIDE OPEN BLUE, DIVIDER
product: The product name or category. Sample Data: BINDERS, BINDER DIVIDERS, LIQUID ACID CONCENTRATE JUG
manufacturer: The manufacturer of the product. Sample Data: CARSTENS, FMC
product_category: The high-level product category. Sample Data: BINDER, DIVIDER, ACID CONCENTRATE
category1: The first level category classification. Sample Data: Office, Med Supplies
category2: The second level category classification. Sample Data: Binders & Binder Accessories, Dialysate
category3: The third level category classification. Sample Data: Binders, Acid Con 3K
vendor_name: The name of the vendor receiving this order. Sample Data: CARSTENS CORPORATION, FRESENIUS USA INC
vendor_name_normalized: The normalized version of the vendor name for consistent searching and matching. Sample Data: CARSTENS CORPORATION, FRESENIUS USA INC
ordered_by: The name of the person who placed the order. Sample Data: JOHN SMITH, MARY JOHNSON, ROBERT BROWN
unit_price: The unit price of the item. Sample Data: 15.89, 12.15, 13.46
quantity_ordered: The quantity of items ordered. Sample Data: 11, 15, 9
quantity_received: The quantity of items actually received. Sample Data: 11, 15, 9
amount_ordered: The total amount ordered (unit_price × quantity_ordered). Sample Data: 174.79, 182.25, 201.9
amount_received: The total amount received (unit_price × quantity_received). Sample Data: 174.79, 182.25, 201.9
unit_of_measure: The unit of measure for the order. Sample Data: EACH, CASE
expense_account: The expense account for financial tracking. Sample Data: 7600, 6604
charge_to: The charge to location or department. Sample Data: 05018, 03671, 11450
sub_account: The sub-account for detailed expense tracking. Sample Data: 300
eaches: The number of individual units per case. Sample Data: 1, 4
eaches_uom: The unit of measure for individual units. Sample Data: EACH, GALLONS
quantity_eaches: The total quantity of individual units. Sample Data: 11, 15, 60
service_type: The type of service (e.g., In-Center Hemo). Sample Data: In-Center Hemo
source: The source of the order (e.g., OMG for ordering management group). Sample Data: NON-OMG, OMG
closed_code: The closure status of the order. Sample Data: CLOSED
urgent_flag: Boolean flag (Y/N) indicating if the order is urgent. Sample Data: N
year: The year when the order was placed. Sample Data: 2025
month: The month when the order was placed. Sample Data: 7, 5, 10
year_month: The year-month combination for reporting. Sample Data: 2025/07, 2025/05, 2025/10
source_system: The source system that created or manages this order. Sample Data: IPRO
created_at: The timestamp when this order record was created. Sample Data: 2026-02-10 06:18:14.298154 UTC
updated_at: The timestamp when this order record was last updated. Sample Data: 2026-02-10 06:18:21.068225 UTC

Join to other tables with these considerations in mind:
Primary Ipro Catalog Integration: Always join davita_item_number to IPRO_CATALOG.davita_item_number to get complete Ipro Catalog information and establish the core relationship.
Catalog Integration: Use davita_item_number to join to IPRO_CATALOG for complete product information, pricing details, and specification validation.
Vendor Integration: Use vendor_id and vendor_name to join to AP_SUPPLIERS for complete supplier information, performance metrics, and contract details.
Facility Integration: Use facility_id and facility_name to join with facility tables for location-based analysis, regional reporting, and operational efficiency studies.
Financial Integration: Use invoice_number to join with AP_INVOICES_ALL for order-to-invoice reconciliation and procurement cycle analysis.
GL Integration: Use expense_account to join with XXC_GL_SUMMARY.account for actual spend analysis and budget validation.
Time Series Analysis: Use order_date, need_by_date, and year_month for demand forecasting, seasonal analysis, and procurement planning.
Category Analysis: Use category1, category2, and category3 for hierarchical spend analysis and category management optimization.
Performance Analysis: Combine amount_ordered, amount_received, and quantity data for supplier performance and order fulfillment analysis.
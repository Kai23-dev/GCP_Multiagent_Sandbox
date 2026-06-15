Table Description
Table Name: IPRO_ORDERS
Record Count: 4,406,124
Complete Description:
This table serves as the master repository for all purchase orders processed through the iProcurement system, representing comprehensive procurement transactions for healthcare and dialysis operations. Each record represents a specific purchase order line item with detailed vendor information, facility details, product specifications, pricing, and order status. This table is essential for procurement analysis, supplier performance tracking, spend management, inventory planning, and operational reporting for healthcare facilities. The extremely high record count indicates comprehensive procurement coverage across the organization's healthcare operations, providing complete visibility into the procurement lifecycle from requisition to order fulfillment.
Natural representation description:
This table acts as the complete purchase order repository for the iProcurement system, containing every healthcare-related purchase order line with its associated vendor details, facility information, product specifications, and order status. It provides the foundation for comprehensive healthcare procurement analysis, supplier management, inventory planning, and operational reporting across all dialysis and medical facilities.
________________________________________
Column Description Schema
po_number: This is the Primary Key for the table. It is the unique purchase order number used to identify each order. Sample Data: 6089-24251, 6089-24016, 95080-1113486, 95080-1067427, 95080-1029752
vendor_id: Foreign Key to supplier master tables. The unique identifier for the vendor receiving this order. Sample Data: 2855, 2855, 6406, 6406, 6406
requisition_id: Foreign Key to requisition tables. The unique identifier for the requisition that generated this order. Sample Data: 16756768, 16589317, 16994068, 16664792, 16396523
line_number: The line number on the purchase order. Sample Data: 1, 3, 3, 5, 4
davita_item_number: Foreign Key to IPRO_CATALOG. The Davita item number from the catalog. Sample Data: 1045199, 1045201, 1046400, 1046400, 1046400
product_number: The product number or manufacturer part number. Sample Data: 1737-3R, 2640-00, 08-3301-2, 08-3301-2, 08-3301-2
facility_id: The unique identifier for the facility where the order is being delivered. Sample Data: 05018, 03671, 11450, 04367, 03653
facility_name: The name of the facility where the order is being delivered. Sample Data: BARRINGTON CREEK DIALYSIS, CHARLOTTESVILLE NORTH DIALYSIS, PLATTE VALLEY DIALYSIS, DENVER CENTRAL DIALYSIS, OSHKOSH WEST DIALYSIS
city: The city where the facility is located. Sample Data: CHICAGO, CHARLOTTESVILLE, BRIGHTON, DENVER, OSHKOSH
state: The state where the facility is located. Sample Data: IL, VA, CO, CO, WI
phone: The phone number for the facility. Sample Data: 773-555-1234, 434-555-5678, 303-555-9012, 303-555-3456, 920-555-7890
po_creation_date: The timestamp when the purchase order was created. Sample Data: 2025-07-16 19:16:01.000000 UTC, 2025-05-21 12:55:59.000000 UTC
order_date: The date when the order was placed. Sample Data: 2025-07-16, 2025-05-21, 2025-10-01, 2025-06-16, 2025-02-24
need_by_date: The date when the items are needed by. Sample Data: 2025-07-21, 2025-05-26, 2025-10-06, 2025-06-21, 2025-03-01
item_description: The detailed description of the item being ordered. Sample Data: BINDER, PATIENT CHART 3-RING 3" SIDE OPEN BLUE, DIVIDER, BINDER 19-TAB COLOR CODE SET, ACID CONCENTRATE, LIQUID 45X 3K 3Ca 1Mg 100 DEXTROSE GALLON, ACID CONCENTRATE, LIQUID 45X 3K 3Ca 1Mg 100 DEXTROSE GALLON
product: The product name or category. Sample Data: BINDERS, BINDER DIVIDERS, LIQUID ACID CONCENTRATE JUG, LIQUID ACID CONCENTRATE JUG, LIQUID ACID CONCENTRATE JUG
manufacturer: The manufacturer of the product. Sample Data: CARSTENS, CARSTENS, FMC, FMC, FMC
product_category: The high-level product category. Sample Data: BINDER, DIVIDER, ACID CONCENTRATE, ACID CONCENTRATE, ACID CONCENTRATE
category1: The first level category classification. Sample Data: Office, Office, Med Supplies, Med Supplies, Med Supplies
category2: The second level category classification. Sample Data: Binders & Binder Accessories, Binders & Binder Accessories, Dialysate, Dialysate, Dialysate
category3: The third level category classification. Sample Data: Binders, Binders, Acid Con 3K, Acid Con 3K, Acid Con 3K
vendor_name: The name of the vendor receiving this order. Sample Data: CARSTENS CORPORATION, CARSTENS CORPORATION, FRESENIUS USA INC, FRESENIUS USA INC, FRESENIUS USA INC
vendor_name_normalized: The normalized version of the vendor name for consistent searching and matching. Sample Data: CARSTENS CORPORATION, CARSTENS CORPORATION, FRESENIUS USA INC, FRESENIUS USA INC, FRESENIUS USA INC
ordered_by: The name of the person who placed the order. Sample Data: JOHN SMITH, MARY JOHNSON, ROBERT BROWN, SARAH DAVIS, MICHAEL WILSON
unit_price: The unit price of the item. Sample Data: 15.89, 12.15, 13.46, 13.46, 13.46
quantity_ordered: The quantity of items ordered. Sample Data: 11, 15, 15, 11, 9
quantity_received: The quantity of items actually received. Sample Data: 11, 15, 15, 11, 9
amount_ordered: The total amount ordered (unit_price × quantity_ordered). Sample Data: 174.79, 182.25, 201.9, 148.06, 121.14
amount_received: The total amount received (unit_price × quantity_received). Sample Data: 174.79, 182.25, 201.9, 148.06, 121.14
unit_of_measure: The unit of measure for the order. Sample Data: EACH, EACH, CASE, CASE, CASE
expense_account: The expense account for financial tracking. Sample Data: 7600, 7600, 6604, 6604, 6604
charge_to: The charge to location or department. Sample Data: 05018, 03671, 11450, 04367, 03653
sub_account: The sub-account for detailed expense tracking. Sample Data: 300, 300, 300, 300, 300
eaches: The number of individual units per case. Sample Data: 1, 1, 4, 4, 4
eaches_uom: The unit of measure for individual units. Sample Data: EACH, EACH, GALLONS, GALLONS, GALLONS
quantity_eaches: The total quantity of individual units. Sample Data: 11, 15, 60, 44, 36
service_type: The type of service (e.g., In-Center Hemo). Sample Data: In-Center Hemo, In-Center Hemo, In-Center Hemo, In-Center Hemo, In-Center Hemo
source: The source of the order (e.g., OMG for ordering management group). Sample Data: NON-OMG, NON-OMG, OMG, NON-OMG, NON-OMG
closed_code: The closure status of the order. Sample Data: CLOSED, CLOSED, CLOSED, CLOSED, CLOSED
urgent_flag: Boolean flag (Y/N) indicating if the order is urgent. Sample Data: N, N, N, N, N
year: The year when the order was placed. Sample Data: 2025, 2025, 2025, 2025, 2025
month: The month when the order was placed. Sample Data: 7, 5, 10, 6, 2
year_month: The year-month combination for reporting. Sample Data: 2025/07, 2025/05, 2025/10, 2025/06, 2025/02
source_system: The source system that created or manages this order. Sample Data: IPRO, IPRO, IPRO, IPRO, IPRO
created_at: The timestamp when this order record was created. Sample Data: 2026-02-10 06:18:14.298154 UTC, 2026-02-10 06:18:14.298154 UTC
updated_at: The timestamp when this order record was last updated. Sample Data: 2026-02-10 06:18:21.068225 UTC, 2026-02-10 06:18:21.068225 UTC

Join to other tables with these considerations in mind:
Primary Vendor Join: Always join vendor_id to supplier master tables to get complete vendor information including contact details, payment terms, and performance metrics.
Catalog Integration: Join davita_item_number to IPRO_CATALOG to get complete product information including specifications, pricing, and vendor details.
Requisition Integration: Join requisition_id to requisition tables to analyze the complete procurement lifecycle from request to order fulfillment.
Facility Integration: Use facility_id to join to facility tables for detailed facility information, location analysis, and regional reporting.
Category Analysis: Use category1, category2, and category3 to join to category tables for hierarchical category analysis and spend reporting.
GL Account Integration: Use expense_account and sub_account to join to GL account tables for detailed expense analysis and budget variance reporting.
User Integration: Use ordered_by to join to employee tables for user-based procurement analysis and approval workflow analysis.
Service Type Analysis: Use service_type to join to service type tables for service-based spend analysis and operational reporting.
Geographic Analysis: Use city and state to join to geographic tables for regional spend analysis and location-based reporting.
Date-based Analysis: Use order_date, need_by_date, year, month, and year_month to analyze procurement timing patterns, seasonal trends, and order processing efficiency.
Financial Analysis: Use unit_price, quantity_ordered, quantity_received, amount_ordered, and amount_received to analyze spend patterns, identify price variances, and track budget utilization.
Order Status Analysis: Use closed_code and urgent_flag to analyze order processing patterns, identify bottlenecks, and track urgent order handling.
Source Analysis: Use source to analyze ordering patterns by source (OMG vs NON-OMG) and support process optimization.
Performance Considerations: Due to the extremely high record count (4.4M+), consider indexing strategies on vendor_id, facility_id, davita_item_number, and date fields for optimal query performance.
Inventory Planning: Use quantity_ordered and quantity_received to analyze order fulfillment rates and support inventory planning optimization.
Audit Trail: Use created_at and updated_at to track order record lifecycle for compliance reporting and change management analysis.

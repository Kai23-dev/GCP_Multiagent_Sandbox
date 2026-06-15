Table Description
Table Name: PO_REQUISITION_LINES_ALL
Record Count: Regular
Complete Description:
This table serves as the master repository for purchase requisition line items, representing the detailed line information for each purchase requisition in the Oracle E-Business Suite. Each record represents a specific line item on a purchase requisition with product details, vendor suggestions, quantities, pricing, and delivery requirements. This table is essential for detailed requisition analysis, demand planning, vendor selection, inventory planning, and maintaining the complete breakdown of requisition contents. The moderate record count indicates comprehensive line item tracking for purchase requisitions across the organization's procurement operations.
________________________________________

Column Description Schema
requisition_line_id: This is the Primary Key for the table. It is the unique system-generated identifier for each requisition line. Sample Data: 90951993, 90729259, 89929686
requisition_header_id: Foreign Key to PO_REQUISITION_HEADERS_ALL table. The unique identifier for the requisition header. Sample Data: 18446474, 18404322, 18237776
line_location_id: Foreign Key to location tables. The unique identifier for the line location. Sample Data: 79513249, 79323365, 78634697
category_id: Foreign Key to category tables. The unique identifier for the item category. Sample Data: 1403
line_type_id: Foreign Key to line type tables. The unique identifier for the line type. Sample Data: 1021, 1
vendor_id: Foreign Key to AP_SUPPLIERS table. The unique identifier for the suggested vendor. Sample Data: 8052
vendor_site_id: Foreign Key to AP_SUPPLIER_SITES_ALL table. The unique identifier for the vendor site. Sample Data: 10062
deliver_to_location_id: Foreign Key to HR_LOCATIONS table. The location where items will be delivered. Sample Data: 275684, 2370, 10451
charge_to_location: The location for charging purposes. Sample Data: 7708
line_number: The line number on the requisition. Sample Data: 1
item_description: The detailed description of the item being requested. Sample Data: LEAK FIX AT TWO RIVERS CLINIC, BICARB SYSTEM DECOMMISSION AND TRANSPORT, LABOR- BICARB SYSTEM REMOVAL
unit_of_measure: The unit of measure for ordering and pricing. Sample Data: HOUR, EACH
quantity: The quantity of items requested. Sample Data: 1, 20, 4
quantity_delivered: The quantity of items delivered. Sample Data: 20
unit_price: The unit price for the item. Sample Data: 150, 250, 8.65
need_by_date: The date when the items are needed by. Sample Data: 2025-01-15, 2025-01-20, 2025-01-25
suggested_vendor_name: The name of the suggested vendor. Sample Data: HYDROLOGIX INC
suggested_vendor_location: The location of the suggested vendor. Sample Data: CHESAPEAKE
suggested_vendor_product_code: The vendor's product code. Sample Data: 00001, 0001, 0664043
on_rfq_flag: Boolean flag (Y/N) indicating if the item is on an RFQ. Sample Data: N/A
urgent_flag: Boolean flag (Y/N) indicating if the requisition is urgent. Sample Data: N
service_type: The type of service for the requisition. Sample Data: In-Center Hemo, Bio-Med
source_updated_at: The timestamp when the requisition line was last updated in the source system. Sample Data: 2026-02-10 06:18:14.311841 UTC
source_system: The source system that created or manages this requisition line. Sample Data: ORACLE
created_at: The timestamp when this requisition line record was created. Sample Data: 2026-02-10 06:18:14.311841 UTC
updated_at: The timestamp when this requisition line record was last updated. Sample Data: 2026-02-10 06:18:18.167652 UTC

Join to other tables with these considerations in mind:
Primary Po Requisition Headers All Integration: Always join requisition_header_id to PO_REQUISITION_HEADERS_ALL.requisition_header_id to get complete Po Requisition Headers All information and establish the core relationship.
Primary Ap Suppliers Integration: Always join vendor_id to AP_SUPPLIERS.vendor_id to get complete Ap Suppliers information and establish the core relationship.
Primary Ap Supplier Sites All Integration: Always join vendor_site_id to AP_SUPPLIER_SITES_ALL.vendor_site_id to get complete Ap Supplier Sites All information and establish the core relationship.
Po Req Distributions All Integration: Use requisition_line_id to join to PO_REQ_DISTRIBUTIONS_ALL.requisition_line_id for complete transaction analysis and business context.
Header Integration: Use requisition_header_id to join to PO_REQUISITION_HEADERS_ALL for complete requisition information.
Distribution Integration: Use requisition_line_id to join to PO_REQ_DISTRIBUTIONS_ALL for budget allocation and cost center analysis.
Order Integration: Use requisition information to join to PO_LINES_ALL for requisition-to-order conversion tracking.
Vendor Integration: Use vendor_id to join to AP_SUPPLIERS for supplier information and performance analysis.
Financial Integration: Use requisition information to join with budget systems for budget validation and commitment accounting.
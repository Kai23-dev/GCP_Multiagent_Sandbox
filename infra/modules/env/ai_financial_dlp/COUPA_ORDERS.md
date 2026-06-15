Table Description
Table Name: COUPA_ORDERS
Record Count: Large
Complete Description:
This table serves as the master repository for all purchase orders processed through the Coupa procurement system. Each record represents a specific purchase order line item with detailed supplier information, financial details, departmental allocations, and order status. This table is essential for procurement analysis, supplier performance tracking, spend management, budget control, and operational reporting. The high record count indicates comprehensive purchase order coverage across the organization's procurement activities, providing complete visibility into the procurement lifecycle from requisition to order fulfillment.
________________________________________

Column Description Schema
po_number: This is the Primary Key for the table. It is the unique purchase order number used to identify each order. Sample Data: DVA-01170188, DVA-01058461, DVA-01253875
supplier_id: Foreign Key to supplier master tables. The unique identifier for the supplier receiving this order. Sample Data: 353598, 104216, 11828
requisition_id: Foreign Key to requisition tables. The unique identifier for the requisition that generated this order. Sample Data: 1224923, 1118491, 1316150
record_number: The record number within the requisition or order. Sample Data: 43, 0, 5
line_number: The line number on the requisition. Sample Data: 3, 0, 4
order_line_number: The line number on the purchase order. Sample Data: 4, 1, 5
order_date: The date when the purchase order was created. Sample Data: 2025-06-24, 2025-02-20, 2025-09-18
facility_number: The facility or location code where the item will be delivered. Sample Data: 11590, 02179, 00908
legal_entity: The legal entity code for the organization placing the order. Sample Data: 101392, 100050, 100043
department_number: The department code responsible for the purchase. Sample Data: 0400, 0253
gl_account_number: The general ledger account number for expense posting. Sample Data: 8030, 1899, 7849
subaccount_modality: The subaccount or modality code for detailed expense tracking. Sample Data: 300, 395
project_code: The project code if this purchase is project-related. Sample Data: N/A
supplier_name: The name of the supplier receiving this order. Sample Data: CLEAN WATER SERVICES INC, EVERON LLC, NETWORK CONNECTIONS INC
supplier_name_normalized: The normalized version of the supplier name for consistent searching and matching. Sample Data: CLEAN WATER SERVICES INC, EVERON LLC, NETWORK CONNECTIONS INC
commodity: The commodity category classification for the item. Sample Data: Water (8030), Security Alarm Monitoring (7701), General IT Installations & Support (7849)
item_description: The detailed description of the item being ordered. Sample Data: WATER TREATMENT SERVICES 2025, LAUREL MANOR DIALYSIS CENTER SECURITY SYSTEMS, 24 PORT CAT6 PATCH PANEL
department_name: The name of the department responsible for the purchase. Sample Data: Facilities Operations, Asset and Facilities Management, Administrative / Support
requester_name: The name of the person who requested the purchase. Sample Data: JOHN DOE, JANE SMITH, ROBERT JOHNSON
requester_job_title: The job title of the person who requested the purchase. Sample Data: FACILITIES MANAGER, ASSET MANAGER, IT COORDINATOR
unit_price: The unit price for the item being ordered. Sample Data: 130, 50176.36, 225
quantity: The quantity of items being ordered. Sample Data: 1, 3
line_spend: The total spend for this line (unit_price × quantity). Sample Data: 130, 50176.36, 225
total_order_spend: The total spend for the entire purchase order. Sample Data: 1970, 50176.36, 680.58
invoiced_amount: The amount that has been invoiced for this line. Sample Data: 0, 50176.36
line_status: The current status of this order line. Sample Data: cancelled
order_status: The current status of the entire purchase order. Sample Data: cancelled
source_system: The source system from which the order data originated. Sample Data: COUPA
created_at: The timestamp when this order record was created. Sample Data: 2026-02-10 06:18:14.421960 UTC
updated_at: The timestamp when this order record was last updated. Sample Data: 2026-02-10 06:18:24.037940 UTC

Join to other tables with these considerations in mind:
Catalog Integration: Use catalog information to join with COUPA_CATALOG for product details, pricing validation, and specification confirmation.
Invoice Integration: Use order information to join with COUPA_INVOICES for order-to-invoice reconciliation, three-way matching, and payment processing.
Supplier Integration: Use supplier_id to join with supplier information for performance analysis and contract compliance.
Requisition Integration: Use requisition_id to join with requisition tables for purchase cycle analysis and approval workflow tracking.
Financial Integration: Use order information to join with financial systems for budget validation and commitment accounting.
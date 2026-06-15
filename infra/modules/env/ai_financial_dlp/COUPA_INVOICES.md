Table Description
Table Name: COUPA_INVOICES
Record Count: Large
Complete Description:
This table serves as the master repository for all invoice transactions processed through the Coupa procurement system. Each record represents a specific invoice line item with detailed supplier information, financial details, contract references, and approval workflow status. This table is essential for accounts payable management, spend analysis, supplier performance tracking, contract compliance, and financial audit compliance. The high record count indicates comprehensive invoice processing coverage across the organization's procurement activities.
________________________________________

Column Description Schema
invoice_id: This is the Primary Key for the table. It is the unique system-generated identifier for each invoice record. Sample Data: 1674833, 1565419, 1526031
supplier_id: Foreign Key to supplier master tables. The unique identifier for the supplier who issued this invoice. Sample Data: 388747, 376502
invoice_number: The supplier's invoice number for reference and matching. Sample Data: 6032453262, 6026671092, 11625128
line_number: The line number on the invoice that identifies this specific line item. Sample Data: 0, 3, 1
invoice_date: The date on the invoice as provided by the supplier. Sample Data: 2025-05-21, 2025-03-13, 2025-01-31
created_date: The date when the invoice was created in the Coupa system. Sample Data: 2025-05-22, 2025-03-14, 2025-02-01
contract_creation_date: The date when the associated contract was created. Sample Data: 2023-01-27, 2022-04-21
invoice_amount: The total amount of the invoice line. Sample Data: 14.06, 13.71, 718697.39
unit_price: The unit price for the item being invoiced. Sample Data: 12.81, 87109.27, 16.25
quantity: The quantity of items being invoiced. Sample Data: 1, 4
currency_code: The currency code for the invoice transaction. Sample Data: USD
facility_number: The facility or location code where the item was delivered or used. Sample Data: 02870, 09782, 05555
department_number: The department code responsible for the purchase. Sample Data: 0120, 0400, 0831
gl_account_number: The general ledger account number for expense posting. Sample Data: 7685, 1598
supplier_name: The name of the supplier who issued this invoice. Sample Data: STAPLES INC, WORLD WIDE TECHNOLOGY LLC
supplier_name_normalized: The normalized version of the supplier name for consistent searching and matching. Sample Data: STAPLES INC, WORLD WIDE TECHNOLOGY LLC
po_number: The purchase order number associated with this invoice. Sample Data: DVA-01135647, DVA-01076502, DVA-01029603
order_line_number: The line number on the purchase order. Sample Data: 1, 4, 2
contract_name: The name of the contract associated with this invoice. Sample Data: Punchout for General Purchases, All IT Products & Services
contract_number: The contract number or identifier. Sample Data: All Purchases, All IT Products
commodity_category: The high-level commodity category classification. Sample Data: goods
commodity_id: Foreign Key to commodity classification tables. The unique identifier for the commodity category. Sample Data: 101, 104, 106
commodity_name: The name of the commodity category with code. Sample Data: Tablet Security (7685), Server License (7685), Speakers (7685)
item_description: The detailed description of the item being invoiced. Sample Data: HONEYWELL SERIES 3, 5, 9 WIRELESS
requested_by: The name of the person who requested the purchase. Sample Data: JOHN SMITH, MARY JOHNSON, ROBERT BROWN
requested_by_email: The email address of the person who requested the purchase. Sample Data: john.smith@company.com, mary.johnson@company.com, robert.brown@company.com
approval_status: The current approval status of the invoice. Sample Data: approved
source_system: The source system from which the invoice data originated. Sample Data: COUPA
created_at: The timestamp when this invoice record was created. Sample Data: 2026-02-10 06:18:14.395410 UTC
updated_at: The timestamp when this invoice record was last updated. Sample Data: 2026-02-10 06:18:20.510582 UTC

Join to other tables with these considerations in mind:
Catalog Integration: Use catalog information to join with COUPA_CATALOG for product details validation and pricing verification.
Order Integration: Use invoice information to join with COUPA_ORDERS for order-to-invoice reconciliation and receipt matching.
Supplier Integration: Use supplier information to join with supplier data for payment processing and performance analysis.
Financial Integration: Use invoice information to join with AP and GL systems for payment processing and financial reporting.
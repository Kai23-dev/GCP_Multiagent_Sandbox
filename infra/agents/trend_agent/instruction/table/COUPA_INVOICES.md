Table Description
Table Name: COUPA_INVOICES
Record Count: 1,275,011
Complete Description:
This table serves as the master repository for all invoice transactions processed through the Coupa procurement system. Each record represents a specific invoice line item with detailed supplier information, financial details, contract references, and approval workflow status. This table is essential for accounts payable management, spend analysis, supplier performance tracking, contract compliance, and financial audit compliance. The high record count indicates comprehensive invoice processing coverage across the organization's procurement activities.
Natural representation description:
This table acts as the complete invoice processing repository for the Coupa system, containing every invoice line with its associated supplier details, financial amounts, contract references, and approval status. It provides the foundation for comprehensive spend analysis, supplier management, and financial reporting across the entire procurement lifecycle.
________________________________________
Column Description Schema
invoice_id: This is the Primary Key for the table. It is the unique system-generated identifier for each invoice record. Sample Data: 1674833, 1565419, 1526031, 1821507, 1948050
supplier_id: Foreign Key to supplier master tables. The unique identifier for the supplier who issued this invoice. Sample Data: 388747, 388747, 376502, 388747, 388747
invoice_number: The supplier's invoice number for reference and matching. Sample Data: 6032453262, 6026671092, 11625128, 6038896831, 6043498697
line_number: The line number on the invoice that identifies this specific line item. Sample Data: 0, 0, 3, 0, 1
invoice_date: The date on the invoice as provided by the supplier. Sample Data: 2025-05-21, 2025-03-13, 2025-01-31, 2025-08-02, 2025-09-26
created_date: The date when the invoice was created in the Coupa system. Sample Data: 2025-05-22, 2025-03-14, 2025-02-01, 2025-08-03, 2025-09-27
contract_creation_date: The date when the associated contract was created. Sample Data: 2023-01-27, 2023-01-27, 2022-04-21, 2023-01-27, 2023-01-27
invoice_amount: The total amount of the invoice line. Sample Data: 14.06, 13.71, 718697.39, 17.33, 267.67
unit_price: The unit price for the item being invoiced. Sample Data: 12.81, 12.81, 87109.27, 16.25, 16.25
quantity: The quantity of items being invoiced. Sample Data: 1, 1, 1, 1, 4
currency_code: The currency code for the invoice transaction. Sample Data: USD, USD, USD, USD, USD
facility_number: The facility or location code where the item was delivered or used. Sample Data: 02870, 09782, 05555, 05087, 12000
department_number: The department code responsible for the purchase. Sample Data: 0120, 0400, 0831, 0400, 0400
gl_account_number: The general ledger account number for expense posting. Sample Data: 7685, 7685, 1598, 7685, 7685
supplier_name: The name of the supplier who issued this invoice. Sample Data: STAPLES INC, STAPLES INC, WORLD WIDE TECHNOLOGY LLC, STAPLES INC, STAPLES INC
supplier_name_normalized: The normalized version of the supplier name for consistent searching and matching. Sample Data: STAPLES INC, STAPLES INC, WORLD WIDE TECHNOLOGY LLC, STAPLES INC, STAPLES INC
po_number: The purchase order number associated with this invoice. Sample Data: DVA-01135647, DVA-01076502, DVA-01029603, DVA-01206935, DVA-01260157
order_line_number: The line number on the purchase order. Sample Data: 1, 1, 4, 1, 2
contract_name: The name of the contract associated with this invoice. Sample Data: Punchout for General Purchases, Punchout for General Purchases, All IT Products & Services, Punchout for General Purchases, Punchout for General Purchases
contract_number: The contract number or identifier. Sample Data: All Purchases, All Purchases, All IT Products, All Purchases, All Purchases
commodity_category: The high-level commodity category classification. Sample Data: goods, goods, goods, goods, goods
commodity_id: Foreign Key to commodity classification tables. The unique identifier for the commodity category. Sample Data: 101, 101, 104, 106, 106
commodity_name: The name of the commodity category with code. Sample Data: Tablet Security (7685), Tablet Security (7685), Server License (7685), Speakers (7685), Speakers (7685)
item_description: The detailed description of the item being invoiced. Sample Data: HONEYWELL SERIES 3, 5, 9 WIRELESS, HONEYWELL SERIES 3, 5, 9 WIRELESS, Palo Alto Platinum Support - Extended Service (Renewal) - 3 Year - Service, ADESSO XTREAM S4 DESKTOP SPEAKERS, ADESSO XTREAM S4 DESKTOP SPEAKERS
requested_by: The name of the person who requested the purchase. Sample Data: JOHN SMITH, MARY JOHNSON, ROBERT BROWN, SARAH DAVIS, MICHAEL WILSON
requested_by_email: The email address of the person who requested the purchase. Sample Data: john.smith@company.com, mary.johnson@company.com, robert.brown@company.com, sarah.davis@company.com, michael.wilson@company.com
approval_status: The current approval status of the invoice. Sample Data: approved, approved, approved, approved, approved
source_system: The source system from which the invoice data originated. Sample Data: COUPA, COUPA, COUPA, COUPA, COUPA
created_at: The timestamp when this invoice record was created. Sample Data: 2026-02-10 06:18:14.395410 UTC, 2026-02-10 06:18:14.395410 UTC
updated_at: The timestamp when this invoice record was last updated. Sample Data: 2026-02-10 06:18:20.510582 UTC, 2026-02-10 06:18:20.510582 UTC

Join to other tables with these considerations in mind:
Primary Supplier Join: Always join supplier_id to supplier master tables to get complete supplier information including contact details, payment terms, and performance metrics.
Purchase Order Integration: Join po_number and order_line_number to purchase order tables to perform invoice-to-PO matching validation and analyze procurement compliance.
Contract Management: Join contract_number and contract_name to contract master tables to analyze contract compliance, spend against contract, and contract performance.
Commodity Analysis: Join commodity_id to commodity classification tables to get detailed commodity hierarchy and support spend analysis by category.
GL Account Analysis: Use gl_account_number to join to GL account tables for detailed expense analysis and budget variance reporting.
Department and Facility Analysis: Use department_number and facility_number to join to department and location tables for organizational spend analysis and cost center reporting.
User Integration: Use requested_by and requested_by_email to join to employee tables for user-based spend analysis and approval workflow analysis.
Approval Workflow Analysis: Use approval_status to analyze invoice processing patterns, identify bottlenecks, and optimize approval workflows.
Currency Analysis: Use currency_code to join to currency tables for multi-currency invoice analysis and foreign exchange impact assessment.
Date-based Analysis: Use invoice_date, created_date, and contract_creation_date to analyze processing times, payment cycles, and contract lifecycle management.
Line Item Analysis: Use line_number and quantity to analyze invoice line details and support unit price variance analysis.
Amount Analysis: Use invoice_amount and unit_price to analyze spend patterns, identify high-value transactions, and perform price variance analysis.
Source System Integration: Use source_system to analyze invoice processing patterns by source system and identify data quality issues.
Audit Trail: Use created_at and updated_at to track invoice record lifecycle for compliance reporting and change management analysis.
Invoice Number Analysis: Use invoice_number for invoice tracking, duplicate detection, and supplier invoice management.

Table Description
Table Name: COUPA_Invoice_AI_Upload_2025
Record Count: 1,275,011
Complete Description:
This table contains comprehensive invoice data extracted from the Coupa procurement system, representing all invoice transactions processed through the platform. Each record represents a specific invoice line item with detailed financial, operational, and organizational context. This table serves as the central repository for invoice analytics, vendor spend analysis, contract compliance monitoring, and financial reporting across the entire organization's procurement activities.
Natural representation description:
This table acts as the master record for all invoices processed through the Coupa system, containing the complete lifecycle of each invoice from creation through approval. It captures the financial details (amounts, taxes, currency), organizational context (departments, facilities, regions), vendor information, and approval status that provides a comprehensive view of all spending activities across the organization.
________________________________________
Column Description Schema
Starting_Record: The batch or file starting record number for data processing and tracking purposes. Sample Data: 113550, 113550, 113550
Record_Number: The sequential record number within the batch or data extract. Sample Data: 39, 40, 41
Record_Line_Number: The line number within each invoice record (for multi-line invoices). Sample Data: 0, 0, 0
FACILITY_NUMBER: The facility or location code where the invoice transaction originated. Sample Data: 01655, 00378, 11314
DEPARTMENT_NUMBER: The department code responsible for the invoice transaction. Sample Data: 0400, 0400, 0400
GL_ACCOUNT_NUMBER: The general ledger account number for financial posting and expense categorization. Sample Data: 6610, 7622, 7610
Approval_Status: The current approval status of the invoice (e.g., approved, pending, rejected). Sample Data: approved, approved, approved
Commodity_Category: The high-level category classification of the purchased item (goods vs services). Sample Data: goods, goods, goods
Commodity_ID: The unique identifier for the specific commodity or item category. Sample Data: 541, 298, 149
COMMODITY: The descriptive name of the commodity category for spend analysis. Sample Data: Other Medical Supplies (6610), Teammate Morale--Food Only (7622), Cleaning Supplies (7610)
Contract_Creation_Date: The date when the associated contract was created. Sample Data: 2022-03-11, 2022-03-11, 2022-03-11
Contract_Name: The name or description of the associated contract. Sample Data: Punchout for General Purchases, Punchout for General Purchases, Punchout for General Purchases
Contract_Number: The unique contract number or identifier. Sample Data: AMZ 0001-P, AMZ 0001-P, AMZ 0001-P
Invoice_Created_Date: The date when the invoice was created in the system. Sample Data: 2025-06-06, 2025-06-06, 2025-06-06
Currency_Code: The currency code for the invoice transaction. Sample Data: USD, USD, USD
Item_Description: The detailed description of the item or service being invoiced. Sample Data: "Sterile Water, 1000ml (Four Pack of 250 ml)", "Nut Harvest, Nut & Fruit Mix, 37 Ounce Jar", "Hot Shot Ant, Roach & Spider Killer, Kills Insects Indoors and Outdoors, Kills Roaches and Listed Ants on Contact, Insecticide Spray, 17.5 Ounce (Crisp Linen)"
Invoice_ID: The unique system-generated identifier for the invoice. Sample Data: 1710146, 1710147, 1710148
Invoice_Date: The date of the invoice as provided by the vendor. Sample Data: 2025-06-06, 2025-06-06, 2025-06-06
Invoice_Number: The vendor-provided invoice number for reference and matching. Sample Data: 1FYM-CDK7-YCG7, 14KP-XTCN-YNKT, 1WXY-TFDR-YKFW
ORDER_LINE_NUM: The line number on the associated purchase order. Sample Data: 1, 1, 1
PO_NUMBER: The purchase order number associated with this invoice. Sample Data: DVA-01149368, DVA-01152124, DVA-01150215
UNIT_PRICE: The unit price of the item being invoiced. Sample Data: 15.95, 24.19, 4.68
ORDER_QTY: The quantity of items being invoiced. Sample Data: 1, 1, 1
Requested_By_Email: The email address of the person who requested the purchase. Sample Data: someone@somewhere.com, john@doe.us, jane@doe.com
Requested_By: The name of the person who requested the purchase. Sample Data: John Smith, Jane Doe, Bob Johnson
Division: The organizational division responsible for the purchase. Sample Data: Woodlands Division: OPER (D0213), Star Wranglers Division: OPER (D0225), Sierra Terrific Division: OPER (D0012)
Group: The organizational group within the division. Sample Data: Avanti (GV009), Galaxy (GV006), Polaris (GV033)
Phone_Num: The phone number associated with the requesting department or location. Sample Data: 123-456-7890, 987-654-3210, 555-123-4567
Region: The geographic region of the transaction. Sample Data: Woodlands Region 06: OPER (R1162), Star Wranglers Region 04: OPER (R0894), Sierra Terrific Region 05: OPER (R0882)
Location_Name: The full name of the facility or location. Sample Data: 01655-PDI-Johnstown, 00378-Northwest Kidney Center (Houston), 11314-Golden State Dialysis (fka Turlock II)
STATUS: The current status of the invoice transaction. Sample Data: approved, approved, approved
VENDOR_NAME: The name of the vendor or supplier. Sample Data: "AMAZON CAPITAL SERVICES, INC.", "AMAZON CAPITAL SERVICES, INC.", "AMAZON CAPITAL SERVICES, INC."
SUPPLIER_NUMBER: The unique supplier number or vendor ID. Sample Data: 263675, 263675, 263675
TOTAL: The total amount of the invoice line item (unit price × quantity). Sample Data: 15.95, 24.19, 4.68
Total_With_Tax: The total amount including any applicable taxes. Sample Data: 15.95, 24.19, 5.08
Updated_At_Date: The date when the invoice record was last updated. Sample Data: 2025-07-04, 2025-07-04, 2025-07-04
Updated_By_Name: The name of the user who last updated the invoice record. Sample Data: sFTP Integration, sFTP Integration, sFTP Integration
Year: The fiscal or calendar year of the transaction. Sample Data: 2025, 2025, 2025
Year_Month: The year and month combination for monthly reporting and analysis. Sample Data: 2025-06, 2025-06, 2025-06

Join to other tables with these considerations in mind:
PO System Integration: Join PO_NUMBER to PO_HEADERS_ALL and PO_LINES_ALL to get complete purchase order context and validate invoice-to-PO matching accuracy.
Vendor Master Data: Join SUPPLIER_NUMBER to AP_SUPPLIERS table to get comprehensive vendor information including payment terms, tax status, and contact details.
Financial Account Analysis: Join GL_ACCOUNT_NUMBER to GL_CODE_COMBINATIONS table to retrieve readable account segments for financial reporting and budget analysis.
Organizational Hierarchy: Join FACILITY_NUMBER, DEPARTMENT_NUMBER, Division, Group, and Region to organizational hierarchy tables to analyze spend by organizational structure.
Contract Compliance: Join Contract_Number to contract management tables to validate that invoices are within contract terms and pricing agreements.
Commodity Analysis: Join Commodity_ID to commodity master tables to get detailed commodity classifications for spend categorization and supplier diversity reporting.
User Information: Join Requested_By_Email and Updated_By_Name to user directories to get employee details for requestor analysis and audit trails.
Currency Conversion: Use Currency_Code to join to currency exchange rate tables for multi-currency reporting and financial consolidation.
Time-based Analysis: Use Invoice_Created_Date, Invoice_Date, Year, and Year_Month for trend analysis, seasonal patterns, and period-over-period comparisons.
Approval Workflow: Use Approval_Status and STATUS to join to workflow tables for approval cycle analysis and bottleneck identification.
Tax Analysis: Compare TOTAL against Total_With_Tax to analyze tax implications and join to tax rate tables for tax compliance reporting.
Duplicate Detection: Use Invoice_Number and VENDOR_NAME combinations to identify potential duplicate invoices across the system.
Spend Analysis: Aggregate TOTAL and Total_With_Tax by VENDOR_NAME, COMMODITY, Department, and Region for comprehensive spend analysis and vendor performance metrics.
Data Quality: Use Starting_Record, Record_Number, and Record_Line_Number to track data processing batches and identify any data loading issues or gaps.

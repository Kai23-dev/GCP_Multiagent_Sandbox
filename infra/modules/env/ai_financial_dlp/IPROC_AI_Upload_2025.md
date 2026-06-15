Table Description
Table Name: IPROC_AI_Upload_2025
Record Count: 4,406,124
Complete Description:
This table contains comprehensive procurement transaction data extracted from the iProcurement system for 2025, representing all purchase order line items processed through the platform. Each record represents a specific line item within a purchase order with detailed financial, operational, and organizational context. This table serves as the central repository for procurement analytics, spend analysis, vendor performance monitoring, and operational efficiency tracking across the entire organization's purchasing activities.
Natural representation description:
This table acts as the master record for all purchase order transactions processed through the iProcurement system in 2025, containing the complete lifecycle of each order line from creation through receipt. It captures the financial details (prices, quantities, amounts), organizational context (locations, departments, service types), vendor information, and order status that provides a comprehensive view of all purchasing activities across the organization.
________________________________________
Column Description Schema
Location: The facility or location code where the transaction originated. Sample Data: 00416, 03071, 11594, 05417
City: The city where the facility is located. Sample Data: POLACCA, LUDINGTON, RALEIGH, YONKERS
State: The state where the facility is located. Sample Data: AZ, MI, NC, NY
Telephone_Num: The telephone number for the facility. Sample Data: 123-456-7890
Loc_Name: The descriptive name of the facility or location. Sample Data: HOPI DIALYSIS CENTER, LUDINGTON DIALYSIS, WESTCHESTER HOME TRAINING (PD)
PO_Creation_Date: The timestamp when the purchase order was created. Sample Data: 2025-10-20 10:13:46, 2025-11-04 09:33:32, 2025-11-17 13:01:01
Requisition: The requisition number that originated this purchase order. Sample Data: 17044334, 17091357, 17129741
PO_Number: The unique purchase order number. Sample Data: 130304-1191380, 130304-1206236, 95083-1264684
Urgent_Flag: Indicates if the order is marked as urgent (Y/N). Sample Data: N, N, Y, N/A
Vendor: The name of the vendor or supplier. Sample Data: ASD HEALTHCARE, ASD HEALTHCARE, VANTIVE US HEALTHCARE LLC
Vendor_Number: The unique vendor number or supplier ID. Sample Data: 355583, 355583, 7639, 402319
Line_Number: The line number within the purchase order. Sample Data: 1, 2, 26, 2, 1
Product_Number: The vendor's product number or SKU. Sample Data: 718793, 718793, 2400043, 718797, 2B1324X
DVA_Item_Num: The internal item number for the product. Sample Data: 1064443, 1064443, 1073203, 1064444, 1070102
Ordered_By_Name: The name of the person who placed the order. Sample Data: "Support Services, PRISM", "Support Services, PRISM", "Support Services, PRISM", "gT1#_t=fO""LJW 0'yBrittany"
Order_Date: The date when the order was placed. Sample Data: 2025-10-20 10:13:46, 2025-11-04 09:33:32, 2025-11-17 13:01:01
Item_Desc: The detailed description of the item being ordered. Sample Data: MIRCERA 30MCG 0.3ML PREFILLED SYRINGE VIFOR (EACH) ASD (718793), "SODIUM CHLORIDE, (SELECT FACILITIES ONLY) 0.9% FOR INJECTION VIAFLEX BAG 1L (14/CASE) VANTIVE US HEALTHCARE (2B1324X)"
CATEGORY1: The primary category classification for the item. Sample Data: Pharma, Med Supplies, Med Supplies
CATEGORY2: The secondary category classification for the item. Sample Data: General Med, MedSurg, Saline
CATEGORY3: The tertiary category classification for the item. Sample Data: Other, Calibration & Testing, None
Closed_Code: The status code indicating if the order line is closed. Sample Data: CLOSED FOR INVOICE, CLOSED, CLOSED
Qty_Ordered: The quantity of items ordered. Sample Data: 1, 6, 1, 2, 15
Qty_Rcvd: The quantity of items received. Sample Data: 0, 0, 1, 0, 15
UNIT_PRICE: The unit price of the item. Sample Data: 32.31, 32.31, 8.2, 161.51, 21
Amount_Ordered: The total amount ordered (Qty_Ordered × UNIT_PRICE). Sample Data: 32.31, 193.86, 8.2, 323.02, 315
Amount_Rcvd: The total amount received (Qty_Rcvd × UNIT_PRICE). Sample Data: 0, 0, 8.2, 0, 315
UOM: The unit of measure for the item. Sample Data: EACH, EACH, BOX, EACH, CASE
Expense_Account: The expense account number for financial posting. Sample Data: 6303, 6303, 6610, 6303, 6606
Charge_To: The cost center or department being charged. Sample Data: 00416, 03071, 11594, 05417, 01707
Sub_Account: The sub-account for detailed expense tracking. Sample Data: 390, 300, 300, 390, 300
Service_Type: The service type or modality (e.g., PD, In-Center Hemo). Sample Data: PD, In-Center Hemo, In-Center Hemo, PD, In-Center Hemo
Source: The source system or origin of the transaction. Sample Data: NON-OMG, NON-OMG, NON-OMG, NON-OMG, OMG
NEED_BY_DATE: The date by which the item is needed. Sample Data: 2025-10-25 00:00:00, 2025-11-09 00:00:00, 2025-11-22 00:00:00, 2025-10-06 00:00:00, 2025-10-04 00:00:00
Year: The fiscal or calendar year of the transaction. Sample Data: 2025, 2025, 2025, 2025, 2025
Month: The month of the transaction. Sample Data: 10, 11, 11, 10, 9
Year_Month: The year and month combination for reporting. Sample Data: 2025/10, 2025/11, 2025/11, 2025/10, 2025/09
Eaches: The quantity in eaches (individual units). Sample Data: 0.3, 0.3, 50, 0.3, 14
Eaches_UOM: The unit of measure for eaches. Sample Data: ML, PACK, EACH, CASE, LITERS
Manufacturer: The manufacturer of the product. Sample Data: VIFOR, VIFOR, N/A, VIFOR, N/A
Product_Category: The product category classification. Sample Data: PHARMA - MIRCERA, PHARMA - MIRCERA, TEST STRIP, PHARMA - MIRCERA, SODIUM CHLORIDE
Qty_Eaches: The total quantity in eaches. Sample Data: 0.3, 1.8, 50, 0.6, 210
Product: The product name or generic description. Sample Data: MIRCERA, MIRCERA, GLUCOSE URINALYSIS TEST STRIP, MIRCERA, NORMAL SALINE

Join to other tables with these considerations in mind:
Location Master Data: Join Location to facility master tables to get detailed location information, operational capacity, and regional data for geographic analysis.
Vendor Master Integration: Join Vendor_Number to AP_SUPPLIERS table to get comprehensive vendor information including payment terms, tax status, and performance metrics.
Employee Information: Join Ordered_By_Name to employee master tables (xxc_iproc_employees) to get detailed employee information, department assignments, and approval authority.
Financial Account Analysis: Join Expense_Account and Sub_Account to GL_CODE_COMBINATIONS table to retrieve readable account segments for financial reporting and budget analysis.
Requisition Traceability: Join Requisition to PO_REQUISITION_HEADERS_ALL and PO_REQUISITION_LINES_ALL to trace the complete purchase request lifecycle from requisition to order.
Product Master Integration: Join DVA_Item_Num and Product_Number to item master tables to get detailed specifications, pricing, and inventory information.
Service Type Analysis: Join Service_Type to service line tables to analyze spending patterns, operational metrics, and resource allocation by modality.
Cost Center Analysis: Join Charge_To to cost center master tables to get departmental hierarchies, budget information, and organizational structure.
Time-based Analysis: Use PO_Creation_Date, Order_Date, NEED_BY_DATE, Year, Month, and Year_Month for trend analysis, seasonal patterns, and period-over-period comparisons.
Receipt Reconciliation: Compare Qty_Ordered vs Qty_Rcvd and Amount_Ordered vs Amount_Rcvd to identify order fulfillment issues and receipt discrepancies.
Urgent Order Analysis: Use Urgent_Flag to identify and analyze urgent orders for supply chain optimization and vendor performance evaluation.
Category Hierarchy Analysis: Use CATEGORY1, CATEGORY2, CATEGORY3, and Product_Category to analyze spend patterns across different categorization schemes and identify opportunities for standardization.
Source System Analysis: Use Source to differentiate between OMG and NON-OMG transactions for system-specific analysis and process optimization.
Manufacturer Analysis: Join Manufacturer to manufacturer master tables to analyze supplier concentration, product availability, and supply chain risk.
Unit Conversion Analysis: Use the relationship between UOM, Eaches, Eaches_UOM, and Qty_Eaches to analyze unit conversions and ensure data consistency in inventory management.

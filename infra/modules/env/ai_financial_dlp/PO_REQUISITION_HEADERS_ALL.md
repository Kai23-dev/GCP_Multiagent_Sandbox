Table Description
Table Name: PO_REQUISITION_HEADERS_ALL
Record Count: Regular
Complete Description:
This table serves as the master repository for purchase requisition headers, representing the main information for each purchase requisition in the Oracle E-Business Suite. Each record represents a complete purchase requisition with requester information, creation dates, and approval status. This table is essential for requisition management, demand planning, approval workflow monitoring, and maintaining the complete lifecycle of purchase requisitions from creation to conversion to purchase orders. The moderate record count indicates comprehensive requisition management across the organization's procurement operations.
________________________________________

Column Description Schema
requisition_header_id: This is the Primary Key for the table. It is the unique system-generated identifier for each purchase requisition. Sample Data: 17651668, 16913484, 17869264
requisition_number: The purchase requisition number used for business reference. Sample Data: 15954507, 15359445, 16170097
created_by: Foreign Key to employee/user tables. The unique identifier for the user who created the requisition. Sample Data: 100010, 100027, 100250
creation_date: The date when the requisition was created in the source system. Sample Data: 2024-10-10 13:48:41.000000 UTC, 2024-03-25 13:44:29.000000 UTC
source_updated_at: The timestamp when the requisition was last updated in the source system. Sample Data: 2024-10-10 13:48:41.000000 UTC, 2024-03-25 13:44:29.000000 UTC
source_system: The source system that created or manages this purchase requisition. Sample Data: ORACLE
created_at: The timestamp when this requisition record was created in the current system. Sample Data: 2026-02-10 06:18:14.279535 UTC
updated_at: The timestamp when this requisition record was last updated in the current system. Sample Data: 2026-02-10 06:18:18.211359 UTC

Join to other tables with these considerations in mind:
Po Requisition Lines All Integration: Use requisition_header_id to join to PO_REQUISITION_LINES_ALL.requisition_header_id for complete transaction analysis and business context.
Line Integration: Use requisition_header_id to join to PO_REQUISITION_LINES_ALL for complete requisition details and item information.
Order Integration: Use requisition information to join to PO_HEADERS_ALL for requisition-to-order conversion analysis.
Financial Integration: Use requisition information to join with budget systems for budget validation and commitment tracking.
Approval Integration: Use approval information to analyze procurement workflows and cycle time analysis.
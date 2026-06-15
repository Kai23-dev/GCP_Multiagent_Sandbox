Table Description
Table Name: PO_REQ_DISTRIBUTIONS_ALL
Record Count: Regular
Complete Description:
This table serves as the master repository for purchase requisition distribution lines, representing the financial and accounting breakdown of purchase requisition line items across different cost centers, departments, or projects. Each record represents a specific distribution of a requisition line to a particular account combination, tracking quantities, project information, and expenditure details. This table is essential for financial accounting, budget tracking, cost allocation, project cost management, and maintaining the financial integrity of purchase requisition processing throughout the Oracle E-Business Suite. The moderate record count indicates comprehensive distribution tracking for purchase requisitions across the organization.
________________________________________

Column Description Schema
distribution_id: This is the Primary Key for the table. It is the unique system-generated identifier for each distribution record. Sample Data: 87702002, 84855995, 88732592
requisition_line_id: Foreign Key to PO_REQUISITION_LINES_ALL table. The unique identifier for the requisition line. Sample Data: 88245672, 85443853, 89263026
project_id: Foreign Key to project tables. The unique identifier for the project if applicable. Sample Data: N/A
task_id: Foreign Key to project task tables. The unique identifier for the project task if applicable. Sample Data: N/A
expenditure_organization_id: Foreign Key to organization tables. The unique identifier for the expenditure organization. Sample Data: N/A
code_combination_id: Foreign Key to GL_CODE_COMBINATIONS table. The GL account combination for this distribution. Sample Data: 6613947, 6613800, 7554631
req_line_quantity: The quantity from the requisition line for this distribution. Sample Data: 384, 1920, 711
expenditure_type: The type of expenditure for this distribution. Sample Data: N/A
project_related_flag: Boolean flag (Y/N) indicating if this distribution is project-related. Sample Data: N
expenditure_item_date: The date of the expenditure item. Sample Data: N/A
source_updated_at: The timestamp when this distribution was last updated in the source system. Sample Data: 2026-02-10 06:18:14.425878 UTC
source_system: The source system that created or manages this distribution. Sample Data: ORACLE
created_at: The timestamp when this distribution record was created. Sample Data: 2026-02-10 06:18:14.425878 UTC
updated_at: The timestamp when this distribution record was last updated. Sample Data: 2026-02-10 06:18:18.256842 UTC

Join to other tables with these considerations in mind:
Primary Po Requisition Lines All Integration: Always join requisition_line_id to PO_REQUISITION_LINES_ALL.requisition_line_id to get complete Po Requisition Lines All information and establish the core relationship.
Po Distributions All Integration: Use distribution_id to join to PO_DISTRIBUTIONS_ALL.req_distribution_id for complete transaction analysis and business context.
Line Integration: Use requisition_line_id to join to PO_REQUISITION_LINES_ALL for complete requisition line information.
Financial Integration: Use distribution information to join with financial systems for budget tracking and cost center analysis.
Project Integration: Use project_id and task_id to join with project systems for project cost tracking and analysis.
Organization Integration: Use expenditure_organization_id to join with organizational tables for departmental analysis.
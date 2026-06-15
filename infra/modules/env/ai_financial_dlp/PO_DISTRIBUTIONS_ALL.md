Table Description
Table Name: PO_DISTRIBUTIONS_ALL
Record Count: Regular
Complete Description:
This table serves as the master repository for purchase order distribution lines, representing the financial and accounting breakdown of purchase order line items across different cost centers, departments, or projects. Each record represents a specific distribution of a PO line to a particular account combination, tracking quantities, amounts, and accrual status. This table is essential for financial accounting, budget tracking, cost allocation, accrual management, and maintaining the financial integrity of purchase order processing throughout the Oracle E-Business Suite. The moderate record count indicates comprehensive distribution tracking for purchase orders across the organization.
________________________________________

Column Description Schema
distribution_id: This is the Primary Key for the table. It is the unique system-generated identifier for each distribution record. Sample Data: 72971011, 79661907, 79661646
po_header_id: Foreign Key to PO_HEADERS_ALL table. The unique identifier for the purchase order header. Sample Data: 8737778, 9392895, 9392893
po_line_id: Foreign Key to PO_LINES_ALL table. The unique identifier for the purchase order line. Sample Data: 9374277, 10200637, 10200634
line_location_id: Foreign Key to PO_LINE_LOCATIONS table. The unique identifier for the line location. Sample Data: 72539982, 79138573, 79138317
req_distribution_id: Foreign Key to PO_REQ_DISTRIBUTIONS_ALL table. The unique identifier for the requisition distribution. Sample Data: 82283653, 90004170, 90003713
code_combination_id: Foreign Key to GL_CODE_COMBINATIONS table. The GL account combination for this distribution. Sample Data: 10002959, 10002969
accrual_account_id: Foreign Key to GL_CODE_COMBINATIONS table. The GL account for accruals. Sample Data: 6615321
variance_account_id: Foreign Key to GL_CODE_COMBINATIONS table. The GL account for variances. Sample Data: 10002959, 10002969
quantity_ordered: The quantity ordered for this distribution. Sample Data: 300, 325, 532
quantity_delivered: The quantity delivered for this distribution. Sample Data: 0, 325, 532
quantity_billed: The quantity billed for this distribution. Sample Data: 0
quantity_cancelled: The quantity cancelled for this distribution. Sample Data: 0
amount_billed: The amount billed for this distribution. Sample Data: 0
accrued_flag: Boolean flag (Y/N) indicating if accruals have been processed. Sample Data: Y
source_system: The source system that created or manages this distribution. Sample Data: ORACLE
created_at: The timestamp when this distribution record was created. Sample Data: 2026-02-10 06:18:12.139567 UTC
updated_at: The timestamp when this distribution record was last updated. Sample Data: 2026-02-10 06:18:15.957046 UTC

Join to other tables with these considerations in mind:
Primary Po Headers All Integration: Always join po_header_id to PO_HEADERS_ALL.po_header_id to get complete Po Headers All information and establish the core relationship.
Primary Po Lines All Integration: Always join po_line_id to PO_LINES_ALL.po_line_id to get complete Po Lines All information and establish the core relationship.
Primary Po Req Distributions All Integration: Always join req_distribution_id to PO_REQ_DISTRIBUTIONS_ALL.distribution_id to get complete Po Req Distributions All information and establish the core relationship.
Header Integration: Use po_header_id to join to PO_HEADERS_ALL for complete order information and vendor details.
Line Integration: Use po_line_id to join to PO_LINES_ALL for detailed line item information and specifications.
Requisition Integration: Use req_distribution_id to join to PO_REQ_DISTRIBUTIONS_ALL for budget validation and purchase tracking.
Financial Integration: Use distribution information to join with financial systems for budget tracking and commitment accounting.
Cost Center Analysis: Use distribution information for departmental expense analysis and budget variance reporting.
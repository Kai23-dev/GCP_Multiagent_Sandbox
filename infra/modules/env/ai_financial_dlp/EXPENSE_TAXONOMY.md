Table Description
Table Name: Expense_Taxonomy
Record Count: Very Small
Complete Description:
This table serves as the master repository for expense taxonomy and classification hierarchy, representing the structured categorization of expenses across different sourcing lanes and account levels. Each record represents a specific expense category with its hierarchical classification, GL account mapping, and ownership information. This table is essential for expense classification, financial reporting consistency, cost analysis, spend categorization, and maintaining standardized expense taxonomy across the organization. The low record count indicates a well-defined and controlled expense classification structure used for consistent financial reporting and analysis.
________________________________________

Column Description Schema
Sourcing_Lane: This is the Primary Key for the table. It represents the sourcing lane classification for expense tracking. Sample Data: Direct
L1_Category: The first level category in the expense hierarchy. Sample Data: Dialysis Equipment & Supplies
L2_Category: The second level category in the expense hierarchy. Sample Data: CRRT Dialysis Supplies, Dialysis Equipment Repair & Maintenance, Dialysis Equipment Supplies
L3_Category: The third level category in the expense hierarchy with GL account code. Sample Data: 6616 - CRRT Supply Expense, 6800 - R&M Dialysis Machine, 6830 - R&M BioMed
GL_Account_L3_Code: Foreign Key to GL_CODE_COMBINATIONS table. The GL account code for the third level category. Sample Data: 6616, 6800, 6830
GL_Account_Description: The description of the GL account. Sample Data: CRRT Supply Expense, R&M Dialysis Machine, R&M BioMed
Is_Direct_Flag: Boolean flag indicating if this is a direct expense. Sample Data: true
Category_Owner: The owner or manager responsible for this expense category. Sample Data: JOHN SMITH, MARY JOHNSON, ROBERT BROWN
Effective_Start_Date: The start date when this taxonomy classification becomes effective. Sample Data: 2026-02-23
Effective_End_Date: The end date when this taxonomy classification expires. Sample Data: N/A

Join to other tables with these considerations in mind:
GL Integration: Use GL_Account_L3_Code to join with XXC_GL_SUMMARY.account for actual expense transaction analysis and budget validation.
Organizational Integration: Use Category_Owner to join with organizational tables for responsibility accounting and performance analysis.
Hierarchical Analysis: Use Sourcing_Lane and category hierarchy for multi-level expense reporting and cost allocation analysis.
Time Analysis: Use Effective_Start_Date and Effective_End_Date for taxonomy change analysis and historical expense reporting.
Budget Integration: Use GL_Account_L3_Code to join with budget systems for budget vs actual analysis and variance reporting.
Compliance Analysis: Use taxonomy structure for regulatory reporting compliance and expense classification validation.
Table Description
Table Name: SPEND_TAXONOMY
Record Count: 1,124
Complete Description:
This table is the spend classification taxonomy, representing the hierarchical structure for categorizing expenses across multiple classification systems including Oracle categories and PRISM commodity codes. Each record represents a specific spend classification with its mapping between different taxonomy systems and account details. This table is essential for spend analysis, financial reporting consistency, procurement categorization, supplier performance analysis, and maintaining standardized expense classification across the organization. The moderate record count indicates a comprehensive spend classification structure that supports multiple reporting and analysis requirements.

________________________________________
Column Description Schema
Account: This is the Primary Key for the table. It represents the GL account code for expense classification. Sample Data: 7720, 6011, 6011, 6011, 6011
Oracle Super Category: The highest level category in the Oracle classification system. Sample Data: Other Controllable, Medical Supplies, Expenses
Oracle Category: The second level category in the Oracle classification system. Sample Data: Other Purchased Services, Professional Fees, Facility, MTN & Repair, Freight & Postage
PRISM Commodity Level 1: The highest level category in the PRISM commodity classification system. Sample Data: Dialysis Equipment & Supplies, Pharma, Dialysis Equipment & Supplies, IT Products & Services
PRISM Commodity Level 2: The second level category in the PRISM commodity classification system. Sample Data: Advertising, Vitamin D Medications, Dialysis Medication, Dialysis Supplies, Dialysis Equipment Repair & Maintenance
PRISM Commodity Level 3: The third level category in the PRISM commodity classification system. Sample Data: Routine Pharmacy Expense, Syringe and Needle Expense, Disinfectant, Engineering
PRISM Commodity Name: The descriptive name for the PRISM commodity classification. Sample Data: Zemplar, Gloves, Catheters, General Waste Disposal
Commodity Level: The level indicator for the commodity classification (L3, L4, etc.). Sample Data: L3, L4
Account Description: The description of the GL account. Sample Data: Advertising, Sal & Wage-Contract, Non Supply PD Expense, Direct Medical Supply Expense

Join to other tables with these considerations in mind:
Primary GL Integration: Always join Account to XXC_GL_SUMMARY to get complete GL account information including account segments and detailed descriptions.
Spend Analysis: Use the hierarchical categories to join to expense transaction tables for categorized spend analysis and reporting across multiple classification systems.
Invoice Line Item Spend (PRISM Commodity Name) Integration: Use table invoice_extracts_prepared with nested attribute line_items.category to identify all instances of invoice line items for a given PRISM Commodity Name. In other words, join invoice_extracts_prepared with SPEND_TAXONOMY on invoice_extracts_prepared.line_items.category and SPEND_TAXONOMY.PRISM Commodity Name to retrieve all matching invoice line items.
Taxonomy Roll-up: Use PRISM Commodity Level 1-3 to roll-up expeneses falling under a specific PRISM Commodity Name by using the hierarchy. 
Cross-System Analysis: Use the mapping between Oracle and PRISM categories to analyze spend classification consistency across different systems and support taxonomy harmonization.
Supplier Analysis: Use PRISM commodity classifications to join to supplier tables for supplier performance analysis by commodity category.
Procurement Analysis: Use PRISM commodity levels to join to procurement tables for category-based procurement analysis and strategic sourcing initiatives.
Financial Reporting: Use Account and Account Description to join to financial reporting tables for standardized expense reporting across different classification systems.
Taxonomy Consistency: Use this table as the master reference to ensure consistent spend classification across all financial and procurement systems.
Category Management: Use the hierarchical structure to analyze spend patterns and support category management initiatives and procurement optimization strategies.

Table Description
Table Name: INVOICE_ID_TO_FILE_NAME
Complete Description:
This table serves as the mapping repository between invoice IDs and their corresponding file information, representing the link between financial invoice records and their document storage locations. Each record represents an invoice with its associated file details, data type, and storage identifiers. This table is essential for document management, invoice retrieval, file access coordination, and maintaining the connection between financial transactions and their supporting documents. 
________________________________________
Column Description Schema
invoice_id: This is the Primary Key for the table. It is the unique system-generated identifier for each invoice. Sample Data: 41058693, 42488300, 45117536, 45317721, 46087186
invoice_number: The business invoice number used for reference and identification. Sample Data: CA073020CA01865, 714605, 509-OCT-21, 726147, 277511_ALHAMBRA2_2021_0955
datatype_name: Foreign Key to FND_DOCUMENT_DATATYPES table. The data type classification for the invoice document. Sample Data: WEB_PAGE
file_name: The name of the file associated with the invoice. Sample Data: 10107241, 11744305, 14753653, 14979877, 15857828
url: The URL where the invoice file can be accessed or retrieved. Sample Data: link to the document.
p8_file_id: The file identifier in the P8 document management system. Sample Data: 10107241, 11744305, 14753653, 14979877, 15857828

Join to other tables with these considerations in mind:
Primary Invoice Integration: Always join invoice_id to AP_INVOICES_ALL to get complete invoice information including vendor details, amounts, dates, and payment status.
Invoice Number Integration: Use invoice_number to join to AP_INVOICES_ALL for business-level invoice identification and validation.
File Management Integration: Use p8_file_id to join to invoice_extracts_prepared, the parsed invoice data
URL Integration: Use url to join to web access systems for online document access and retrieval workflows.
Invoice Validation: Use this table to validate that all invoices have corresponding document files and identify missing documentation.
Audit Trail: Use this mapping to trace invoice documents back to their financial transactions for audit compliance and verification.
Data Quality Analysis: Use this table to identify invoices without proper file mappings and ensure data integrity across financial and document systems.
System Integration: Use this table as the bridge between financial systems (AP) and document management systems (P8) for integrated workflow support.

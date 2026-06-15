Table Description
Table Name: FND_ATTACHED_DOCUMENTS
Record Count: Very Large
Complete Description:
This table serves as the master repository for document attachments, representing the relationship between documents and business entities throughout the Oracle Applications system. Each record represents a specific attachment that links a document to a particular business entity (such as invoices, purchase orders, or other transactions). This table is essential for document management, attachment tracking, audit compliance, and maintaining the relationship between business transactions and their supporting documentation. The high record count indicates extensive use of document attachments across various business processes.
________________________________________

Column Description Schema
attached_document_id: This is the Primary Key for the table. It is the unique system-generated identifier for each attachment relationship. Sample Data: 62542993, 62545059, 65468034
document_id: Foreign Key to DOCUMENTS table. The unique identifier for the document being attached. Sample Data: 45397264, 45399330, 47909716
entity_name: The name of the business entity type to which the document is attached. Sample Data: AP_INVOICES
entity_pk_value: The primary key value of the specific business entity instance. Sample Data: 60063705, 60065759, 62133496
sequence_number: The sequence number for ordering multiple attachments to the same entity. Sample Data: 1
created_by: Foreign Key to user tables. The user ID of the person who created this attachment. Sample Data: 108429, 118741, 149118
last_updated_by: Foreign Key to user tables. The user ID of the person who last updated this attachment. Sample Data: 108429, 118741, 149118
source_created_at: The timestamp when this attachment was created in the source system. Sample Data: 2025-01-15 10:30:00 UTC, 2025-02-20 14:45:00 UTC, 2025-03-10 09:15:00 UTC
source_updated_at: The timestamp when this attachment was last updated in the source system. Sample Data: 2025-01-15 10:30:00 UTC, 2025-02-20 14:45:00 UTC, 2025-03-10 09:15:00 UTC
source_system: The source system that created or manages this attachment. Sample Data: ORACLE
created_at: The timestamp when this attachment record was created in the current system. Sample Data: 2026-02-10 06:18:14.334359 UTC
updated_at: The timestamp when this attachment record was last updated in the current system. Sample Data: 2026-02-10 06:18:20.359326 UTC

Join to other tables with these considerations in mind:
Primary Documents Integration: Always join document_id to DOCUMENTS.document_id to get complete Documents information and establish the core relationship.
Document Integration: Use document_id to join to DOCUMENTS for complete document information, file details, and metadata.
Entity Analysis: Use entity_name and entity_pk_value to join with business transaction tables for complete context and relationship analysis.
Workflow Integration: Use attachment relationships to analyze business process flows, approval workflows, and document lifecycle management.
Audit Trail: Use created_by, last_updated_by, and timestamp fields for compliance reporting and change management analysis.
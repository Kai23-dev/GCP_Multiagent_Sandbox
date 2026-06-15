Table Description
Table Name: DOCUMENTS
Record Count: Very Large
Complete Description:
This table serves as the master repository for all documents and attachments within the system, representing a comprehensive document management system. Each record represents a specific document with its associated metadata, content, file information, and security settings. This table is essential for document management, content storage, attachment tracking, security compliance, and audit trail maintenance. The extremely high record count indicates this is a central document repository supporting multiple business processes including invoices, purchase orders, contracts, and other transactional documents.
________________________________________

Column Description Schema
document_id: This is the Primary Key for the table. It is the unique system-generated identifier for each document. Sample Data: 45375118, 45397512
media_id: Foreign Key to media storage tables. The unique identifier for the media file storage location. Sample Data: N/A
datatype_id: Foreign Key to data type tables. The identifier for the data type or format of the document. Sample Data: 5
category_id: Foreign Key to document category tables. The identifier for the document category classification. Sample Data: 1000533
attached_entity_type: The type of entity this document is attached to (e.g., AP_INVOICES, PO_HEADERS, CONTRACTS). Sample Data: AP_INVOICES
attached_entity_id: The unique identifier of the entity this document is attached to. Sample Data: 60017922, 60063953
document_type: The system code for the document type. Sample Data: WEB_PAGE
document_type_display: The display name for the document type. Sample Data: Web Page
language_code: The language code for the document content. Sample Data: US
document_content: The actual content of the document (may be stored separately for large files). Sample Data: N/A
file_name: The name of the document file. Sample Data: 29239665, 29251803
document_url: The URL where the document can be accessed. Sample Data: N/A
usage_type: The usage type classification for the document. Sample Data: S
security_type: The security type or access level for the document. Sample Data: 2
translation_language: The language code for document translation if applicable. Sample Data: US
source_system: The source system that created or manages this document. Sample Data: ORACLE
created_at: The timestamp when this document record was created. Sample Data: 2026-02-10 06:18:21.302282 UTC
updated_at: The timestamp when this document record was last updated. Sample Data: 2026-02-10 06:18:21.302282 UTC

Join to other tables with these considerations in mind:
Fnd Attached Documents Integration: Use document_id to join to FND_ATTACHED_DOCUMENTS.document_id for complete transaction analysis and business context.
Document Attachment Integration: Use document_id to join to FND_ATTACHED_DOCUMENTS for attachment relationships, business entity context, and transaction linkage.
File Management Integration: Use file_name and url to join with document storage systems for file access, retrieval workflows, and storage optimization.
Document Type Integration: Use datatype_id to join to FND_DOCUMENT_DATATYPES for document format analysis, processing requirements, and system integration.
Category Integration: Use category_id to join to FND_DOCUMENT_CATEGORIES_TL for document classification, access control, and reporting analysis.
Multi-language Support: Use document_id to join to FND_DOCUMENTS_TL for translation analysis and multi-language document management.
Security Analysis: Use security_type and security_id for access pattern analysis and compliance reporting.
Audit Trail: Use created_at and updated_at for document lifecycle analysis and retention policy management.
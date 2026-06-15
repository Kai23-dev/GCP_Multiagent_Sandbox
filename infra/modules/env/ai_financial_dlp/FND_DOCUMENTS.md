Table Description
Table Name: FND_DOCUMENTS
Record Count: Very Large
Complete Description:
This table serves as the master repository for document metadata and file information within the Oracle Applications Foundation (FND) system. Each record represents a specific document with its associated metadata, file details, security settings, and storage information. This table is essential for document management, content storage, security control, and maintaining the foundation for document attachments throughout the Oracle E-Business Suite. The high record count indicates extensive use of document management across various business processes and modules.
________________________________________

Column Description Schema
document_id: This is the Primary Key for the table. It is the unique system-generated identifier for each document. Sample Data: 45383956, 45396438, 43321904
media_id: Foreign Key to media storage tables. The unique identifier for the media file storage location and format. Sample Data: N/A
datatype_id: Foreign Key to data type tables. The identifier for the data type or format of the document (e.g., PDF, Word, Excel). Sample Data: 5
category_id: Foreign Key to document category tables. The identifier for the document category classification. Sample Data: 1000533, 1000468
security_type: The security type classification for access control (e.g., 2=Standard, 4=Public). Sample Data: 2, 4
security_id: Foreign Key to security tables. The identifier for specific security rules or groups. Sample Data: 1
usage_type: The usage type classification for the document (S=Standard, O=Official). Sample Data: S, O
file_name: The name of the document file or file identifier. Sample Data: 29244155, 29250741, davita_fi20240000213082
url: The URL where the document can be accessed or retrieved. Sample Data: https://dms.davita.de/documents/jsp/qv?pri=davita&ft=Invoice@archivrechnungen&q_FileID=davita_fi20240000213082, https://dms.davita.de/documents/jsp/qv?pri=davita&ft=Invoice@archivrechnungen&q_FileID=davita_fi20240000214003, https://dms.davita.de/documents/jsp/qv?pri=davita&ft=Invoice@archivrechnungen&q_FileID=davita_fi20240000216729
created_by: Foreign Key to user tables. The user ID of the person who created this document. Sample Data: 108429, 109080
last_updated_by: Foreign Key to user tables. The user ID of the person who last updated this document. Sample Data: 108429, 109080
source_created_at: The timestamp when this document was created in the source system. Sample Data: 2025-01-15 10:30:00 UTC, 2025-02-20 14:45:00 UTC, 2025-03-10 09:15:00 UTC
source_updated_at: The timestamp when this document was last updated in the source system. Sample Data: 2025-01-15 10:30:00 UTC, 2025-02-20 14:45:00 UTC, 2025-03-10 09:15:00 UTC
source_system: The source system that created or manages this document. Sample Data: ORACLE
created_at: The timestamp when this document record was created in the current system. Sample Data: 2026-02-10 06:18:14.318295 UTC
updated_at: The timestamp when this document record was last updated in the current system. Sample Data: 2026-02-10 06:18:21.370006 UTC

Join to other tables with these considerations in mind:
Attachment Integration: Use document_id to join to FND_ATTACHED_DOCUMENTS for business context, entity relationships, and transaction linkage.
Document Type Integration: Use datatype_id to join to FND_DOCUMENT_DATATYPES for format analysis, processing requirements, and system integration.
Category Integration: Use category_id to join to FND_DOCUMENT_CATEGORIES_TL for classification analysis, access control, and reporting.
Translation Integration: Use document_id to join to FND_DOCUMENTS_TL for multi-language support and localization analysis.
Security Integration: Use security_type and security_id for access pattern analysis, compliance reporting, and security audit trails.
Storage Integration: Use media_id and url to join with storage systems for capacity planning, access optimization, and cost analysis.
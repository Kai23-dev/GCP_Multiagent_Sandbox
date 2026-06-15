Table Description
Table Name: FND_DOCUMENT_DATATYPES
Record Count: Very Small
Complete Description:
This table serves as the master repository for document data types in the Oracle Applications Foundation (FND) system. Each record represents a specific document data type with its associated language-specific names and display information. This table is essential for document type classification, format management, content processing, and maintaining consistency in document handling throughout the Oracle E-Business Suite. The very low record count indicates a limited, standardized set of document data types used across the organization's document management system.
________________________________________

Column Description Schema
datatype_id: This is the Primary Key for the table. It is the unique system-generated identifier for each document data type. Sample Data: 6, 2, 1
language_code: The language code for this data type definition (e.g., US for American English, FR for French, DE for German). Sample Data: US
datatype_name: The internal system name for the document data type in the specified language. Sample Data: FILE, LONG_TEXT, SHORT_TEXT
user_display_name: The user-friendly display name for the document data type shown in the user interface. Sample Data: File, Long Text, Short Text
created_by: Foreign Key to user tables. The user ID of the person who created this data type definition. Sample Data: 1
last_updated_by: Foreign Key to user tables. The user ID of the person who last updated this data type definition. Sample Data: 2
source_created_at: The timestamp when this data type definition was created in the source system. Sample Data: 2020-01-01 00:00:00 UTC
source_updated_at: The timestamp when this data type definition was last updated in the source system. Sample Data: 2020-01-01 00:00:00 UTC
source_system: The source system that created or manages this data type definition. Sample Data: ORACLE
created_at: The timestamp when this data type definition record was created in the current system. Sample Data: 2026-02-10 06:18:14.311708 UTC
updated_at: The timestamp when this data type definition record was last updated in the current system. Sample Data: 2026-02-10 06:18:17.672113 UTC

Join to other tables with these considerations in mind:
Invoice Id To File Name Integration: Use datatype_name to join to INVOICE_ID_TO_FILE_NAME.datatype_name for complete transaction analysis and business context.
Document Integration: Use datatype information to join to FND_DOCUMENTS for document format analysis and processing requirements.
File Analysis: Use datatype details to analyze document processing workflows, storage requirements, and system integration.
System Integration: Use datatype information for system compatibility analysis and processing optimization.
Performance Analysis: Use datatype patterns to optimize document processing and system performance.
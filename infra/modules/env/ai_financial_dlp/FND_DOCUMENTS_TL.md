Table Description
Table Name: FND_DOCUMENTS_TL
Record Count: Very Large
Complete Description:
This table serves as the multi-language translation repository for documents in the Oracle Applications Foundation (FND) system. The "_TL" suffix indicates this is a Translation Layer table that stores language-specific information for documents. Each record represents a document translation for a specific language, enabling internationalization and multi-language support throughout the Oracle E-Business Suite. This table is essential for global document management, localization compliance, multi-language user support, and maintaining document information in multiple languages. The high record count indicates extensive use of multi-language support across the organization's document management system.
________________________________________

Column Description Schema
document_id: This is the Primary Key for the table. It is the unique system-generated identifier for each document translation record. Sample Data: 43881521, 44047343, 43979172
language: The language code for this translation (e.g., US for American English, FR for French, DE for German). Sample Data: US
created_by: Foreign Key to user tables. The user ID of the person who created this document translation. Sample Data: 109080, 149136
last_updated_by: Foreign Key to user tables. The user ID of the person who last updated this document translation. Sample Data: 109080, 149136
source_created_at: The timestamp when this document translation was created in the source system. Sample Data: 2025-01-15 10:30:00 UTC, 2025-02-20 14:45:00 UTC, 2025-03-10 09:15:00 UTC
source_updated_at: The timestamp when this document translation was last updated in the source system. Sample Data: 2025-01-15 10:30:00 UTC, 2025-02-20 14:45:00 UTC, 2025-03-10 09:15:00 UTC
source_system: The source system that created or manages this document translation. Sample Data: ORACLE
created_at: The timestamp when this document translation record was created in the current system. Sample Data: 2026-02-10 06:18:14.329666 UTC
updated_at: The timestamp when this document translation record was last updated in the current system. Sample Data: 2026-02-10 06:18:19.186801 UTC

Join to other tables with these considerations in mind:
Document Integration: Use document_id to join to FND_DOCUMENTS for base document information, metadata, and file details.
Language Analysis: Use language to analyze multi-language document availability, translation coverage, and localization compliance.
Translation Management: Combine with user information for translation workflow analysis and quality control.
Regional Analysis: Use language patterns to support regional reporting and compliance requirements.
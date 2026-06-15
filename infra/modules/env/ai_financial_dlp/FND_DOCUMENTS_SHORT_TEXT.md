Table Description
Table Name: FND_DOCUMENTS_SHORT_TEXT
Record Count: Large
Complete Description:
This table serves as the repository for short text content associated with documents in the Oracle Applications Foundation (FND) system. Each record represents a text content entry linked to a specific media file, typically containing notes, comments, descriptions, or brief textual information that supplements document files. This table is essential for document annotation, comment tracking, textual content storage, and maintaining supplementary information for documents throughout the Oracle E-Business Suite. The moderate record count indicates selective use of text annotations for specific documents requiring additional textual context.
________________________________________

Column Description Schema
media_id: This is the Primary Key for the table. It is the unique identifier that links this text content to a specific media file or document. Sample Data: 7808674, 7810731, 7810760
short_text: The actual text content of the annotation, note, or description associated with the document. Sample Data: APREQ0537793 PAYMENT REQUEST: TEAMMATE CHECK WAS SENT OUT TO WRONG ADDRESS. CHECK HAS BEEN VOIDED AND INVOICE PUT ON HOLD. PROCESSING DATE: 03/06/2024 REQUESTED BY: DNIMBALKAR, APREQ0538007 PAYMENT REQUEST: KINDLY REISSUE THE CHECK TO CORRECT ADDRESS. CHECK HAS BEEN VOIDED AND INVOICE PUT ON HOLD. PROCESSING DATE: 03/07/2024 REQUESTED BY: DNIMBALKAR, APREQ0538035 PAYMENT REQUEST: CHECK SENT TO INCORRECT ADDRESS. CORRECT ADDRESS PROVIDED. CHECK HAS BEEN VOIDED AND INVOICE PUT ON HOLD. PROCESSING DATE: 03/07/2024 REQUESTED BY: DNIMBALKAR
source_system: The source system that created or manages this text content. Sample Data: ORACLE
created_at: The timestamp when this text content record was created. Sample Data: 2026-02-10 06:18:12.128974 UTC
updated_at: The timestamp when this text content record was last updated. Sample Data: 2026-02-10 06:18:15.956641 UTC

Join to other tables with these considerations in mind:
Document Integration: Use media_id to join to FND_DOCUMENTS for complete document information, metadata, and business context.
Attachment Integration: Use media_id to join through FND_DOCUMENTS to FND_ATTACHED_DOCUMENTS for entity relationships and business process context.
Text Analysis: Use short_text content for content analysis, keyword extraction, sentiment analysis, and document categorization.
Language Analysis: Combine with FND_DOCUMENTS_TL for multi-language text analysis and localization support.
Content Search: Use text content for full-text search capabilities, document retrieval, and knowledge management.
CREATE OR REPLACE TABLE `sco_supplier_classification.INVOICE_ID_TO_FILE_NAME` AS
SELECT DISTINCT
  aia.invoice_id,
  aia.invoice_number,
  fdat.datatype_name,
  fd.file_name,
  fd.url,
  
  -- Standarized P8 / File ID Extraction
  COALESCE(
    -- 1. Extract from the P8 URL (e.g., https://...invoiceId=2013128)
    REGEXP_EXTRACT(fd.url, r'invoiceId=(\d+)'),
    
    -- 2. Extract if the file_name is literally just the ID (e.g., '28665154')
    REGEXP_EXTRACT(fd.file_name, r'^(\d+)$'),
    
    -- 3. Extract if it's a manually uploaded file named with the ID (e.g., '1987819.pdf')
    REGEXP_EXTRACT(fd.file_name, r'^(\d+)\.[a-zA-Z0-9]+$')
  ) AS p8_file_id

FROM `ai_financial_dlp.AP_INVOICES_ALL` AS aia
INNER JOIN `ai_financial_dlp.FND_ATTACHED_DOCUMENTS` AS fad
  ON fad.entity_pk_value = aia.invoice_id AND fad.entity_name = 'AP_INVOICES'
INNER JOIN `ai_financial_dlp.FND_DOCUMENTS` AS fd
  ON fd.document_id = fad.document_id
INNER JOIN `ai_financial_dlp.FND_DOCUMENT_DATATYPES` AS fdat
  ON fdat.datatype_id = fd.datatype_id AND fdat.language_code = 'US'

-- CRITICAL FILTER: Only grab Web Pages (P8 Links). Ignore Files and text notes.
WHERE fdat.datatype_name = 'WEB_PAGE'
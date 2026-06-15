CREATE OR REPLACE TABLE `sco_rage_invoice_extract_ds.invoice_extracts_prepared`
PARTITION BY DATE(extraction_timestamp)
CLUSTER BY p8_file_id, vendor, invoice_number
OPTIONS(
  description="Prepared OCR extracts with standardized p8_file_id for real-time AI agent joins."
)
AS
SELECT 
  *,
  -- Extracts digits/ID between the last '/' and the '.pdf' extension
  REGEXP_EXTRACT(input_file_name, r'/([^/]+)\.[^.]+$') AS p8_file_id
FROM `sco_rage_invoice_extract_ds.invoice_extracts`;

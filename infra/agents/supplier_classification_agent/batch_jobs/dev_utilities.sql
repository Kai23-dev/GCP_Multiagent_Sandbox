-- Dev Utilities for Catalog Categorization Tables
-- WARNING: These operations can delete categorization data. Source catalogs remain untouched.

-- =============================================================================
-- RESET CATEGORIZATION TABLES (Development/Testing)
-- =============================================================================

-- Drop and recreate IPRO categorizations
DROP TABLE IF EXISTS `{project}.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION`;

CREATE TABLE `{project}.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION` (
  davita_item_number STRING NOT NULL,
  prism_commodity_name_predicted STRING,
  prism_prediction_confidence FLOAT64,
  prism_prediction_model STRING,
  prism_categorized_at TIMESTAMP,
  categorization_run_id STRING,
  item_description_snapshot STRING,
  account_code_snapshot STRING
)
PARTITION BY DATE(prism_categorized_at)
OPTIONS(
  description="LLM-generated PRISM commodity categorizations for IPRO catalog items."
);

ALTER TABLE `{project}.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION`
ADD PRIMARY KEY (davita_item_number) NOT ENFORCED;

-- Drop and recreate COUPA categorizations
DROP TABLE IF EXISTS `{project}.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION`;

CREATE TABLE `{project}.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION` (
  item_id STRING NOT NULL,
  prism_commodity_name_predicted STRING,
  prism_prediction_confidence FLOAT64,
  prism_prediction_model STRING,
  prism_categorized_at TIMESTAMP,
  categorization_run_id STRING,
  item_description_snapshot STRING
)
PARTITION BY DATE(prism_categorized_at)
OPTIONS(
  description="LLM-generated PRISM commodity categorizations for COUPA catalog items."
);

ALTER TABLE `{project}.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION`
ADD PRIMARY KEY (item_id) NOT ENFORCED;

-- =============================================================================
-- VIEW CATEGORIZATION COVERAGE STATS
-- =============================================================================

SELECT 
  'IPRO_CATALOG' as catalog,
  COUNT(DISTINCT cat.davita_item_number) as total_items,
  COUNT(DISTINCT ctg.davita_item_number) as categorized_items,
  ROUND(COUNT(DISTINCT ctg.davita_item_number) / COUNT(DISTINCT cat.davita_item_number) * 100, 2) as coverage_pct,
  ROUND(AVG(ctg.prism_prediction_confidence), 3) as avg_confidence
FROM `{project}.ai_financial_dlp.IPRO_CATALOG` cat
LEFT JOIN `{project}.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION` ctg
  ON cat.davita_item_number = ctg.davita_item_number

UNION ALL

SELECT 
  'COUPA_CATALOG' as catalog,
  COUNT(DISTINCT cat.item_id) as total_items,
  COUNT(DISTINCT ctg.item_id) as categorized_items,
  ROUND(COUNT(DISTINCT ctg.item_id) / COUNT(DISTINCT cat.item_id) * 100, 2) as coverage_pct,
  ROUND(AVG(ctg.prism_prediction_confidence), 3) as avg_confidence
FROM `{project}.ai_financial_dlp.COUPA_CATALOG` cat
LEFT JOIN `{project}.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION` ctg
  ON cat.item_id = ctg.item_id;

-- =============================================================================
-- VIEW LOW CONFIDENCE CATEGORIZATIONS (For Review)
-- =============================================================================

SELECT 
  'IPRO' as source,
  ctg.davita_item_number as item_id,
  ctg.item_description_snapshot as description,
  ctg.prism_commodity_name_predicted as predicted_category,
  ctg.prism_prediction_confidence as confidence,
  ctg.account_code_snapshot as account_code
FROM `{project}.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION` ctg
WHERE ctg.prism_prediction_confidence < 0.7
ORDER BY ctg.prism_prediction_confidence ASC
LIMIT 100;

-- =============================================================================
-- DELETE CATEGORIZATIONS FROM A SPECIFIC RUN (For Re-running Failed Batches)
-- =============================================================================

-- Example: Delete IPRO categorizations from a specific run
-- DELETE FROM `{project}.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION`
-- WHERE categorization_run_id = 'IPRO_CATALOG_20260310_140530';

-- Example: Delete COUPA categorizations from a specific run
-- DELETE FROM `{project}.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION`
-- WHERE categorization_run_id = 'COUPA_CATALOG_20260310_140530';

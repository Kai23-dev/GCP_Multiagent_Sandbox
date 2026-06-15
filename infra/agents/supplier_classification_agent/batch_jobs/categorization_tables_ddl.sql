-- DDL for Catalog Categorization Tables
-- Dataset: sco_supplier_classification
-- Purpose: Store LLM-generated PRISM commodity categorizations for catalog items

-- =============================================================================
-- IPRO_CATALOG_CATEGORIZATION Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION` (
  davita_item_number STRING NOT NULL,
  prism_commodity_name_predicted STRING NOT NULL,
  prism_prediction_confidence FLOAT64 NOT NULL,
  prism_prediction_model STRING NOT NULL,
  prism_categorized_at TIMESTAMP NOT NULL,
  categorization_run_id STRING NOT NULL,
  item_description_snapshot STRING,
  account_code_snapshot STRING,
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
OPTIONS(
  description = 'LLM-generated PRISM commodity categorizations for IPRO catalog items. Links catalog items to taxonomy for tail supplier consolidation analysis.'
);

-- Add primary key constraint (informational - BigQuery doesn't enforce)
-- PRIMARY KEY: davita_item_number

-- Create index on categorization timestamp for stale record queries
CREATE INDEX IF NOT EXISTS idx_ipro_categorized_at 
ON `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION` (prism_categorized_at);

-- Create index on predicted category for join performance
CREATE INDEX IF NOT EXISTS idx_ipro_predicted_category 
ON `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION` (prism_commodity_name_predicted);

-- Create index on confidence for filtering
CREATE INDEX IF NOT EXISTS idx_ipro_confidence 
ON `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION` (prism_prediction_confidence);


-- =============================================================================
-- COUPA_CATALOG_CATEGORIZATION Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION` (
  item_id STRING NOT NULL,
  prism_commodity_name_predicted STRING NOT NULL,
  prism_prediction_confidence FLOAT64 NOT NULL,
  prism_prediction_model STRING NOT NULL,
  prism_categorized_at TIMESTAMP NOT NULL,
  categorization_run_id STRING NOT NULL,
  item_description_snapshot STRING,
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
OPTIONS(
  description = 'LLM-generated PRISM commodity categorizations for COUPA catalog items. Links catalog items to taxonomy for tail supplier consolidation analysis.'
);

-- Add primary key constraint (informational - BigQuery doesn't enforce)
-- PRIMARY KEY: item_id

-- Create index on categorization timestamp for stale record queries
CREATE INDEX IF NOT EXISTS idx_coupa_categorized_at 
ON `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION` (prism_categorized_at);

-- Create index on predicted category for join performance
CREATE INDEX IF NOT EXISTS idx_coupa_predicted_category 
ON `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION` (prism_commodity_name_predicted);

-- Create index on confidence for filtering
CREATE INDEX IF NOT EXISTS idx_coupa_confidence 
ON `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION` (prism_prediction_confidence);


-- =============================================================================
-- Data Quality Checks
-- =============================================================================

-- Check for duplicate categorizations (should not exist)
SELECT 'IPRO Duplicates' as check_type, COUNT(*) as duplicate_count
FROM (
  SELECT davita_item_number, COUNT(*) as cnt
  FROM `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION`
  GROUP BY davita_item_number
  HAVING cnt > 1
);

SELECT 'COUPA Duplicates' as check_type, COUNT(*) as duplicate_count
FROM (
  SELECT item_id, COUNT(*) as cnt
  FROM `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION`
  GROUP BY item_id
  HAVING cnt > 1
);

-- Check for orphaned categorizations (catalog items that no longer exist)
SELECT 'IPRO Orphans' as check_type, COUNT(*) as orphan_count
FROM `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION` ctg
LEFT JOIN `sco-kb-dev-1a9n.ai_financial_dlp.IPRO_CATALOG` cat
  ON ctg.davita_item_number = cat.davita_item_number
WHERE cat.davita_item_number IS NULL;

SELECT 'COUPA Orphans' as check_type, COUNT(*) as orphan_count
FROM `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION` ctg
LEFT JOIN `sco-kb-dev-1a9n.ai_financial_dlp.COUPA_CATALOG` cat
  ON ctg.item_id = cat.item_id
WHERE cat.item_id IS NULL;

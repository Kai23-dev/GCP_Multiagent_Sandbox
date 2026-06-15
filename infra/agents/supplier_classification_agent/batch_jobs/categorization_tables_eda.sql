-- EDA for Catalog Categorization Tables
-- Dataset: sco_supplier_classification
-- Purpose: Analyze LLM categorization quality and distribution

-- =============================================================================
-- 1. Overall Statistics
-- =============================================================================

-- Summary statistics for both catalogs
SELECT 
  'IPRO' as catalog,
  COUNT(*) as total_items,
  COUNT(DISTINCT prism_commodity_name_predicted) as unique_categories,
  COUNTIF(prism_commodity_name_predicted = 'Unknown') as unknown_count,
  ROUND(COUNTIF(prism_commodity_name_predicted = 'Unknown') / COUNT(*) * 100, 1) as unknown_pct,
  ROUND(AVG(prism_prediction_confidence), 3) as avg_confidence,
  ROUND(MIN(prism_prediction_confidence), 3) as min_confidence,
  ROUND(MAX(prism_prediction_confidence), 3) as max_confidence,
  COUNT(DISTINCT categorization_run_id) as total_runs,
  MAX(prism_categorized_at) as latest_categorization
FROM `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION`

UNION ALL

SELECT 
  'COUPA' as catalog,
  COUNT(*) as total_items,
  COUNT(DISTINCT prism_commodity_name_predicted) as unique_categories,
  COUNTIF(prism_commodity_name_predicted = 'Unknown') as unknown_count,
  ROUND(COUNTIF(prism_commodity_name_predicted = 'Unknown') / COUNT(*) * 100, 1) as unknown_pct,
  ROUND(AVG(prism_prediction_confidence), 3) as avg_confidence,
  ROUND(MIN(prism_prediction_confidence), 3) as min_confidence,
  ROUND(MAX(prism_prediction_confidence), 3) as max_confidence,
  COUNT(DISTINCT categorization_run_id) as total_runs,
  MAX(prism_categorized_at) as latest_categorization
FROM `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION`;


-- =============================================================================
-- 2. Top Categories by Item Count
-- =============================================================================

-- IPRO Top 20 Categories
SELECT 
  'IPRO' as catalog,
  prism_commodity_name_predicted,
  COUNT(*) as item_count,
  ROUND(AVG(prism_prediction_confidence), 2) as avg_confidence,
  ROUND(MIN(prism_prediction_confidence), 2) as min_confidence,
  ROUND(MAX(prism_prediction_confidence), 2) as max_confidence,
  ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 1) as pct_of_total
FROM `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION`
GROUP BY prism_commodity_name_predicted
ORDER BY item_count DESC
LIMIT 20;

-- COUPA Top 20 Categories
SELECT 
  'COUPA' as catalog,
  prism_commodity_name_predicted,
  COUNT(*) as item_count,
  ROUND(AVG(prism_prediction_confidence), 2) as avg_confidence,
  ROUND(MIN(prism_prediction_confidence), 2) as min_confidence,
  ROUND(MAX(prism_prediction_confidence), 2) as max_confidence,
  ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 1) as pct_of_total
FROM `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION`
GROUP BY prism_commodity_name_predicted
ORDER BY item_count DESC
LIMIT 20;


-- =============================================================================
-- 3. Confidence Distribution Analysis
-- =============================================================================

-- Confidence buckets for IPRO
SELECT 
  'IPRO' as catalog,
  CASE 
    WHEN prism_prediction_confidence = 1.0 THEN '1.0 (Perfect)'
    WHEN prism_prediction_confidence >= 0.9 THEN '0.9-0.99 (Very High)'
    WHEN prism_prediction_confidence >= 0.7 THEN '0.7-0.89 (High)'
    WHEN prism_prediction_confidence >= 0.5 THEN '0.5-0.69 (Medium)'
    WHEN prism_prediction_confidence > 0.0 THEN '0.01-0.49 (Low)'
    ELSE '0.0 (Unknown)'
  END as confidence_bucket,
  COUNT(*) as item_count,
  ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 1) as pct_of_total
FROM `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION`
GROUP BY confidence_bucket
ORDER BY MIN(prism_prediction_confidence) DESC;

-- Confidence buckets for COUPA
SELECT 
  'COUPA' as catalog,
  CASE 
    WHEN prism_prediction_confidence = 1.0 THEN '1.0 (Perfect)'
    WHEN prism_prediction_confidence >= 0.9 THEN '0.9-0.99 (Very High)'
    WHEN prism_prediction_confidence >= 0.7 THEN '0.7-0.89 (High)'
    WHEN prism_prediction_confidence >= 0.5 THEN '0.5-0.69 (Medium)'
    WHEN prism_prediction_confidence > 0.0 THEN '0.01-0.49 (Low)'
    ELSE '0.0 (Unknown)'
  END as confidence_bucket,
  COUNT(*) as item_count,
  ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 1) as pct_of_total
FROM `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION`
GROUP BY confidence_bucket
ORDER BY MIN(prism_prediction_confidence) DESC;


-- =============================================================================
-- 4. Category Coverage Analysis
-- =============================================================================

-- Categories used in categorizations vs available in taxonomy
WITH taxonomy_categories AS (
  SELECT DISTINCT `PRISM Commodity Name` as category
  FROM `sco-kb-dev-1a9n.sco_supplier_classification.SPEND_TAXONOMY`
  WHERE `PRISM Commodity Name` IS NOT NULL
),
ipro_categories AS (
  SELECT DISTINCT prism_commodity_name_predicted as category
  FROM `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION`
  WHERE prism_commodity_name_predicted != 'Unknown'
),
coupa_categories AS (
  SELECT DISTINCT prism_commodity_name_predicted as category
  FROM `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION`
  WHERE prism_commodity_name_predicted != 'Unknown'
)
SELECT 
  'Taxonomy' as source,
  COUNT(*) as category_count
FROM taxonomy_categories
UNION ALL
SELECT 
  'IPRO Used' as source,
  COUNT(*) as category_count
FROM ipro_categories
UNION ALL
SELECT 
  'COUPA Used' as source,
  COUNT(*) as category_count
FROM coupa_categories
UNION ALL
SELECT 
  'Both Catalogs Used' as source,
  COUNT(*) as category_count
FROM (
  SELECT category FROM ipro_categories
  INTERSECT DISTINCT
  SELECT category FROM coupa_categories
);


-- =============================================================================
-- 5. Low Confidence Items (Needs Review)
-- =============================================================================

-- IPRO items with low confidence (< 0.5)
SELECT 
  'IPRO' as catalog,
  davita_item_number as item_id,
  item_description_snapshot,
  prism_commodity_name_predicted,
  prism_prediction_confidence,
  account_code_snapshot
FROM `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION`
WHERE prism_prediction_confidence < 0.5
  AND prism_commodity_name_predicted != 'Unknown'
ORDER BY prism_prediction_confidence ASC
LIMIT 50;

-- COUPA items with low confidence (< 0.5)
SELECT 
  'COUPA' as catalog,
  item_id,
  item_description_snapshot,
  prism_commodity_name_predicted,
  prism_prediction_confidence
FROM `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION`
WHERE prism_prediction_confidence < 0.5
  AND prism_commodity_name_predicted != 'Unknown'
ORDER BY prism_prediction_confidence ASC
LIMIT 50;


-- =============================================================================
-- 6. Categorization Run Analysis
-- =============================================================================

-- Analyze categorization runs over time
SELECT 
  'IPRO' as catalog,
  categorization_run_id,
  COUNT(*) as items_categorized,
  ROUND(AVG(prism_prediction_confidence), 3) as avg_confidence,
  COUNTIF(prism_commodity_name_predicted = 'Unknown') as unknown_count,
  MIN(prism_categorized_at) as run_timestamp
FROM `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION`
GROUP BY categorization_run_id, prism_categorized_at
ORDER BY run_timestamp DESC;

SELECT 
  'COUPA' as catalog,
  categorization_run_id,
  COUNT(*) as items_categorized,
  ROUND(AVG(prism_prediction_confidence), 3) as avg_confidence,
  COUNTIF(prism_commodity_name_predicted = 'Unknown') as unknown_count,
  MIN(prism_categorized_at) as run_timestamp
FROM `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION`
GROUP BY categorization_run_id, prism_categorized_at
ORDER BY run_timestamp DESC;


-- =============================================================================
-- 7. Join Validation - Check Categorizations Link to Source Catalogs
-- =============================================================================

-- IPRO: Check all categorizations have valid catalog items
SELECT 
  COUNT(*) as total_categorizations,
  COUNT(cat.davita_item_number) as valid_catalog_links,
  COUNT(*) - COUNT(cat.davita_item_number) as orphaned_categorizations
FROM `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION` ctg
LEFT JOIN `sco-kb-dev-1a9n.ai_financial_dlp.IPRO_CATALOG` cat
  ON ctg.davita_item_number = cat.davita_item_number;

-- COUPA: Check all categorizations have valid catalog items
SELECT 
  COUNT(*) as total_categorizations,
  COUNT(cat.item_id) as valid_catalog_links,
  COUNT(*) - COUNT(cat.item_id) as orphaned_categorizations
FROM `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION` ctg
LEFT JOIN `sco-kb-dev-1a9n.ai_financial_dlp.COUPA_CATALOG` cat
  ON ctg.item_id = cat.item_id;


-- =============================================================================
-- 8. Check Categorizations Link to Taxonomy
-- =============================================================================

-- IPRO: Check predicted categories exist in taxonomy
SELECT 
  COUNT(DISTINCT ctg.prism_commodity_name_predicted) as predicted_categories,
  COUNT(DISTINCT tax.`PRISM Commodity Name`) as valid_taxonomy_matches,
  COUNT(DISTINCT ctg.prism_commodity_name_predicted) - COUNT(DISTINCT tax.`PRISM Commodity Name`) as invalid_categories
FROM `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION` ctg
LEFT JOIN `sco-kb-dev-1a9n.sco_supplier_classification.SPEND_TAXONOMY` tax
  ON ctg.prism_commodity_name_predicted = tax.`PRISM Commodity Name`
WHERE ctg.prism_commodity_name_predicted != 'Unknown';

-- COUPA: Check predicted categories exist in taxonomy
SELECT 
  COUNT(DISTINCT ctg.prism_commodity_name_predicted) as predicted_categories,
  COUNT(DISTINCT tax.`PRISM Commodity Name`) as valid_taxonomy_matches,
  COUNT(DISTINCT ctg.prism_commodity_name_predicted) - COUNT(DISTINCT tax.`PRISM Commodity Name`) as invalid_categories
FROM `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION` ctg
LEFT JOIN `sco-kb-dev-1a9n.sco_supplier_classification.SPEND_TAXONOMY` tax
  ON ctg.prism_commodity_name_predicted = tax.`PRISM Commodity Name`
WHERE ctg.prism_commodity_name_predicted != 'Unknown';


-- =============================================================================
-- 9. Sample Join Test - Tail Supplier Consolidation Preview
-- =============================================================================

-- Test join from invoice line items to IPRO catalog via categorization
-- (Sample query - replace category list with actual values)
SELECT 
  inv.vendor as invoice_vendor,
  line_item.description as invoice_item_description,
  line_item.category as prism_category,
  SAFE_CAST(line_item.amount AS NUMERIC) as invoice_amount,
  cat.vendor_name_normalized as catalog_vendor,
  cat.item_description as catalog_item_description,
  cat.price as catalog_price,
  ctg.prism_prediction_confidence
FROM `sco-kb-dev-1a9n.sco_rage_invoice_extract_ds.invoice_extracts_prepared` inv,
UNNEST(line_items) AS line_item
INNER JOIN `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION` ctg
  ON LOWER(line_item.category) = LOWER(ctg.prism_commodity_name_predicted)
INNER JOIN `sco-kb-dev-1a9n.ai_financial_dlp.IPRO_CATALOG` cat
  ON ctg.davita_item_number = cat.davita_item_number
WHERE LOWER(line_item.category) IN ('dialysis chairs', 'spare parts')  -- Sample categories
  AND ctg.prism_prediction_confidence >= 0.7
LIMIT 20;


-- =============================================================================
-- 10. Stale Categorizations (Older than 30 days)
-- =============================================================================

SELECT 
  'IPRO' as catalog,
  COUNT(*) as stale_count,
  MIN(prism_categorized_at) as oldest_categorization,
  MAX(prism_categorized_at) as newest_stale_categorization
FROM `sco-kb-dev-1a9n.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION`
WHERE prism_categorized_at < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)

UNION ALL

SELECT 
  'COUPA' as catalog,
  COUNT(*) as stale_count,
  MIN(prism_categorized_at) as oldest_categorization,
  MAX(prism_categorized_at) as newest_stale_categorization
FROM `sco-kb-dev-1a9n.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION`
WHERE prism_categorized_at < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY);

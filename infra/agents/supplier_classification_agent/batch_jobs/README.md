# Catalog Categorization Batch Job

Batch job to categorize IPRO_CATALOG and COUPA_CATALOG items with L4 PRISM Commodity Names using LLM.

## Features

- **Batch processing**: 10 items per LLM call (10x faster than sequential)
- **Error recovery**: Saves progress every 1000 items
- **Resume capability**: Skips already-categorized items
- **Audit trail**: Tracks run_id and snapshots for each categorization

## Quick Start

### Local Testing (100 items)

```bash
cd infra/batch_jobs

# Set environment variables
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"

# Install dependencies
pip install -r requirements.txt

# Run categorization
python categorize_catalog_items.py
```

### Modify for Testing

To test on a small sample, edit `get_uncategorized_items()` to add a LIMIT:

```python
query = f"""
    ...
    ORDER BY cat.{id_col}
    LIMIT 100  -- Add this line for testing
"""
```

## How It Works

1. **Load taxonomy**: Fetches valid PRISM categories from SPEND_TAXONOMY grouped by account_code
2. **Find uncategorized items**: LEFT JOIN to categorization tables to find items needing work
3. **Batch categorize**: Groups items by account_code, sends 10 items per LLM call
4. **Write results**: MERGE into categorization tables every 1000 items
5. **Resume on error**: If job fails, re-run and it will skip completed items

## Output Tables

- `sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION`
- `sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION`

## Configuration

Edit constants at top of script:

```python
MODEL_NAME = "gemini-2.0-flash-exp"  # LLM model
BATCH_SIZE = 10                       # Items per LLM call
WRITE_BATCH_SIZE = 1000               # Items per BigQuery write
```

## Monitoring

Check categorization coverage:

```sql
SELECT 
  'IPRO_CATALOG' as catalog,
  COUNT(DISTINCT cat.davita_item_number) as total_items,
  COUNT(DISTINCT ctg.davita_item_number) as categorized_items,
  ROUND(COUNT(DISTINCT ctg.davita_item_number) / COUNT(DISTINCT cat.davita_item_number) * 100, 2) as coverage_pct,
  ROUND(AVG(ctg.prism_prediction_confidence), 3) as avg_confidence
FROM `project.ai_financial_dlp.IPRO_CATALOG` cat
LEFT JOIN `project.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION` ctg
  ON cat.davita_item_number = ctg.davita_item_number;
```

## Reset for Development

```sql
-- WARNING: Deletes all categorizations
DROP TABLE IF EXISTS `project.sco_supplier_classification.IPRO_CATALOG_CATEGORIZATION`;
DROP TABLE IF EXISTS `project.sco_supplier_classification.COUPA_CATALOG_CATEGORIZATION`;

-- Then re-run table creation SQL from plan
```

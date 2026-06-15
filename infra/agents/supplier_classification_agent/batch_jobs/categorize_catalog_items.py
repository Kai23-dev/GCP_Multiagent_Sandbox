"""
Batch categorization of catalog items using LLM.
Assigns PRISM Commodity Names to IPRO_CATALOG and COUPA_CATALOG items.

Features:
- Batches 10 items per LLM call for efficiency
- Saves progress every 1000 items (error recovery)
- Skips already-categorized items (resume capability)
- Tracks run_id for audit trail
"""

import os
from google.cloud import bigquery
from google import genai
from datetime import datetime, timezone
import time
from typing import List
from pydantic import BaseModel
import json

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
bq_client = bigquery.Client(project=PROJECT_ID)

MODEL_NAME = "gemini-2.5-flash"
BATCH_SIZE = 10
CONFIDENCE_THRESHOLD = 0.5
WRITE_BATCH_SIZE = 100
DEBUG_MODE = os.environ.get("DEBUG", "false").lower() == "true"

# Pydantic schema for structured output
class ItemCategorization(BaseModel):
    """Single item categorization result."""
    item_number: int
    category: str
    confidence: float

class BatchCategorizationResult(BaseModel):
    """Batch of item categorizations."""
    categorizations: List[ItemCategorization]

def load_taxonomy_mapping():
    """Load SPEND_TAXONOMY to get valid PRISM categories by account code."""
    query = f"""
    SELECT 
        CAST(Account AS STRING) as account,
        `PRISM Commodity Level 1` as l1,
        `PRISM Commodity Level 2` as l2,
        `PRISM Commodity Level 3` as l3,
        `PRISM Commodity Name` as l4
    FROM `{PROJECT_ID}.sco_supplier_classification.SPEND_TAXONOMY`
    WHERE `PRISM Commodity Name` IS NOT NULL
    """
    
    df = bq_client.query(query).to_dataframe()
    
    taxonomy_by_account = {}
    all_categories = {}  # Deduplicated by L4 name for COUPA (no account_code)
    for _, row in df.iterrows():
        account = str(row['account'])
        entry = {
            'l1': row['l1'],
            'l2': row['l2'],
            'l3': row['l3'],
            'l4': row['l4']
        }
        if account not in taxonomy_by_account:
            taxonomy_by_account[account] = []
        taxonomy_by_account[account].append(entry)
        all_categories[row['l4']] = entry
    
    # Store all categories under empty key for COUPA items (no account_code)
    taxonomy_by_account[''] = list(all_categories.values())
    
    return taxonomy_by_account

def get_uncategorized_items(catalog_table, stale_days=30):
    """Get items needing categorization from specified catalog."""
    
    if catalog_table == 'IPRO_CATALOG':
        id_col = 'davita_item_number'
        categorization_table = 'IPRO_CATALOG_CATEGORIZATION'
        extra_cols = """
            cat.product_category,
            cat.po_category_1,
            cat.po_category_2,
            cat.po_category_3,
            cat.spare_part,
            CAST(cat.account_code AS STRING) as account_code
        """
    else:
        id_col = 'item_id'
        categorization_table = 'COUPA_CATALOG_CATEGORIZATION'
        extra_cols = """
            cat.commodity_name,
            cat.supplier_name,
            '' as account_code
        """
    
    query = f"""
    SELECT 
        cat.{id_col} as item_id,
        cat.item_description,
        {extra_cols}
    FROM `{PROJECT_ID}.ai_financial_dlp.{catalog_table}` cat
    LEFT JOIN `{PROJECT_ID}.sco_supplier_classification.{categorization_table}` ctg
        ON cat.{id_col} = ctg.{id_col}
    WHERE ctg.{id_col} IS NULL
       OR ctg.prism_categorized_at < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {stale_days} DAY)
    ORDER BY cat.{id_col}
    """
    
    return bq_client.query(query).to_dataframe()

def build_categorization_prompt(items, valid_categories, catalog_type):
    """Build LLM prompt for batch categorization with structured output."""
    
    category_list = "\n".join([f"- {cat['l4']}" for cat in valid_categories])
    
    items_text = ""
    for idx, item in enumerate(items, 1):
        if catalog_type == 'IPRO':
            items_text += f"""
Item {idx}:
  Description: {item['item_description']}
  Product Category: {item.get('product_category', 'N/A')}
  PO Categories: {item.get('po_category_1', '')} / {item.get('po_category_2', '')} / {item.get('po_category_3', '')}
  Spare Part: {item.get('spare_part', 'N/A')}
  Account Code: {item.get('account_code', 'N/A')}
"""
        else:
            items_text += f"""
Item {idx}:
  Description: {item['item_description']}
  Commodity: {item.get('commodity_name', 'N/A')}
  Supplier: {item.get('supplier_name', 'N/A')}
"""
    
    prompt = f"""You are categorizing catalog items into PRISM Commodity Names (L4 categories).

VALID CATEGORIES for this account code:
{category_list}

ITEMS TO CATEGORIZE:
{items_text}

INSTRUCTIONS:
1. For each item (by item_number), select the ONE best matching category from the list above
2. If no category fits well, use "Unknown"
3. Provide a confidence score (0.0-1.0) for each prediction
4. Consider all available metadata (description, categories, spare part flag)
5. Return results in the structured format with item_number, category, and confidence

Be precise. Only use exact category names from the list above.
"""
    
    return prompt

def categorize_items_batch(items, taxonomy_mapping, catalog_type, debug=False):
    """Categorize a batch of items using LLM with structured output."""
    account_code = str(items[0].get('account_code', ''))
    valid_categories = taxonomy_mapping.get(account_code, [])
    
    if not valid_categories:
        if debug:
            print(f"  DEBUG - No valid categories for account {account_code}")
        return [{"category": "Unknown", "confidence": 0.0} for _ in items]
    
    if debug:
        print(f"  DEBUG - Account {account_code} has {len(valid_categories)} valid categories")
        print(f"  DEBUG - Sample categories: {[c['l4'] for c in valid_categories[:3]]}")
    
    prompt = build_categorization_prompt(items, valid_categories, catalog_type)
    
    if debug:
        print(f"  DEBUG - Prompt length: {len(prompt)} chars")
    
    try:
        # Use structured output with Pydantic schema (google-genai SDK)
        response = genai_client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=4096,
                response_mime_type="application/json",
                response_schema=BatchCategorizationResult
            )
        )
        
        if debug:
            print(f"  DEBUG - Raw JSON response: {response.text[:300]}")
        
        # Parse structured response via Pydantic
        result = BatchCategorizationResult.model_validate_json(response.text)
        
        if debug:
            print(f"  DEBUG - Parsed {len(result.categorizations)} categorizations")
            for cat in result.categorizations[:3]:
                print(f"  DEBUG - Item {cat.item_number}: {cat.category} | {cat.confidence}")
        
        # Convert to expected format
        predictions = []
        for cat in result.categorizations:
            predictions.append({
                "category": cat.category,
                "confidence": cat.confidence
            })
        
        # Ensure we have predictions for all items
        while len(predictions) < len(items):
            predictions.append({"category": "Unknown", "confidence": 0.0})
        
        return predictions[:len(items)]
    
    except Exception as e:
        print(f"  Error calling LLM: {e}")
        if debug:
            import traceback
            print(f"  DEBUG - Full traceback:\n{traceback.format_exc()}")
        return [{"category": "Unknown", "confidence": 0.0} for _ in items]

def write_predictions_to_bq(predictions, catalog_table, run_id):
    """Write categorization predictions to categorization tables."""
    if not predictions:
        return
    
    if catalog_table == 'IPRO_CATALOG':
        categorization_table = 'IPRO_CATALOG_CATEGORIZATION'
        id_col = 'davita_item_number'
    else:
        categorization_table = 'COUPA_CATALOG_CATEGORIZATION'
        id_col = 'item_id'
    
    # Build rows for temp table - use JSON escaping to avoid SQL injection
    import json
    
    rows_to_insert = []
    for pred in predictions:
        if catalog_table == 'IPRO_CATALOG':
            rows_to_insert.append({
                'item_id': pred['item_id'],
                'category': pred['category'],
                'confidence': pred['confidence'],
                'model': MODEL_NAME,
                'run_id': run_id,
                'description': pred.get('description', ''),
                'account_code': str(pred.get('account_code', ''))
            })
        else:
            rows_to_insert.append({
                'item_id': pred['item_id'],
                'category': pred['category'],
                'confidence': pred['confidence'],
                'model': MODEL_NAME,
                'run_id': run_id,
                'description': pred.get('description', '')
            })
    
    # Use a temp table approach to avoid SQL injection issues
    temp_table_id = f"{PROJECT_ID}.sco_supplier_classification._temp_categorization_{run_id.replace('-', '_')}"
    
    # Load data into temp table
    from google.cloud.bigquery import LoadJobConfig, WriteDisposition
    import pandas as pd
    
    df = pd.DataFrame(rows_to_insert)
    
    job_config = LoadJobConfig(
        write_disposition=WriteDisposition.WRITE_TRUNCATE,
    )
    
    try:
        # Load to temp table
        load_job = bq_client.load_table_from_dataframe(df, temp_table_id, job_config=job_config)
        load_job.result()
        
        # Now MERGE from temp table
        if catalog_table == 'IPRO_CATALOG':
            merge_query = f"""
            MERGE `{PROJECT_ID}.sco_supplier_classification.{categorization_table}` T
            USING `{temp_table_id}` S
            ON T.davita_item_number = S.item_id
            WHEN MATCHED THEN UPDATE SET
                prism_commodity_name_predicted = S.category,
                prism_prediction_confidence = S.confidence,
                prism_prediction_model = S.model,
                prism_categorized_at = CURRENT_TIMESTAMP(),
                categorization_run_id = S.run_id,
                item_description_snapshot = S.description,
                account_code_snapshot = S.account_code
            WHEN NOT MATCHED THEN INSERT (
                davita_item_number,
                prism_commodity_name_predicted,
                prism_prediction_confidence,
                prism_prediction_model,
                prism_categorized_at,
                categorization_run_id,
                item_description_snapshot,
                account_code_snapshot
            ) VALUES (
                S.item_id,
                S.category,
                S.confidence,
                S.model,
                CURRENT_TIMESTAMP(),
                S.run_id,
                S.description,
                S.account_code
            )
            """
        else:
            merge_query = f"""
            MERGE `{PROJECT_ID}.sco_supplier_classification.{categorization_table}` T
            USING `{temp_table_id}` S
            ON T.item_id = S.item_id
            WHEN MATCHED THEN UPDATE SET
                prism_commodity_name_predicted = S.category,
                prism_prediction_confidence = S.confidence,
                prism_prediction_model = S.model,
                prism_categorized_at = CURRENT_TIMESTAMP(),
                categorization_run_id = S.run_id,
                item_description_snapshot = S.description
            WHEN NOT MATCHED THEN INSERT (
                item_id,
                prism_commodity_name_predicted,
                prism_prediction_confidence,
                prism_prediction_model,
                prism_categorized_at,
                categorization_run_id,
                item_description_snapshot
            ) VALUES (
                S.item_id,
                S.category,
                S.confidence,
                S.model,
                CURRENT_TIMESTAMP(),
                S.run_id,
                S.description
            )
            """
        
        bq_client.query(merge_query).result()
        
        # Clean up temp table
        bq_client.delete_table(temp_table_id, not_found_ok=True)
        
    except Exception as e:
        print(f"  Error writing to BigQuery: {e}")
        # Try to clean up temp table
        try:
            bq_client.delete_table(temp_table_id, not_found_ok=True)
        except:
            pass
        raise

def categorize_catalog(catalog_table, catalog_type):
    """Main categorization flow for a catalog."""
    print(f"\n{'='*60}")
    print(f"Categorizing {catalog_table}")
    print(f"{'='*60}")
    
    run_id = f"{catalog_table}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    print(f"Run ID: {run_id}")
    
    taxonomy_mapping = load_taxonomy_mapping()
    print(f"Loaded {len(taxonomy_mapping)} account codes from SPEND_TAXONOMY")
    
    items_df = get_uncategorized_items(catalog_table)
    print(f"Found {len(items_df)} items needing categorization")
    
    if len(items_df) == 0:
        print("No items to categorize. Done!")
        return
    
    if catalog_table == 'IPRO_CATALOG':
        items_by_account = items_df.groupby('account_code')
    else:
        items_by_account = [('all', items_df)]
    
    all_predictions = []
    processed_count = 0
    total_items = len(items_df)
    
    for account_code, group in items_by_account:
        print(f"\nProcessing account {account_code}: {len(group)} items")
        
        items_list = group.to_dict('records')
        
        for i in range(0, len(items_list), BATCH_SIZE):
            batch = items_list[i:i+BATCH_SIZE]
            
            try:
                # Enable debug for first batch only
                debug = DEBUG_MODE and processed_count == 0
                predictions = categorize_items_batch(batch, taxonomy_mapping, catalog_type, debug=debug)
                
                for item, pred in zip(batch, predictions):
                    prediction_record = {
                        'item_id': item['item_id'],
                        'category': pred['category'],
                        'confidence': pred['confidence'],
                        'description': item.get('item_description', '')
                    }
                    
                    if catalog_table == 'IPRO_CATALOG':
                        prediction_record['account_code'] = item.get('account_code', '')
                    
                    all_predictions.append(prediction_record)
                
                processed_count += len(batch)
                print(f"  Progress: {processed_count}/{total_items} items ({100*processed_count/total_items:.1f}%)", end='\r')
                
                time.sleep(0.5)
                
                if len(all_predictions) >= WRITE_BATCH_SIZE:
                    print(f"\n  Writing {len(all_predictions)} predictions to BigQuery...")
                    write_predictions_to_bq(all_predictions, catalog_table, run_id)
                    all_predictions = []
                
            except Exception as e:
                print(f"\n  Error processing batch: {e}")
                if all_predictions:
                    print(f"  Saving {len(all_predictions)} predictions before continuing...")
                    try:
                        write_predictions_to_bq(all_predictions, catalog_table, run_id)
                        all_predictions = []
                    except:
                        pass
                continue
    
    if all_predictions:
        print(f"\n  Writing final {len(all_predictions)} predictions to BigQuery...")
        write_predictions_to_bq(all_predictions, catalog_table, run_id)
    
    print(f"\n\nCompleted {catalog_table}: {processed_count} items categorized")
    print(f"Run ID: {run_id}")

def main():
    """Main entry point."""
    print("Starting catalog categorization job...")
    print(f"Project: {PROJECT_ID}")
    print(f"Model: {MODEL_NAME}")
    print(f"Batch size: {BATCH_SIZE} items per LLM call")
    print(f"Write batch size: {WRITE_BATCH_SIZE} items per BigQuery write")
    
    categorize_catalog('IPRO_CATALOG', 'IPRO')
    categorize_catalog('COUPA_CATALOG', 'COUPA')
    
    print("\n" + "="*60)
    print("Categorization complete!")
    print("="*60)

if __name__ == "__main__":
    main()

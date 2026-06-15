Table Description
Table Name: COUPA_CATALOG_CATEGORIZATION
Record Count: ~11,526 (grows with catalog)
Complete Description:
This table contains LLM-generated PRISM commodity categorizations for COUPA catalog items. Each record represents a categorization prediction linking a COUPA catalog item to a PRISM Commodity Name from the SPEND_TAXONOMY. The categorizations are generated using Gemini 2.5 Flash with structured output to ensure consistent classification across the full taxonomy (all 1,119+ L4 categories). Unlike IPRO items which are categorized using account_code-specific taxonomy subsets, COUPA items are categorized against the complete taxonomy since they lack account_code mappings. This table enables tail supplier consolidation analysis by allowing queries to find catalog alternatives from preferred suppliers for items currently purchased from tail suppliers. The table includes confidence scores, model version tracking, and snapshots of item descriptions at categorization time for audit purposes. Records are updated when new items are added to the catalog or when existing categorizations become stale (>30 days old).

________________________________________
Column Description Schema
item_id: This is the Primary Key for the table and Foreign Key to COUPA_CATALOG. The unique identifier for the catalog item. Sample Data: (various item IDs from COUPA system)
prism_commodity_name_predicted: The predicted PRISM Commodity Name (L4 category) from SPEND_TAXONOMY. This is the LLM's categorization of the item. Sample Data: Enterprise IT Annual Software Maintenance - OpEx, Printer Supplies (Ink & Toner), Desktops
prism_prediction_confidence: The confidence score (0.0-1.0) of the LLM's categorization prediction. Higher values indicate stronger confidence. Sample Data: 1.0, 0.95, 0.8
prism_prediction_model: The LLM model used to generate the categorization. Sample Data: gemini-2.5-flash
prism_categorized_at: The timestamp when the categorization was generated. Sample Data: 2026-03-11 04:05:44.913705 UTC
categorization_run_id: The unique identifier for the categorization batch run, used for tracking and auditing. Format: COUPA_CATALOG_YYYYMMDD_HHMMSS. Sample Data: COUPA_CATALOG_20260311_040517
item_description_snapshot: A snapshot of the item description at the time of categorization, preserved for audit trail. Sample Data: N/A, TLP OptiPlex 7010 Micro with WiFi

Join to other tables with these considerations in mind:
COUPA Catalog Integration: Join item_id to COUPA_CATALOG.item_id to get complete catalog item details including supplier, commodity classification, and pricing.
Taxonomy Integration: Join prism_commodity_name_predicted to SPEND_TAXONOMY.PRISM Commodity Name to get the full hierarchical taxonomy (L1, L2, L3) and account mapping.
Tail Supplier Consolidation: Use this table to find catalog alternatives for invoice line items by joining invoice_extracts_prepared.line_items.category (lowercased PRISM Commodity Name) to prism_commodity_name_predicted, then joining to COUPA_CATALOG for pricing and supplier information.
Confidence Filtering: Filter by prism_prediction_confidence >= 0.5 to exclude low-confidence predictions from analysis. Higher thresholds (0.8-0.9) can be used for critical procurement decisions. Note that COUPA items may have lower average confidence than IPRO items due to broader taxonomy matching.
Model Version Tracking: Use prism_prediction_model to track which LLM version generated categorizations, enabling analysis of model performance over time.
Audit Trail: Use categorization_run_id to identify which batch run generated specific categorizations, and item_description_snapshot to verify categorizations remain valid if source descriptions change.
Recategorization Analysis: Compare prism_categorized_at to current timestamp to identify stale categorizations that may need refresh, especially for items with changing descriptions or new taxonomy additions.
Savings Opportunity Analysis: Join to invoice line items via PRISM Commodity Name to compare tail supplier pricing against preferred supplier catalog pricing for the same commodity categories.
Data Quality Considerations: Some COUPA items may have poor source data quality (e.g., item_id containing descriptions, "N/A" descriptions), which can result in "Unknown" categorizations or lower confidence scores.

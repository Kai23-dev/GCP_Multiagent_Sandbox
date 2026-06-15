Table Description
Table Name: IPRO_CATALOG_CATEGORIZATION
Record Count: ~9,734 (grows with catalog)
Complete Description:
This table contains LLM-generated PRISM commodity categorizations for IPRO catalog items. Each record represents a categorization prediction linking an IPRO catalog item to a PRISM Commodity Name from the SPEND_TAXONOMY. The categorizations are generated using Gemini 2.5 Flash with structured output to ensure consistent classification. This table enables tail supplier consolidation analysis by allowing queries to find catalog alternatives from preferred suppliers for items currently purchased from tail suppliers. The table includes confidence scores, model version tracking, and snapshots of item descriptions at categorization time for audit purposes. Records are updated when new items are added to the catalog or when existing categorizations become stale (>30 days old).

________________________________________
Column Description Schema
davita_item_number: This is the Primary Key for the table and Foreign Key to IPRO_CATALOG. The unique identifier for the catalog item. Sample Data: 1046408, 1046416, 1046420
prism_commodity_name_predicted: The predicted PRISM Commodity Name (L4 category) from SPEND_TAXONOMY. This is the LLM's categorization of the item. Sample Data: Acid Concentrate, Canister, Spare Parts - Assembly
prism_prediction_confidence: The confidence score (0.0-1.0) of the LLM's categorization prediction. Higher values indicate stronger confidence. Sample Data: 1.0, 0.95, 0.9
prism_prediction_model: The LLM model used to generate the categorization. Sample Data: gemini-2.5-flash
prism_categorized_at: The timestamp when the categorization was generated. Sample Data: 2026-03-11 04:05:15.111306 UTC
categorization_run_id: The unique identifier for the categorization batch run, used for tracking and auditing. Format: IPRO_CATALOG_YYYYMMDD_HHMMSS. Sample Data: IPRO_CATALOG_20260311_040440
item_description_snapshot: A snapshot of the item description at the time of categorization, preserved for audit trail. Sample Data: ACID CONCENTRATE, DRY GRANUFLO 45X 2K 2.0Ca 1Mg 100 Dextrose 16.5 GALLON (CASE) FMC (0FD2201-3B)
account_code_snapshot: A snapshot of the GL account code at the time of categorization, used to determine which taxonomy categories were available for matching. Sample Data: 6604, 6800, 6424

Join to other tables with these considerations in mind:
IPRO Catalog Integration: Join davita_item_number to IPRO_CATALOG.davita_item_number to get complete catalog item details including vendor, pricing, and product categories.
Taxonomy Integration: Join prism_commodity_name_predicted to SPEND_TAXONOMY.PRISM Commodity Name to get the full hierarchical taxonomy (L1, L2, L3) and account mapping.
Tail Supplier Consolidation: Use this table to find catalog alternatives for invoice line items by joining invoice_extracts_prepared.line_items.category (lowercased PRISM Commodity Name) to prism_commodity_name_predicted, then joining to IPRO_CATALOG for pricing and vendor information.
Confidence Filtering: Filter by prism_prediction_confidence >= 0.5 to exclude low-confidence predictions from analysis. Higher thresholds (0.8-0.9) can be used for critical procurement decisions.
Model Version Tracking: Use prism_prediction_model to track which LLM version generated categorizations, enabling analysis of model performance over time.
Audit Trail: Use categorization_run_id to identify which batch run generated specific categorizations, and item_description_snapshot to verify categorizations remain valid if source descriptions change.
Recategorization Analysis: Compare prism_categorized_at to current timestamp to identify stale categorizations that may need refresh, especially for items with changing descriptions or new taxonomy additions.
Savings Opportunity Analysis: Join to invoice line items via PRISM Commodity Name to compare tail supplier pricing against preferred supplier catalog pricing for the same commodity categories.

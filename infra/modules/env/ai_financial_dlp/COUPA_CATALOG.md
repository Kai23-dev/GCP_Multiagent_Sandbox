Table Description
Table Name: COUPA_CATALOG
Record Count: Small
Complete Description:
This table serves as the master repository for all catalog items available through the Coupa procurement system. Each record represents a specific catalog item with its associated supplier, commodity classification, and catalog details. This table is essential for catalog management, supplier analysis, commodity classification, spend analysis, and procurement optimization. It provides the foundation for guided buying, contract management, and supplier relationship management within the Coupa platform.
________________________________________

Column Description Schema
item_id: This is the Primary Key for the table. It is the unique system-generated identifier for each catalog item. Sample Data: 4463, 4507, 4536
supplier_id: Foreign Key to supplier master tables. The unique identifier for the supplier offering this item. Sample Data: 4544
commodity_id: Foreign Key to commodity classification tables. The unique identifier for the commodity category. Sample Data: 438
catalog_id: The catalog identifier for grouping related items. Sample Data: 0
item_description: The detailed description of the catalog item. Sample Data: Snow Removal Services
commodity_name: The name of the commodity category with code. Sample Data: Snow Removal (7820)
commodity_custom_field_3: Custom field for commodity classification - department or category code. Sample Data: 7820 - R&M Grounds
commodity_custom_field_4: Custom field for commodity classification - subcategory or additional code. Sample Data: 00000 - N/A
supplier_name: The name of the supplier offering this catalog item. Sample Data: BT LANDSCAPING AND SONS INC
supplier_name_normalized: The normalized version of the supplier name for consistent searching and matching. Sample Data: BT LANDSCAPING AND SONS INC
catalog_start_date: The date when this catalog item becomes active and available for purchase. Sample Data: 2025-01-01
catalog_end_date: The date when this catalog item becomes inactive and unavailable for purchase. Sample Data: 2025-12-31
source_system: The source system from which the catalog data originated. Sample Data: COUPA
created_at: The timestamp when this catalog item record was created. Sample Data: 2026-02-10 06:18:14.281298 UTC
updated_at: The timestamp when this catalog item record was last updated. Sample Data: 2026-02-10 06:18:17.958953 UTC

Join to other tables with these considerations in mind:
Order Integration: Use catalog information to join with COUPA_ORDERS for catalog-based purchasing analysis and compliance tracking.
Invoice Integration: Use catalog details to join with COUPA_INVOICES for catalog item billing validation and price verification.
Supplier Integration: Use supplier_id to join with supplier information for catalog governance and supplier relationship management.
Compliance Analysis: Use catalog information to track maverick spending and catalog adoption rates across the organization.
Spend Analysis: Combine catalog data with order and invoice information for comprehensive spend analysis by catalog category.
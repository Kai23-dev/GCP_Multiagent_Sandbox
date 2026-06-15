Table Description
Table Name: IPRO_CATALOG
Record Count: Small
Complete Description:
This table serves as the master repository for the iProcurement catalog items, representing a comprehensive product catalog specifically designed for healthcare and dialysis operations. Each record represents a specific catalog item with detailed product information, pricing, vendor details, categorization, and inventory management attributes. This table is essential for procurement management, supplier relationship management, inventory control, cost analysis, and healthcare supply chain optimization. The catalog includes medical supplies, dialysis equipment, spare parts, and specialized healthcare products with detailed specifications and vendor information.
________________________________________

Column Description Schema
davita_item_number: This is the Primary Key for the table. It is the unique item number used to identify each catalog item. Sample Data: 1046420, 1055177, 1055196
item_description: The detailed description of the catalog item including specifications and usage information. Sample Data: ACID CONCENTRATE, LIQUID 45X 3K 2.5Ca 1Mg 100 DEXTROSE 55GAL DRUM FMC, BOARD
model_number: The model number of the product or equipment. Sample Data: 2008K, 2008K2, 2008H
manufacturer_part_number: The manufacturer's part number for the item. Sample Data: M31451, 190100, 370048
price: The unit price of the item in the specified currency. Sample Data: 197.46, 100, 15
unit_of_measure: The unit of measure for pricing and ordering (e.g., DRUM, EACH, GALLON). Sample Data: DRUM, EACH
pack_factor: The pack factor for the item indicating quantity per package. Sample Data: 55, 1
pack_factor_conversion: The conversion unit for the pack factor (e.g., GALLON, EACH). Sample Data: GALLON, EACH
ndc_code: The National Drug Code for pharmaceutical items. Sample Data: N/A
ndc_unit_of_use: The unit of use for NDC-coded items. Sample Data: N/A
weight: The weight of the item. Sample Data: N/A
weight_code: The weight unit code (e.g., LB, KG). Sample Data: N/A
po_category_1: The first level purchase order category classification. Sample Data: Med Supplies, Dialysis Equip
po_category_2: The second level purchase order category classification. Sample Data: Dialysate, Dialysis Machines
po_category_3: The third level purchase order category classification. Sample Data: Acid Con 3K, Electrical
po_category_4: The fourth level purchase order category classification. Sample Data: DVA, BIO
product_category: The product category classification. Sample Data: ACID CONCENTRATE, SPARE PARTS - BOARD, CABLE
updated_product_category: The updated product category classification. Sample Data: ACID CONCENTRATE, SPARE PARTS - BOARD, CABLE
vendor_name: The name of the supplier for this item. Sample Data: FRESENIUS USA INC, NIPRO TECHNICAL SOLUTIONS INC
vendor_name_normalized: The normalized version of the vendor name for consistent searching and matching. Sample Data: FRESENIUS USA INC, NIPRO TECHNICAL SOLUTIONS INC
vendor_site: The vendor site or location code. Sample Data: PROC-GURNEE, PROC-MESA
account_code: The account code for financial tracking and GL posting. Sample Data: 6604, 6800
modality: The modality or department classification (e.g., ALL for all modalities). Sample Data: ALL
pfbc: The PFBC code or classification. Sample Data: N/A
effective_date_from: The effective start date for the item pricing and availability. Sample Data: 2025-01-01
effective_date_to: The effective end date for the item pricing and availability. Sample Data: N/A
inventoriable: Boolean flag (Y/N) indicating if the item is inventoriable. Sample Data: N
countable: Boolean flag (Y/N) indicating if the item is countable for inventory purposes. Sample Data: N
green_flag: The green flag status or priority indicator. Sample Data: B
replacement_item_number: The item number that replaces this item. Sample Data: 1001892, 1007933, 1007958
spare_part: Boolean flag (Y/N) indicating if this is a spare part. Sample Data: N, Y
image_file_name: The filename of the product image. Sample Data: 220061e.jpg, 221029.jpg, 221049.jpg
professional_logo: Boolean flag (Y/N) indicating if professional logo is available. Sample Data: N
price_change_comment: Comments regarding price changes or adjustments. Sample Data: N/A
source_system: The source system that created or manages this catalog item. Sample Data: IPRO
created_at: The timestamp when this catalog item record was created. Sample Data: 2026-02-10 06:18:14.400291 UTC
updated_at: The timestamp when this catalog item record was last updated. Sample Data: 2026-02-10 06:18:18.010748 UTC

Join to other tables with these considerations in mind:
Ipro Orders Integration: Use davita_item_number to join to IPRO_ORDERS.davita_item_number for complete transaction analysis and business context.
Order Integration: Use davita_item_number to join to IPRO_ORDERS for order history, demand analysis, and usage pattern tracking.
Vendor Integration: Use vendor_name and vendor_id to join to AP_SUPPLIERS for supplier information, contract terms, and performance analysis.
Product Analysis: Combine manufacturer, product_category, and category hierarchy for product portfolio analysis and sourcing optimization.
Demand Analysis: Use order integration to analyze demand patterns, seasonal variations, and inventory planning requirements.
Pricing Analysis: Use unit_price from order data to analyze price variations, supplier comparisons, and cost optimization opportunities.
Category Management: Use category1, category2, and category3 for product categorization, spend analysis, and strategic sourcing initiatives.
Catalog Management: Analyze product information completeness, specification accuracy, and catalog data quality metrics.
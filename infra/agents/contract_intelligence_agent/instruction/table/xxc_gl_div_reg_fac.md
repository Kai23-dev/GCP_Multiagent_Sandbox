# XXC_GL_DIV_REG_FAC

**Dataset:** ai_financial_dlp
**Purpose:** Facility hierarchy - **CRITICAL for facility-level contract pricing**

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| **facility_id** | STRING | Facility ID (PK) | **Match to contract facilities** |
| facility_description | STRING | Facility description | Display name |
| facility_common_name | STRING | Common name | Alternative name |
| **palmer_vp** | STRING | Palmer VP code | **RBAC filtering** |
| palmer_vp_desc | STRING | Palmer VP description | Display |
| group_vp | STRING | Group VP code | Grouping |
| **division** | STRING | Division code | **Regional filtering** |
| division_desc | STRING | Division description | Display |
| **region** | STRING | Region code | **Regional filtering** |
| region_desc | STRING | Region description | Display |
| facility_type | STRING | Facility type | Type filtering |
| legal_entity | STRING | Legal entity | Entity filtering |
| is_active | BOOLEAN | Active status | Active filtering |
| facility_city | STRING | City | Location |
| facility_state | STRING | State | Location |

## Sample Query

```sql
-- Get active facilities by region
SELECT
    facility_id,
    facility_common_name,
    palmer_vp,
    division,
    region,
    facility_type
FROM ai_financial_dlp.XXC_GL_DIV_REG_FAC
WHERE is_active = TRUE
  AND region = 'WEST'
ORDER BY facility_common_name
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| facility_id | 05487, 12345, 00609 |
| facility_common_name | DaVita Clinic Phoenix; DaVita Dallas North |
| palmer_vp | PALMER_WEST, PALMER_CENTRAL |
| division | WEST, CENTRAL, EAST |
| region | ARIZONA, TEXAS, FLORIDA |
| facility_type | CLINIC, HOME, ACUTE |

## Join Considerations

- **To COUPA_INVOICES**: Join on `facility_number` (may need normalization)
- **To COUPA_ORDERS**: Join on `facility_number`
- **To IPRO_ORDERS**: Join on `facility_id`
- **Contract Matching**: Match `facility_id` to facility-specific contract pricing
- **RBAC**: Filter by `palmer_vp` or `division` for role-based access

## Contract Pricing Use Cases

```sql
-- Facility Services Agreement pricing check
-- Contract: "$2,000/month per center"
SELECT
    f.facility_id,
    f.facility_common_name,
    c.supplier_name,
    SUM(c.invoice_amount) as total_invoiced,
    COUNT(DISTINCT EXTRACT(MONTH FROM c.invoice_date)) as months_billed,
    SUM(c.invoice_amount) / COUNT(DISTINCT EXTRACT(MONTH FROM c.invoice_date)) as avg_per_month
FROM ai_financial_dlp.XXC_GL_DIV_REG_FAC f
JOIN ai_financial_dlp.COUPA_INVOICES c ON f.facility_id = c.facility_number
WHERE c.supplier_name_normalized LIKE '%CLEANING%'
  AND f.is_active = TRUE
GROUP BY f.facility_id, f.facility_common_name, c.supplier_name
```

## Notes

- **RBAC Critical**: Use `palmer_vp`, `division`, `region` for access control
- **Facility-Level Contracts**: Some contracts specify per-facility pricing
- `facility_id` may be in invoices as `facility_number` (different naming)
- Filter `is_active = TRUE` for active facilities only
- Contains both DaVita Clinics and administrative facilities

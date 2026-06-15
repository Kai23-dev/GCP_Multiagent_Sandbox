# CONTRACT_METADATA

**Dataset:** ai_financial_dlp
**Purpose:** Ironclad contract metadata — dates, status, renewal info, supplier mapping

## Key Columns

| Column | Type | Description | CIA Use |
|--------|------|-------------|---------|
| ironclad_id | STRING | Ironclad contract ID (e.g., IC-66899) | Unique identifier |
| contract_type | STRING | enterpriseAgreements, facilityServicesAgreement, mnda, etc. | Contract classification |
| contract_name | STRING | Full contract name | Display |
| **counterparty_name** | STRING | Supplier/vendor name | **Primary lookup key** |
| agreement_date | DATE | Date agreement was signed | Reference |
| **effective_date** | DATE | Contract start date | **Contract start** |
| **expiration_date** | DATE | Contract end date (NULL if not set) | **Contract expiry** |
| anniversary_date | DATE | Anniversary/renewal trigger date | Renewal tracking |
| **renewal_type** | STRING | Auto-Renew, Evergreen, Manual | **Renewal behavior** |
| renewal_term_length | STRING | ISO 8601 duration (P1Y = 1 year) | Renewal period |
| initial_term_length | STRING | ISO 8601 duration (P2Y = 2 years) | Original term |
| contract_value_amount | FLOAT64 | Total contract value | Financial analysis |
| contract_value_currency | STRING | Currency (USD) | Financial analysis |
| **contract_status** | STRING | active, inactive, expiring | **Status filter** |
| remaining_duration | STRING | ISO 8601 duration (P135D = 135 days) | Time remaining |
| hierarchy_type | STRING | Master, Order Form | Contract hierarchy |
| agreement_type | STRING | Services Agreement, NDA, etc. | Classification |
| business_group | STRING | Business unit | Organizational mapping |
| last_updated | TIMESTAMP | Last metadata update | Freshness check |
| **signed_copy_filename** | STRING | D1.LF.XXXXX.pdf filename from Ironclad attachment | **RAG source matching** |

## Sample Query

```sql
-- Find contracts for a supplier, latest effective_date first (governing contract = first row)
SELECT
    ironclad_id,
    contract_name,
    counterparty_name,
    contract_type,
    effective_date,
    expiration_date,
    renewal_type,
    contract_status,
    signed_copy_filename
FROM ai_financial_dlp.CONTRACT_METADATA
WHERE UPPER(counterparty_name) LIKE '%<SUPPLIER_NAME>%'
ORDER BY
    CASE WHEN contract_status IN ('active', 'expiring') THEN 0 ELSE 1 END,
    effective_date DESC
```

## Sample Data

| Column | Sample Values |
|--------|---------------|
| counterparty_name | DocuSign, Inc.; Medline Industries, LP; Scioto, LLC |
| signed_copy_filename | D1.LF.00111629.pdf, D1.LF.00102586.pdf, NULL |
| contract_type | enterpriseAgreements, facilityServicesAgreement, mnda |
| effective_date | 2024-01-01, 2025-03-18, 2026-07-01 |
| expiration_date | 2026-06-30, 2027-03-18, NULL |
| renewal_type | Auto-Renew, Evergreen, Manual |
| contract_status | active, inactive, expiring |
| remaining_duration | P135D, P365D, P30D |

## Join Considerations

- **To COUPA_INVOICES**: Match on `UPPER(counterparty_name) LIKE UPPER(supplier_name_normalized)`
- **To AP_SUPPLIERS**: Match on `UPPER(counterparty_name) LIKE UPPER(supplier_name)`
- **To XXC_GL_SUMMARY**: Match on `UPPER(counterparty_name) LIKE UPPER(vendor_name)`
- **Fuzzy matching required**: counterparty_name may differ slightly from spend table supplier names

## Notes

- **Source**: Ironclad CLM metadata (8 contract types)
- ~20K contracts total; ~10K have explicit expiration_date
- All contracts have contract_status from Ironclad
- **Evergreen contracts**: No expiration_date but contract_status = 'active'
- **Auto-Renew**: Check renewal_term_length for effective renewal period
- Use `ssi_get_contract_dates` specialized tool instead of raw SQL when possible

-- Row count check
SELECT COUNT(*) AS row_count
FROM `gp-ct-sbox-con-sbp0i2-eyenterp.ai_financial_dlp.XXC_GL_SUMMARY`;

-- Monthly vendor spend trend
SELECT
  period_name,
  vendor_name,
  SUM(amount) AS total_spend
FROM `gp-ct-sbox-con-sbp0i2-eyenterp.ai_financial_dlp.XXC_GL_SUMMARY`
GROUP BY period_name, vendor_name
ORDER BY period_name, total_spend DESC;

-- Category-wise spend
SELECT
  category,
  SUM(amount) AS total_spend
FROM `gp-ct-sbox-con-sbp0i2-eyenterp.ai_financial_dlp.XXC_GL_SUMMARY`
GROUP BY category
ORDER BY total_spend DESC;

-- Top vendors by spend
SELECT
  vendor_name,
  SUM(amount) AS total_spend
FROM `gp-ct-sbox-con-sbp0i2-eyenterp.ai_financial_dlp.XXC_GL_SUMMARY`
GROUP BY vendor_name
ORDER BY total_spend DESC
LIMIT 10;

-- Create Financial Leakage sandbox table
CREATE TABLE IF NOT EXISTS `gp-ct-sbox-con-sbp0i2-eyenterp.ai_financial_dlp.XXC_GL_SUMMARY_FINANCIAL_LEAKAGE_SANDBOX` AS
SELECT
  vendor_name,
  amount,
  category,
  super_category,
  commodity,
  effective_date,
  period_name,
  CONCAT(category, " - ", vendor_name) AS line_description,
  CASE
    WHEN amount > 10000 THEN "PO-" || CAST(ROW_NUMBER() OVER () AS STRING)
    ELSE NULL
  END AS po_number,
  "CHK-" || CAST(ROW_NUMBER() OVER () AS STRING) AS check_id
FROM `gp-ct-sbox-con-sbp0i2-eyenterp.ai_financial_dlp.XXC_GL_SUMMARY`;

-- Leakage risk classification
SELECT
  vendor_name,
  amount,
  category,
  commodity,
  line_description,
  po_number,
  CASE
    WHEN LOWER(line_description) LIKE "%gift card%" THEN "High Risk"
    WHEN LOWER(line_description) LIKE "%airpods%" THEN "High Risk"
    WHEN po_number IS NULL AND amount > 1000 THEN "High Risk"
    WHEN LOWER(line_description) LIKE "%coffee machine%" THEN "Medium Risk"
    WHEN LOWER(line_description) LIKE "%streaming%" THEN "Medium Risk"
    WHEN po_number IS NULL AND amount > 500 THEN "Medium Risk"
    ELSE "Low Risk"
  END AS leakage_risk
FROM `gp-ct-sbox-con-sbp0i2-eyenterp.ai_financial_dlp.XXC_GL_SUMMARY_FINANCIAL_LEAKAGE_SANDBOX`
ORDER BY amount DESC;
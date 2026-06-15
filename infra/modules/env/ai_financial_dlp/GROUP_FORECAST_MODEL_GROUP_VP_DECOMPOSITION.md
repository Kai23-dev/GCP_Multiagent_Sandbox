Table Description
Table Name: GROUP_FORECAST_MODEL_GROUP_VP_DECOMPOSITION
Record Count: Very Small
Complete Description:
This table serves as the repository for time series decomposition results for Group VP forecast models, representing the breakdown of historical time series data into trend, seasonal, holiday, and residual components. Each record represents a specific time point with its decomposed components for a particular Group VP group. This table is essential for time series analysis, forecast model evaluation, seasonal pattern identification, holiday impact assessment, and understanding the underlying patterns in financial data for predictive modeling. The low record count indicates this contains processed analytical results rather than raw transactional data.
________________________________________

Column Description Schema
group_vp: This is the Primary Key for the table. It represents the Group VP group identifier for the forecast model. Sample Data: GV009
time_series_timestamp: The timestamp for the time series data point. Sample Data: 2025-10-01 00:00:00.000000 UTC, 2025-10-02 00:00:00.000000 UTC, 2025-10-03 00:00:00.000000 UTC
time_series_data: The actual time series data value at the given timestamp. Sample Data: 48372950.37, 13135082.96, 384969.64
trend: The trend component extracted from the time series decomposition. Sample Data: 65093683.4166129
seasonal_period_yearly: The seasonal component for yearly periodicity extracted from the time series. Sample Data: N/A
holiday_effect: The holiday effect component extracted from the time series decomposition. Sample Data: N/A
residual: The residual component (remaining variation) after removing trend, seasonal, and holiday effects. Sample Data: -16720733.046612903, -51958600.4566129, -64708713.7766129

Join to other tables with these considerations in mind:
Organizational Integration: Use group identifier to join with XXC_GL_DIV_REG_FAC for organizational hierarchy, performance analysis, and regional comparison.
Financial Integration: Use forecast results to join with XXC_GL_SUMMARY for comparing predicted vs actual financial performance and variance analysis.
Time Series Integration: Use timestamp fields to join with financial transaction tables for forecast validation, accuracy measurement, and model improvement.
Decomposition Analysis: Use decomposition results to join with actual financial data for trend analysis and pattern validation.
Model Performance: Combine forecast data with actual results to analyze model accuracy, identify improvement opportunities, and support forecast optimization.
Planning Integration: Use forecast results to join with planning and budgeting systems for integrated financial planning and analysis.
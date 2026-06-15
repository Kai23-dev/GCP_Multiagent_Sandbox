Table Description
Table Name: GROUP_FORECAST_MODEL_PALMER_VP_DECOMPOSITION
Record Count: Very Small
Complete Description:
This table serves as the repository for time series decomposition results for Palmer VP forecast models, representing the breakdown of historical time series data into trend, seasonal, holiday, and residual components. Each record represents a specific time point with its decomposed components for a particular Palmer VP group. This table is essential for time series analysis, forecast model evaluation, seasonal pattern identification, holiday impact assessment, and understanding the underlying patterns in financial data for predictive modeling. The low record count indicates this contains processed analytical results rather than raw transactional data.
________________________________________

Column Description Schema
palmer_vp: This is the Primary Key for the table. It represents the Palmer VP group identifier for the forecast model. Sample Data: PS002
time_series_timestamp: The timestamp for the time series data point. Sample Data: 2025-10-01 00:00:00.000000 UTC, 2025-10-02 00:00:00.000000 UTC, 2025-10-03 00:00:00.000000 UTC
time_series_data: The actual time series data value at the given timestamp. Sample Data: 399073806.0, 40516997.16, 1295866.11
trend: The trend component extracted from the time series decomposition. Sample Data: 917460000.23645163
seasonal_period_yearly: The seasonal component for yearly periodicity extracted from the time series. Sample Data: N/A
holiday_effect: The holiday effect component extracted from the time series decomposition. Sample Data: N/A
residual: The residual component (remaining variation) after removing trend, seasonal, and holiday effects. Sample Data: -518386194.23645163, -876943003.07645166, -916164134.12645161

Join to other tables with these considerations in mind:
Organizational Integration: Use group identifier to join with XXC_GL_DIV_REG_FAC for organizational hierarchy, performance analysis, and regional comparison.
Financial Integration: Use forecast results to join with XXC_GL_SUMMARY for comparing predicted vs actual financial performance and variance analysis.
Time Series Integration: Use timestamp fields to join with financial transaction tables for forecast validation, accuracy measurement, and model improvement.
Decomposition Analysis: Use decomposition results to join with actual financial data for trend analysis and pattern validation.
Model Performance: Combine forecast data with actual results to analyze model accuracy, identify improvement opportunities, and support forecast optimization.
Planning Integration: Use forecast results to join with planning and budgeting systems for integrated financial planning and analysis.
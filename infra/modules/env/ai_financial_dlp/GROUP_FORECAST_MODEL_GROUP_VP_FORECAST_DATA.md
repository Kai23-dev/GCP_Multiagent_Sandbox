Table Description
Table Name: GROUP_FORECAST_MODEL_GROUP_VP_FORECAST_DATA
Record Count: Very Small
Complete Description:
This table serves as the repository for historical time series data used in Group VP forecast models, representing the actual historical values that serve as the foundation for predictive modeling. Each record represents a specific date with its corresponding financial value for a particular Group VP group. This table is essential for time series forecasting, model training, historical trend analysis, and providing the baseline data for generating accurate financial forecasts. The low record count indicates this contains a focused dataset of historical data specifically prepared for forecasting model development and validation.
________________________________________

Column Description Schema
ds: This is the Primary Key for the table. It represents the date stamp for the time series data point. Sample Data: 2025-10-01, 2025-10-02, 2025-10-03
y: The target variable or actual value for the given date. Sample Data: 48372950.37, 13135082.96, 384969.64
group_vp: Foreign Key to organizational hierarchy tables. The Group VP group identifier for the forecast model. Sample Data: GV009

Join to other tables with these considerations in mind:
Organizational Integration: Use group identifier to join with XXC_GL_DIV_REG_FAC for organizational hierarchy, performance analysis, and regional comparison.
Financial Integration: Use forecast results to join with XXC_GL_SUMMARY for comparing predicted vs actual financial performance and variance analysis.
Time Series Integration: Use timestamp fields to join with financial transaction tables for forecast validation, accuracy measurement, and model improvement.
Decomposition Analysis: Use decomposition results to join with actual financial data for trend analysis and pattern validation.
Model Performance: Combine forecast data with actual results to analyze model accuracy, identify improvement opportunities, and support forecast optimization.
Planning Integration: Use forecast results to join with planning and budgeting systems for integrated financial planning and analysis.
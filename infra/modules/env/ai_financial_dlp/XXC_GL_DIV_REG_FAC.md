Table Description
Table Name: XXC_GL_DIV_REG_FAC
Record Count: Small
Complete Description:
This table serves as the master repository for facility hierarchy and organizational structure, representing the complete breakdown of facilities by division, region, and organizational reporting lines. Each record represents a specific facility with its hierarchical relationships, administrative details, legal entity information, and geographic location. This table is essential for organizational management, financial reporting by facility, regional analysis, divisional performance tracking, and maintaining the complete organizational structure for reporting and compliance purposes. The moderate record count indicates comprehensive facility coverage across the organization's healthcare operations.
________________________________________

Column Description Schema
facility_id: This is the Primary Key for the table. It is the unique identifier for each facility. Sample Data: 01134, 01063, 01226
facility_description: The full description of the facility. Sample Data: Arkansas Acutes, SKY RIDGE ACUTES, DEKALB ACUTES
facility_common_name: The common name used for the facility. Sample Data: ARKANSAS ACUTES, SKY RIDGE ACUTES, DEKALB ACUTES
palmer_vp: The Palmer Vice President code for organizational hierarchy. Sample Data: PS003
palmer_vp_desc: The description of the Palmer Vice President role. Sample Data: Small Palmer: OPER
group_vp: The Group Vice President code for organizational hierarchy. Sample Data: GV036
group_vp_desc: The description of the Group Vice President role. Sample Data: APEX: OPER
division: The division code for organizational hierarchy. Sample Data: D0216
division_desc: The description of the division. Sample Data: APEX Hospital Svcs Division: OPER
region: The region code for organizational hierarchy. Sample Data: R0713, R0306, R0918
region_desc: The description of the region. Sample Data: APEX Hospital Svcs Region 01: OPER, APEX Hospital Svcs Region 02: OPER, APEX Hospital Svcs Region 03: OPER
facility_type: The type of facility. Sample Data: Facilities Operations
legal_entity: The legal entity code. Sample Data: 200709, 200600, 200166
legal_entity_desc: The description of the legal entity. Sample Data: Capes Dialysis, LLC, Mountain West Dialysis Services
inactive_date: The date when the facility became inactive. Sample Data: N/A
is_active: Boolean flag (Y/N) indicating if the facility is currently active. Sample Data: false
accounting_start_date: The start date for accounting purposes. Sample Data: 2020-01-01
accounting_end_date: The end date for accounting purposes. Sample Data: N/A
denovo_flag: Boolean flag (Y/N) indicating if this is a de novo facility. Sample Data: N
rollup_flag: Boolean flag (Y/N) indicating if this facility is included in rollups. Sample Data: Y
facility_administrator_name: The name of the facility administrator. Sample Data: JOHN SMITH, MARY JOHNSON, NOT APPLICABLE
regional_director_name: The name of the regional director. Sample Data: MICHAEL WILSON, LISA ANDERSON, JAMES TAYLOR
facility_city: The city where the facility is located. Sample Data: LITTLE ROCK, LONE TREE, DEKALB
facility_state: The state where the facility is located. Sample Data: AR, CO, IL
facility_zip_code: The zip code of the facility. Sample Data: 72205-5423, 80124, 60115
county: The county where the facility is located. Sample Data: PULASKI, ARAPAHOE, WINNEBAGO
source_system: The source system that created or manages this facility record. Sample Data: ORACLE
created_at: The timestamp when this facility record was created. Sample Data: 2026-02-10 06:18:12.114200 UTC
updated_at: The timestamp when this facility record was last updated. Sample Data: 2026-02-10 06:18:15.668565 UTC

Join to other tables with these considerations in mind:
GL Integration: Use account information to join with XXC_GL_SUMMARY for actual transaction analysis, spend validation, and budget performance.
Organizational Analysis: Use division, region, and facility hierarchy for organizational reporting, responsibility accounting, and performance analysis.
Geographic Analysis: Use location information for regional spend analysis, market comparison, and geographic performance reporting.
Hierarchical Reporting: Use the organizational structure for multi-level reporting and drill-down analysis.
Budget Integration: Combine with budget systems for budget vs actual analysis by organizational hierarchy.
Performance Analysis: Use facility information for operational efficiency analysis and benchmarking.
Table Description
Table Name: XXC_GL_DIV_REG_FAC
Record Count: 10,020
Complete Description:
This table serves as the master repository for facility hierarchy and organizational structure, representing the complete breakdown of facilities by division, region, and organizational reporting lines. Each record represents a specific facility with its hierarchical relationships, administrative details, legal entity information, and geographic location. This table is essential for organizational management, financial reporting by facility, regional analysis, divisional performance tracking, and maintaining the complete organizational structure for reporting and compliance purposes. The moderate record count indicates comprehensive facility coverage across the organization's healthcare operations.
Natural representation description:
This table acts as the organizational hierarchy system for facilities, containing the complete breakdown of facilities by division, region, and reporting structure. It provides the foundation for organizational analysis, regional reporting, divisional performance management, and facility-based financial reporting across all healthcare operations.
________________________________________
Column Description Schema
facility_id: This is the Primary Key for the table. It is the unique identifier for each facility. Sample Data: 01134, 01063, 01226, 01064, 12539
facility_description: The full description of the facility. Sample Data: Arkansas Acutes, SKY RIDGE ACUTES, DEKALB ACUTES, ROCK RIVER ACUTES, RENAL CENTER OF FORT DODGE ACUTES
facility_common_name: The common name used for the facility. Sample Data: ARKANSAS ACUTES, SKY RIDGE ACUTES, DEKALB ACUTES, ROCK RIVER ACUTES, RENAL CENTER OF FORT DODGE ACUTES
palmer_vp: The Palmer Vice President code for organizational hierarchy. Sample Data: PS003, PS003, PS003, PS003, PS003
palmer_vp_desc: The description of the Palmer Vice President role. Sample Data: Small Palmer: OPER, Small Palmer: OPER, Small Palmer: OPER, Small Palmer: OPER, Small Palmer: OPER
group_vp: The Group Vice President code for organizational hierarchy. Sample Data: GV036, GV036, GV036, GV036, GV036
group_vp_desc: The description of the Group Vice President role. Sample Data: APEX: OPER, APEX: OPER, APEX: OPER, APEX: OPER, APEX: OPER
division: The division code for organizational hierarchy. Sample Data: D0216, D0216, D0216, D0216, D0216
division_desc: The description of the division. Sample Data: APEX Hospital Svcs Division: OPER, APEX Hospital Svcs Division: OPER, APEX Hospital Svcs Division: OPER, APEX Hospital Svcs Division: OPER, APEX Hospital Svcs Division: OPER
region: The region code for organizational hierarchy. Sample Data: R0713, R0713, R0306, R0306, R0918
region_desc: The description of the region. Sample Data: APEX Hospital Svcs Region 01: OPER, APEX Hospital Svcs Region 01: OPER, APEX Hospital Svcs Region 02: OPER, APEX Hospital Svcs Region 02: OPER, APEX Hospital Svcs Region 03: OPER
facility_type: The type of facility. Sample Data: Facilities Operations, Facilities Operations, Facilities Operations, Facilities Operations, Facilities Operations
legal_entity: The legal entity code. Sample Data: 200709, 200600, 200166, 101270, 101321
legal_entity_desc: The description of the legal entity. Sample Data: Capes Dialysis, LLC, Mountain West Dialysis Services, LLC, Dialysis of Northern Illinois, LLC, Placid Dialysis, LLC, Renal Center of Fort Dodge, LLC
inactive_date: The date when the facility became inactive. Sample Data: N/A, N/A, N/A, N/A, N/A
is_active: Boolean flag (Y/N) indicating if the facility is currently active. Sample Data: false, false, false, false, false
accounting_start_date: The start date for accounting purposes. Sample Data: 2020-01-01, 2020-01-01, 2020-01-01, 2020-01-01, 2020-01-01
accounting_end_date: The end date for accounting purposes. Sample Data: N/A, N/A, N/A, N/A, N/A
denovo_flag: Boolean flag (Y/N) indicating if this is a de novo facility. Sample Data: N, N, N, N, N
rollup_flag: Boolean flag (Y/N) indicating if this facility is included in rollups. Sample Data: Y, Y, Y, Y, Y
facility_administrator_name: The name of the facility administrator. Sample Data: JOHN SMITH, MARY JOHNSON, NOT APPLICABLE, ROBERT BROWN, SARAH DAVIS
regional_director_name: The name of the regional director. Sample Data: MICHAEL WILSON, LISA ANDERSON, N/A, JAMES TAYLOR, JENNIFER MARTINEZ
facility_city: The city where the facility is located. Sample Data: LITTLE ROCK, LONE TREE, DEKALB, ROCKFORD, FORT DODGE
facility_state: The state where the facility is located. Sample Data: AR, CO, IL, IL, IA
facility_zip_code: The zip code of the facility. Sample Data: 72205-5423, 80124, 60115, 61107, 50501
county: The county where the facility is located. Sample Data: PULASKI, ARAPAHOE, WINNEBAGO, WINNEBAGO, WEBSTER
source_system: The source system that created or manages this facility record. Sample Data: ORACLE, ORACLE, ORACLE, ORACLE, ORACLE
created_at: The timestamp when this facility record was created. Sample Data: 2026-02-10 06:18:12.114200 UTC, 2026-02-10 06:18:12.114200 UTC
updated_at: The timestamp when this facility record was last updated. Sample Data: 2026-02-10 06:18:15.668565 UTC, 2026-02-10 06:18:15.668565 UTC

Join to other tables with these considerations in mind:
Primary Facility Integration: Always join facility_id to transaction tables (PO_HEADERS_ALL, AP_INVOICES_ALL, etc.) to get facility-specific financial and operational data.
Legal Entity Integration: Join legal_entity to legal entity tables to get detailed legal entity information for multi-entity reporting and compliance analysis.
Division Analysis: Use division and division_desc to join to division tables for divisional performance analysis and organizational reporting.
Region Analysis: Use region and region_desc to join to region tables for regional performance analysis and geographic reporting.
VP Hierarchy Integration: Join palmer_vp and group_vp to organizational hierarchy tables for management reporting and organizational structure analysis.
Geographic Analysis: Use facility_city, facility_state, facility_zip_code, and county to join to geographic tables for location-based analysis and market analysis.
Facility Type Analysis: Use facility_type to join to facility type tables for facility classification analysis and operational reporting.
Administrator Integration: Use facility_administrator_name and regional_director_name to join to employee tables for management analysis and organizational reporting.
Active Facility Analysis: Use is_active and inactive_date to filter for currently active facilities and analyze facility lifecycle management.
Accounting Period Analysis: Use accounting_start_date and accounting_end_date to analyze facility accounting periods and support financial reporting.
De Novo Analysis: Use denovo_flag to analyze de novo facility patterns and support growth strategy analysis.
Rollup Analysis: Use rollup_flag to identify facilities included in organizational rollups and support hierarchical reporting.
Source System Integration: Use source_system to analyze facility data creation patterns by source system and identify data integration issues.
Audit Trail: Use created_at and updated_at to track facility record lifecycle for compliance reporting and change management analysis.
Hierarchical Reporting: Use the combination of palmer_vp, group_vp, division, and region to support multi-level hierarchical reporting and organizational analysis.
Facility Performance: Join facility_id to financial tables to analyze facility-specific performance metrics and support operational optimization initiatives.

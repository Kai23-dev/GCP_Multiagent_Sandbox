Table Description
Table Name: XXC_GL_DIV_REG_FAC
Record Count: 10,020
Complete Description:
This is a custom "Flattened Hierarchy" or "Dimension" table designed to simplify General Ledger reporting. It maps the lowest level of the organization (Facility) up through the entire corporate reporting chain (Region -> Division -> Group -> Palmer VP). Unlike standard normalized tables that require recursive joins to find a parent, this table stores the entire lineage for a facility in a single row. It also acts as a master directory for facility-specific attributes like addresses, legal entity ownership, and operational leadership.
Natural representation description:
This table acts as the "Organizational Tree" for financial reporting. It answers the question: "Who is responsible for this facility?" It links a physical building (Facility) to its operational hierarchy, distincting between Operational reporting lines (OPER) and Selling, General, and administrative lines (SG&A). It is used to roll up financial data from a single clinic to the highest Vice President level.
________________________________________
Column Description Schema
PARENT_PALMER_VP: The highest level code in the reporting hierarchy (Top-level VP). This represents the "All" or "Summary" node for the top executive level. Sample Data: PS001, PS001, PS001
PARENT_PALMER_VP_DESC: The description associated with the top-level parent code. Sample Data: Small Palmer: All
PALMER_VP: The specific functional node at the top level. This differentiates between different functional areas (e.g., Operations vs. SG&A) under the same parent. Sample Data: PS003, PS003, PS002
PALMER_VP_DESC: The description of the specific functional node. Sample Data: Small Palmer: OPER, Small Palmer: SG&A
PARENT_GROUP_VP: The second level in the hierarchy, grouping multiple divisions. Sample Data: GV025, GV007, GV043
PARENT_GROUP_VP_DESC: The description for the parent Group VP code. Sample Data: Titan: All, Avanti: All, Strategic Initiatives Group: All
GROUP_VP: The specific functional node for the Group level. Sample Data: GV027, GV009, GV044
GROUP_VP_DESC: The description for the specific Group VP, indicating the functional focus (OPER/SG&A). Sample Data: Titan: OPER, Avanti: OPER, Strategic Initiatives Group: SG&A
PARENT_DIVISION: The third level in the hierarchy. Divisions typically cover large geographical areas or business lines. Sample Data: D0117, D0235, D0045
PARENT_DIV_DESC: The description for the parent Division. Sample Data: Bay City Lights Division: All, Centurion Division: All, DaVita IKC-VillageHealth Division: All
DIVISION: The specific functional node for the Division. Sample Data: D0119, D0237, D0046
DIV_DESC: The description for the specific Division node. Sample Data: Bay City Lights Division: OPER, Centurion Division: OPER, DaVita IKC-VillageHealth Division: SG&A
PARENT_REGION: The fourth level in the hierarchy. Regions manage clusters of facilities. Sample Data: R1002, R0525, R0215
PARENT_REG_DESC: The description for the parent Region. Sample Data: Bay City Lights Region 08: All, Centurion Region 01: All, DaVita IKC-VillageHealth Region 03: All
REGION: The specific functional node for the Region. Sample Data: R1004, R0527, R0216
REG_DESC: The description for the specific Region node. Sample Data: Bay City Lights Region 08: OPER, Centurion Region 01: OPER, DaVita IKC-VillageHealth Region 03: SG&A
FACILITY: The Primary Business Key for this table. This is the unique code identifying the specific location or cost center. It likely maps to a General Ledger Segment value. Sample Data: 12749, 5343, 1882
FAC_DESC: The name of the facility. Sample Data: DNVO-h1H`Zvpp.f (Masked), Teterboro Dialysis, IKC Clinical Support Central-PA
LEGAL_ENTITY: A Foreign Key usually linking to XLE_ENTITY_PROFILES. It identifies the registered legal company that owns the assets or operations of this facility. Sample Data: 201768, 100101, 100201
LE_DESC: The name of the Legal Entity. Sample Data: Dixville Dialysis, LLC, Total Renal Care, Inc., VillageHealth DM, LLC
FAC_TYPE: A classification of the facility's function (e.g., Dialysis Center, Office, Team). Sample Data: Facilities Operations, Facilities Operations, IKC Central Team Home
OWNERSHIP_TYPE: Describes the business arrangement (e.g., Wholly Owned, Joint Venture/Majority Partner). Sample Data: Majority Partner, Wholly Owned, Wholly Owned
ROLLUP_FLAG: A boolean indicator (Y/N). If 'Y', this facility's financials are rolled up into the corporate consolidated reporting. Sample Data: Y, N, N/A
DENOVO_FLAG: A boolean indicator (Y/N). "De Novo" typically refers to a new location built from scratch rather than acquired. 'Y' indicates a new build. Sample Data: Y, N, N/A
ACCOUNTING_START_DATE: The effective date when this hierarchy assignment began. Sample Data: 12/25/2022, 25/12/2022, and 2022-12-25. *format may vary
ACCOUNTING_END_DATE: The date when this hierarchy assignment ended. If NULL or far future, it is currently active. Sample Data: 12/25/2022, 25/12/2022, and 2022-12-25. *format may vary, N/A
LOCATION_INACTIVE_DATE: The date the physical location itself became inactive (closed). Sample Data: N/A, 12/25/2022, 25/12/2022, and 2022-12-25. *format may vary
FAC_COMMON_NAME: An alias or common name used to refer to the facility internally. Sample Data: TETERBORO DIALYSIS, IKC CLINICAL SUPPORT CENTRAL-PA
FAC_ADMINISTRATOR_NAME: The full name of the administrator responsible for the facility. Sample Data: AT HOME, VACANT POSITION
FAC_ADDRESS_LINE_1: The first line of the facility's physical address. Sample Data: 123 Main St / Line 2: Apt 4B or 100 Main St, Suite 200
FAC_ADDRESS_LINE_2: The second line of the physical address. Sample Data: N/A, 123 Main St / Line 2: Apt 4B or 100 Main St, Suite 200
FAC_CITY: The city of the facility. Sample Data: HARRINGTON, AUSTIN, SAN FRANCISCO
FAC_STATE: The state abbreviation. Sample Data: MI, CA, TX
FAC_ZIP_CODE: The zip code. Sample Data: 19952-2449,
MAILING_ADDRESS_LINE_1: The first line of the mailing address (if different from physical). Sample Data: 123 Main St / Line 2: Apt 4B or 100 Main St, Suite 200, N/A
MAILING_ADDRESS_LINE_2: The second line of the mailing address. Sample Data: 123 Main St / Line 2: Apt 4B or 100 Main St, Suite 200, N/A
MAILING_CITY: The city for the mailing address. Sample Data: HARRINGTON, AUSTIN, SAN FRANCISCO, N/A
MAILING_STATE: The state for the mailing address. Sample Data: N/A, MI, CA, TX
MAILING_ZIP_CODE: The zip code for the mailing address. Sample Data: 04859,23894, 78393
FAC_PHONE_NUMBER: The main phone number for the facility. Sample Data: 2123456789
FAC_FAX_NUMBER: The fax number for the facility. Sample Data: 2123456789
OPERATIONAL_VP_NAME: The name of the Vice President of Operations overseeing this facility. Sample Data: Michael Smith, William Eobaldi, N/A
REG_DIRECTOR_NAME: The name of the Regional Director. Sample Data: N/A, Sam Adams, Janeth Yilerth.
FAC_ADMIN_USERID: A Foreign Key linking to FND_USER. It identifies the system user account of the facility administrator. Sample Data: userID format
DIV_DESC_LAST4: A utility column likely storing the last 4 characters of the division description or a short code (e.g., OPER vs SG&A). Sample Data: OPER, OPER, SG&A
MAJOR_ROLLUP: An alternative rollup grouping code. Sample Data: OPER0, OPER0, ANCL0
COUNTY: The county where the facility is located. Sample Data: KENT, BERGEN, CHESTER
________________________________________
Join to other tables with these considerations in mind:
GL Chart of Accounts (FACILITY): The FACILITY column is designed to map directly to a segment in the General Ledger (Code Combination). When joining to GL_BALANCES or GL_CODE_COMBINATIONS, join FACILITY to the specific segment column (e.g., SEGMENT3 or SEGMENT4) defined in your Chart of Accounts.
Effective Dating (ACCOUNTING_START_DATE): This table tracks history. When joining to transactions (like Journal Entries or Invoices), you must ensure the transaction date falls BETWEEN the ACCOUNTING_START_DATE and ACCOUNTING_END_DATE. Failing to check dates may result in duplicate rows if a facility moved hierarchies over time.
User/Employee Lookups: The FAC_ADMIN_USERID joins to FND_USER (USER_NAME) to get login details, but for the actual person's details, you may need to bridge from FND_USER to PER_ALL_PEOPLE_F (HR employees).
Legal Entity: The LEGAL_ENTITY column is a Foreign Key. Join this to Oracle's Legal Entity architecture (likely XLE_ENTITY_PROFILES or HR_ALL_ORGANIZATION_UNITS classified as Legal Entities) to validate tax ID and ownership details.
Hierarchy Flattening: Do not attempt recursive joins (Parent = Child) on this table. It is already flattened. If you need to find all facilities under "Bay City Lights Division," simply query WHERE PARENT_DIV_DESC = 'Bay City Lights Division: All'.
Custom Nature (XXC Prefix): Since this is a custom table (XXC), the column names and logic are specific to this client's implementation. Always verify the FACILITY code format against the GL Value Set to ensure data type compatibility (string vs. number) before joining.


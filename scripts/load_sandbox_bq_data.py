import argparse
from datetime import date, datetime
from google.cloud import bigquery


def load_sample_data(project_id: str, dataset_id: str) -> None:
    client = bigquery.Client(project=project_id)

    rows = [
        {
            "journal_header_id": "9376105",
            "journal_line_number": 1984,
            "invoice_id": "61661352",
            "invoice_number": "0204212400",
            "gl_code_combination_id": "6595958",
            "legal_entity": "100101",
            "location": "00552",
            "department": "0400",
            "account": "6604",
            "sub_account": "300",
            "account_name": "Acid Expense",
            "sub_account_name": "In-Center Hemo",
            "amount": 7.5,
            "stat_amount": 0,
            "currency_code": "USD",
            "ledger_id": 1,
            "effective_date": date(2025, 10, 31).isoformat(),
            "period_name": "OCT-25",
            "journal_posted_date": date(2025, 11, 1).isoformat(),
            "journal_category": "Payments",
            "journal_source": "Payables",
            "line_description": "Journal Import Created",
            "batch_name": "DVAAPNP Payables A 20012023 86396417",
            "category": "Direct Medical Supply Expense",
            "super_category": "Medical Supplies",
            "commodity": "N/A",
            "vendor_name": "FRESENIUS USA INC",
            "vendor_id": "6406",
            "po_number": "95080-1083884",
            "check_id": "23524414",
            "check_number": "913052",
            "source_system": "ORACLE",
            "created_at": datetime(2026, 2, 10, 6, 18, 14, 416371).isoformat() + "Z",
            "updated_at": datetime(2026, 2, 10, 6, 18, 24, 895371).isoformat() + "Z",
        }
    ]

    table = f"{project_id}.{dataset_id}.XXC_GL_SUMMARY"
    errors = client.insert_rows_json(table, rows)
    if errors:
        raise RuntimeError(f"Failed to insert rows into {table}: {errors}")
    print(f"Inserted {len(rows)} rows into {table}")

    facility_rows = [
        {
            "facility_id": "01134",
            "facility_description": "Arkansas Acutes",
            "facility_common_name": "ARKANSAS ACUTES",
            "palmer_vp": "PS003",
            "palmer_vp_desc": "Small Palmer: OPER",
            "group_vp": "GV036",
            "group_vp_desc": "APEX: OPER",
            "division": "D0216",
            "division_desc": "APEX Hospital Svcs Division: OPER",
            "region": "R0713",
            "region_desc": "APEX Hospital Svcs Region 01: OPER",
            "facility_type": "Facilities Operations",
            "legal_entity": "200709",
            "legal_entity_desc": "Capes Dialysis, LLC",
            "inactive_date": None,
            "is_active": True,
            "accounting_start_date": date(2020, 1, 1).isoformat(),
            "accounting_end_date": None,
            "denovo_flag": "N",
            "rollup_flag": "Y",
            "facility_administrator_name": "JOHN SMITH",
            "regional_director_name": "MICHAEL WILSON",
            "facility_city": "LITTLE ROCK",
            "facility_state": "AR",
            "facility_zip_code": "72205-5423",
            "county": "PULASKI",
            "source_system": "ORACLE",
            "created_at": datetime(2026, 2, 10, 6, 18, 12, 114200).isoformat() + "Z",
            "updated_at": datetime(2026, 2, 10, 6, 18, 15, 114200).isoformat() + "Z",
        }
    ]
    table = f"{project_id}.{dataset_id}.XXC_GL_DIV_REG_FAC"
    errors = client.insert_rows_json(table, facility_rows)
    if errors:
        raise RuntimeError(f"Failed to insert rows into {table}: {errors}")
    print(f"Inserted {len(facility_rows)} rows into {table}")

    supplier_rows = [
        {
            "vendor_id": "6406",
            "vendor_number": "6406",
            "supplier_name": "FRESENIUS USA INC",
            "supplier_name_normalized": "FRESENIUS USA INC",
            "vendor_type": "VENDOR",
            "organization_type": "CORPORATION",
            "enabled_flag": True,
            "is_active": True,
            "start_date_active": date(2020, 1, 15).isoformat(),
            "end_date_active": None,
            "hold_flag": False,
            "hold_reason": None,
            "hold_all_payments_flag": False,
            "hold_future_payments_flag": False,
            "payment_terms_id": "10032",
            "payment_priority": 10,
            "invoice_currency_code": "USD",
            "payment_currency_code": "USD",
            "num_1099": "91-2154439",
            "type_1099": "MISC6",
            "tax_reporting_name": "FRESENIUS USA INC",
            "source_system": "ORACLE",
            "created_at": datetime(2026, 2, 10, 6, 18, 14, 423229).isoformat() + "Z",
            "updated_at": datetime(2026, 2, 10, 6, 18, 17, 858229).isoformat() + "Z",
        }
    ]
    table = f"{project_id}.{dataset_id}.AP_SUPPLIERS"
    errors = client.insert_rows_json(table, supplier_rows)
    if errors:
        raise RuntimeError(f"Failed to insert rows into {table}: {errors}")
    print(f"Inserted {len(supplier_rows)} rows into {table}")

    invoice_rows = [
        {
            "invoice_id": "61661352",
            "vendor_id": "6406",
            "vendor_site_id": "352685",
            "invoice_number": "0204212400",
            "po_header_id": None,
            "org_id": "0",
            "party_id": "654555",
            "party_site_id": "2383544",
            "invoice_date": date(2025, 1, 15).isoformat(),
            "gl_date": date(2025, 1, 20).isoformat(),
            "invoice_received_date": date(2025, 1, 16).isoformat(),
            "invoice_amount": 225.0,
            "amount_paid": 225.0,
            "currency_code": "USD",
            "description": "DAVITA 6265",
            "source": "170_MV_CONNECTOR",
            "source_system": "ORACLE",
            "created_at": datetime(2026, 2, 10, 6, 18, 14, 335110).isoformat() + "Z",
            "updated_at": datetime(2026, 2, 10, 6, 18, 21, 366110).isoformat() + "Z",
        }
    ]
    table = f"{project_id}.{dataset_id}.AP_INVOICES_ALL"
    errors = client.insert_rows_json(table, invoice_rows)
    if errors:
        raise RuntimeError(f"Failed to insert rows into {table}: {errors}")
    print(f"Inserted {len(invoice_rows)} rows into {table}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load sandbox sample BigQuery rows.")
    parser.add_argument("--project", required=True, help="GCP project ID that contains sandbox BigQuery tables.")
    parser.add_argument("--dataset", default="ai_financial_dlp", help="BigQuery dataset name.")
    args = parser.parse_args()

    load_sample_data(args.project, args.dataset)


if __name__ == "__main__":
    main()

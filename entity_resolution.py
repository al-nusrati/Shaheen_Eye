import pandas as pd
import os

def run_entity_resolution():
    fbr = pd.read_csv("data/processed/fbr_tax_records_clean.csv")
    excise = pd.read_csv("data/processed/excise_vehicles_clean.csv")
    disco = pd.read_csv("data/processed/disco_consumption_clean.csv")
    prop = pd.read_csv("data/processed/property_transfers_clean.csv")

    master_records = []
    
    for idx, row in fbr.iterrows():
        m_id = f"PK-{idx:03d}"
        phone = row['phone_number']
        clean_name = row['clean_name']
        
        # Match Vehicles
        matched_vehicles = excise[excise['clean_name'] == clean_name]
        v_count = len(matched_vehicles)
        max_cc = matched_vehicles['engine_capacity_cc'].max() if v_count > 0 else 0
        v_model = matched_vehicles.iloc[0]['vehicle_make_model'] if v_count > 0 else "None"
        import_t = matched_vehicles.iloc[0]['import_type'] if v_count > 0 else "Local"
        import_val = matched_vehicles['declared_import_value_pkr'].sum() if v_count > 0 else 0
        reg_yr = matched_vehicles['registration_year'].max() if v_count > 0 else 2020

        # Match Properties
        matched_props = prop[prop['clean_name'] == clean_name]
        p_count = len(matched_props)
        p_val = matched_props['property_value_pkr'].sum() if p_count > 0 else 0
        area = matched_props['area_marla'].sum() if p_count > 0 else 0
        reg_type = matched_props.iloc[0]['registry_type'] if p_count > 0 else "None"
        reg_no = matched_props.iloc[0]['registry_no'] if p_count > 0 else "None"
        noc = matched_props.iloc[0]['noc_status'] if p_count > 0 else "Approved"
        transfers = len(matched_props)
        prop_yr = 2024 # default if no transfer year can be extracted

        # Match Utilities
        matched_disco = disco[disco['clean_name'] == clean_name]
        m_bill = matched_disco['avg_monthly_bill_pkr'].mean() if not matched_disco.empty else 0.0

        master_records.append({
            "master_person_id": m_id, "full_name": row['full_name'],
            "city": row['reported_address'].split(",")[-1].strip() if "," in row['reported_address'] else "Lahore",
            "reported_address": row['reported_address'], "address_id": row['address_id'], "phone_number": phone,
            "declared_income_pkr": row['declared_income_pkr'], "tax_paid_pkr": row['tax_paid_pkr'], "filer_status": row['filer_status'],
            "occupation": row['occupation'], "income_source": row['income_source'], "wealth_source": row['wealth_source'],
            "years_as_nonfiler": row['years_as_nonfiler'], "has_bank_account": row['has_bank_account'], "vehicle_count": v_count,
            "max_vehicle_cc": max_cc, "vehicle_make_model": v_model, "import_type": import_t, "declared_import_value_pkr": import_val,
            "vehicle_registration_year": reg_yr, "property_count": p_count, "total_property_value": p_val, "area_marla": area,
            "registry_type": reg_type, "registry_no": reg_no, "noc_status": noc, "transfer_count": transfers,
            "years_active": 2, "property_transfer_year": prop_yr, "avg_monthly_bill_pkr": m_bill, "annual_utility_bill": m_bill * 12
        })

    os.makedirs("outputs", exist_ok=True)
    pd.DataFrame(master_records).to_csv("outputs/master_entities.csv", index=False)
    print("✅ Step 3 complete. Master Entities resolved and outputs/master_entities.csv generated.")

if __name__ == "__main__":
    run_entity_resolution()
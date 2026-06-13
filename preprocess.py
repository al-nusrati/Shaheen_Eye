import pandas as pd
import hashlib
import os
import re

norm_dict = {
    "h#": "house ", "st.": "street ", "ph ": "phase ", "makaan": "house",
    "makan": "house", "gali": "street", "isb": "islamabad", "lhr": "lahore",
    "st ": "street ", "house no.": "house "
}

def normalize_name(name):
    if not isinstance(name, str): return ""
    name = name.lower().strip()
    name = re.sub(r'\b(muhammad|mhd|m|mohammad)\b', 'muhammad', name)
    name = re.sub(r'\b(ahmed|ahmad)\b', 'ahmad', name)
    name = re.sub(r'\b(ch|chaudhry|chaudhri)\b', 'chaudhry', name)
    name = re.sub(r'\b(syed)\b', '', name)
    return " ".join(name.split())

def normalize_address(address):
    if not isinstance(address, str): return ""
    addr = address.lower().strip()
    for key, val in norm_dict.items():
        addr = addr.replace(key, val)
    addr = re.sub(r'\s+', ' ', addr)
    return addr.strip()

def generate_address_id(standard_address):
    if not standard_address: return "UNKNOWN"
    return hashlib.md5(standard_address.encode('utf-8')).hexdigest()[:8]

# Minimum expected columns per source file, used when a file is empty/missing
# so downstream steps (entity_resolution.py) get a valid (0-row) DataFrame
# with the columns they expect, instead of crashing on "no columns to parse".
EXPECTED_COLUMNS = {
    "fbr_tax_records.csv": [
        "fbr_id", "full_name", "declared_income_pkr", "tax_paid_pkr", "filer_status",
        "reported_address", "phone_number", "income_source", "wealth_source",
        "occupation", "years_as_nonfiler", "has_bank_account"
    ],
    "excise_vehicles.csv": [
        "vehicle_reg_no", "owner_name", "engine_capacity_cc", "vehicle_make_model",
        "registration_year", "owner_address", "import_type", "declared_import_value_pkr"
    ],
    "disco_consumption.csv": [
        "meter_ref_no", "consumer_name", "installation_address",
        "avg_monthly_bill_pkr", "connection_type"
    ],
    "property_transfers.csv": [
        "registry_no", "buyer_name", "seller_name", "property_address",
        "property_value_pkr", "transfer_date", "area_marla", "property_type",
        "registry_type", "noc_status", "society_name", "plot_number"
    ],
}

def _load_or_empty(path, file):
    """Read a raw CSV; if it's missing or empty (no columns to parse),
    return an empty DataFrame with the expected columns for that file."""
    expected_cols = EXPECTED_COLUMNS.get(file, [])
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        print(f"⚠️  {path} is missing or empty — treating as 0 records.")
        return pd.DataFrame(columns=expected_cols)
    try:
        df = pd.read_csv(path)
        if df.empty and len(df.columns) == 0:
            print(f"⚠️  {path} has no columns — treating as 0 records.")
            return pd.DataFrame(columns=expected_cols)
        return df
    except pd.errors.EmptyDataError:
        print(f"⚠️  {path} has no columns to parse — treating as 0 records.")
        return pd.DataFrame(columns=expected_cols)

def run_preprocessing():
    os.makedirs("data/processed", exist_ok=True)

    # Process files
    for file in ["fbr_tax_records.csv", "excise_vehicles.csv", "disco_consumption.csv", "property_transfers.csv"]:
        raw_path = f"data/raw/{file}"
        df = _load_or_empty(raw_path, file)

        name_candidates = [c for c in df.columns if 'name' in c or 'owner' in c or 'buyer' in c]
        addr_candidates = [c for c in df.columns if 'address' in c]

        if name_candidates:
            name_col = name_candidates[0]
            df['clean_name'] = df[name_col].apply(normalize_name)
        else:
            df['clean_name'] = pd.Series(dtype='object')

        if addr_candidates:
            addr_col = addr_candidates[0]
            df['clean_address'] = df[addr_col].apply(normalize_address)
        else:
            df['clean_address'] = pd.Series(dtype='object')

        df['address_id'] = df['clean_address'].apply(generate_address_id) if len(df) else pd.Series(dtype='object')

        df.to_csv(f"data/processed/{file.replace('.csv', '_clean.csv')}", index=False)
        print(f"   {file}: {len(df)} record(s) processed.")

    print("✅ Step 2 complete. Secure Address IDs computed in data/processed/")

if __name__ == "__main__":
    run_preprocessing()
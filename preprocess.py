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

def run_preprocessing():
    os.makedirs("data/processed", exist_ok=True)
    
    # Process files
    for file in ["fbr_tax_records.csv", "excise_vehicles.csv", "disco_consumption.csv", "property_transfers.csv"]:
        df = pd.read_csv(f"data/raw/{file}")
        
        name_col = [c for c in df.columns if 'name' in c or 'owner' in c or 'buyer' in c][0]
        addr_col = [c for c in df.columns if 'address' in c][0]
        
        df['clean_name'] = df[name_col].apply(normalize_name)
        df['clean_address'] = df[addr_col].apply(normalize_address)
        df['address_id'] = df['clean_address'].apply(generate_address_id)
        
        df.to_csv(f"data/processed/{file.replace('.csv', '_clean.csv')}", index=False)
        
    print("✅ Step 2 complete. Secure Address IDs computed in data/processed/")

if __name__ == "__main__":
    run_preprocessing()
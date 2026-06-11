import pandas as pd
import numpy as np
from rapidfuzz import fuzz
import networkx as nx
import re
import os

# -----------------------------------------------------------------------------
# 1. Deep name normalisation (Pakistani‑specific)
# -----------------------------------------------------------------------------
ALIAS_MAP = {
    r"\bm\b\.?": "muhammad", r"\bmhd\b\.?": "muhammad", r"\bmohd\b\.?": "muhammad",
    r"\bmohammad\b": "muhammad", r"\bch\b\.?": "chaudhry", r"\bdr\b\.?": "doctor",
    r"\bsyed\b\.?": "syed", r"\bs\b\.?": "syed", r"\babd\b": "abdul",
    r"\b\.": "",  # remove stray dots
}
def clean_pak_name(name):
    if pd.isna(name):
        return ""
    name = str(name).lower().strip()
    for pattern, repl in ALIAS_MAP.items():
        name = re.sub(pattern, repl, name)
    name = re.sub(r'[^\w\s]', '', name)          # remove punctuation
    tokens = sorted(name.split())                # sort for order‑invariant matching
    return " ".join(tokens)

def clean_pak_address(addr):
    if pd.isna(addr):
        return ""
    addr = str(addr).lower().strip()
    addr = re.sub(r'[^\w\s]', '', addr)
    addr = re.sub(r'\b(h|house|ho|hno)\b', 'house', addr)
    addr = re.sub(r'\b(st|street|str)\b', 'street', addr)
    addr = re.sub(r'\b(ph|phase)\b', 'phase', addr)
    return " ".join(addr.split())

# -----------------------------------------------------------------------------
# 2. Helper functions for safe conversion
# -----------------------------------------------------------------------------
def _safe_str(val, default=""):
    if pd.isna(val):
        return default
    return str(val).strip()

def _safe_float(val, default=0.0):
    try:
        v = float(val)
        return v if pd.notna(v) else default
    except:
        return default

def _safe_int(val, default=0):
    try:
        v = int(float(val))
        return v if pd.notna(v) else default
    except:
        return default

# -----------------------------------------------------------------------------
# 3. Main graph‑based entity resolution
# -----------------------------------------------------------------------------
def run_entity_resolution():
    print("🕵️‍♂️ Starting Graph‑Based Entity Resolution (Transitive Closure)")

    # Load cleaned files
    fbr    = pd.read_csv("data/processed/fbr_tax_records_clean.csv")
    excise = pd.read_csv("data/processed/excise_vehicles_clean.csv")
    disco  = pd.read_csv("data/processed/disco_consumption_clean.csv")
    prop   = pd.read_csv("data/processed/property_transfers_clean.csv")

    # Add source tag
    fbr['source'] = 'FBR'
    excise['source'] = 'EXC'
    disco['source'] = 'DIS'
    prop['source'] = 'PRO'

    # Unify column names for melting
    fbr = fbr.rename(columns={'full_name': 'raw_name', 'reported_address': 'raw_address'})
    excise = excise.rename(columns={'owner_name': 'raw_name', 'owner_address': 'raw_address'})
    disco = disco.rename(columns={'consumer_name': 'raw_name', 'installation_address': 'raw_address'})
    prop = prop.rename(columns={'buyer_name': 'raw_name', 'property_address': 'raw_address'})

    # Keep relevant columns only
    keep_cols = ['raw_name', 'raw_address', 'phone_number', 'filer_status', 'declared_income_pkr',
                 'tax_paid_pkr', 'occupation', 'income_source', 'wealth_source', 'has_bank_account',
                 'years_as_nonfiler', 'fbr_id', 'engine_capacity_cc', 'vehicle_make_model',
                 'import_type', 'declared_import_value_pkr', 'registration_year',
                 'property_value_pkr', 'area_marla', 'registry_type', 'noc_status',
                 'avg_monthly_bill_pkr', 'source']

    for df in [fbr, excise, disco, prop]:
        for col in keep_cols:
            if col not in df.columns:
                df[col] = None

    melting_pot = pd.concat([fbr[keep_cols], excise[keep_cols], disco[keep_cols], prop[keep_cols]], ignore_index=True)
    melting_pot['record_id'] = ['REC_' + str(i) for i in range(len(melting_pot))]

    # Apply cleaning
    melting_pot['clean_name'] = melting_pot['raw_name'].apply(clean_pak_name)
    melting_pot['clean_address'] = melting_pot['raw_address'].apply(clean_pak_address)
    melting_pot['phone'] = melting_pot['phone_number'].fillna('').astype(str)
    melting_pot['fbr_id'] = melting_pot['fbr_id'].fillna('').astype(str)

    # -------------------------------------------------------------------------
    # Build similarity graph
    # -------------------------------------------------------------------------
    G = nx.Graph()
    for _, row in melting_pot.iterrows():
        G.add_node(row['record_id'], data=row.to_dict())

    records = melting_pot.to_dict('records')
    n = len(records)
    print(f"Processing {n} records – building transitive edges")

    # Blocking: compare only records that share first 4 chars of cleaned name or same phone
    # This keeps complexity manageable (O(n²) becomes O(n * block_size))
    from collections import defaultdict
    blocks = defaultdict(list)
    for rec in records:
        key = rec['clean_name'][:4] if rec['clean_name'] else rec['phone'][:8]
        if key:
            blocks[key].append(rec)

    total_compared = 0
    edges_added = 0
    for key, block_records in blocks.items():
        if len(block_records) < 2:
            continue
        for i in range(len(block_records)):
            A = block_records[i]
            for j in range(i + 1, len(block_records)):
                B = block_records[j]
                total_compared += 1

                # ----- Strong signals (direct match) -----
                # 1. Exact phone match
                if A['phone'] and B['phone'] and A['phone'] == B['phone']:
                    G.add_edge(A['record_id'], B['record_id'])
                    edges_added += 1
                    continue

                # 2. Exact FBR ID match
                if A['fbr_id'] and B['fbr_id'] and A['fbr_id'] == B['fbr_id']:
                    G.add_edge(A['record_id'], B['record_id'])
                    edges_added += 1
                    continue

                # ----- Weaker signals (require multiple) -----
                name_sim = fuzz.token_sort_ratio(A['clean_name'], B['clean_name'])
                addr_sim = fuzz.token_sort_ratio(A['clean_address'], B['clean_address'])

                # High name similarity + reasonable address similarity
                if name_sim >= 85 and addr_sim >= 70:
                    G.add_edge(A['record_id'], B['record_id'])
                    edges_added += 1
                    continue

                # Very high name similarity (90+) even without address
                if name_sim >= 90:
                    G.add_edge(A['record_id'], B['record_id'])
                    edges_added += 1
                    continue

                # Name medium (70+) AND address high (85+)
                if name_sim >= 70 and addr_sim >= 85:
                    G.add_edge(A['record_id'], B['record_id'])
                    edges_added += 1
                    continue

                # If one record contains the other's address (e.g., "House 5, Gulberg" vs "Gulberg")
                if A['clean_address'] and B['clean_address']:
                    if A['clean_address'] in B['clean_address'] or B['clean_address'] in A['clean_address']:
                        if name_sim >= 75:
                            G.add_edge(A['record_id'], B['record_id'])
                            edges_added += 1
                            continue

    print(f"Compared {total_compared} pairs, added {edges_added} edges")

    # -------------------------------------------------------------------------
    # Extract connected components → each component = one unique person
    # -------------------------------------------------------------------------
    components = list(nx.connected_components(G))
    print(f"Found {len(components)} unique person clusters")

    master_records = []
    for comp_id, comp_nodes in enumerate(components):
        cluster_records = [G.nodes[nid]['data'] for nid in comp_nodes]
        cluster_df = pd.DataFrame(cluster_records)

        # Pick the FBR record as primary if exists, else first
        fbr_rows = cluster_df[cluster_df['source'] == 'FBR']
        primary = fbr_rows.iloc[0] if not fbr_rows.empty else cluster_df.iloc[0]

        # Aggregate assets
        vehicles = cluster_df[cluster_df['source'] == 'EXC']
        props = cluster_df[cluster_df['source'] == 'PRO']
        utils = cluster_df[cluster_df['source'] == 'DIS']

        master_records.append({
            "master_person_id": f"PK-{comp_id:04d}",
            "full_name": _safe_str(primary.get('raw_name', 'Unknown')),
            "city": _safe_str(primary.get('raw_address', '')).split(',')[-1].strip().capitalize() or "Lahore",
            "reported_address": _safe_str(primary.get('raw_address')),
            "address_id": "UNKNOWN",
            "phone_number": _safe_str(primary.get('phone_number')),
            "declared_income_pkr": _safe_float(primary.get('declared_income_pkr')),
            "tax_paid_pkr": _safe_float(primary.get('tax_paid_pkr')),
            "filer_status": _safe_str(primary.get('filer_status'), "Non-ATL"),
            "occupation": _safe_str(primary.get('occupation')),
            "income_source": _safe_str(primary.get('income_source')),
            "wealth_source": _safe_str(primary.get('wealth_source')),
            "years_as_nonfiler": _safe_int(primary.get('years_as_nonfiler')),
            "has_bank_account": bool(primary.get('has_bank_account', True)),
            "fbr_id": _safe_str(primary.get('fbr_id')),
            "vehicle_count": len(vehicles),
            "max_vehicle_cc": _safe_float(vehicles['engine_capacity_cc'].max()) if len(vehicles) else 0,
            "vehicle_make_model": _safe_str(vehicles.iloc[0]['vehicle_make_model']) if len(vehicles) else "None",
            "import_type": _safe_str(vehicles.iloc[0]['import_type']) if len(vehicles) else "Local",
            "declared_import_value_pkr": _safe_float(vehicles['declared_import_value_pkr'].sum()),
            "vehicle_registration_year": _safe_int(vehicles['registration_year'].max()) if len(vehicles) else 2020,
            "property_count": len(props),
            "total_property_value": _safe_float(props['property_value_pkr'].sum()),
            "area_marla": _safe_float(props['area_marla'].sum()),
            "registry_type": _safe_str(props.iloc[0]['registry_type']) if len(props) else "None",
            "registry_no": "N/A",
            "noc_status": _safe_str(props.iloc[0]['noc_status'], "Approved") if len(props) else "Approved",
            "transfer_count": len(props),
            "years_active": 2,
            "property_transfer_year": 2025 if len(props) else 2020,
            "buyer_name": "N/A",
            "avg_monthly_bill_pkr": _safe_float(utils['avg_monthly_bill_pkr'].mean()) if len(utils) else 0.0,
            "annual_utility_bill": (_safe_float(utils['avg_monthly_bill_pkr'].mean()) * 12) if len(utils) else 0.0,
        })

    os.makedirs("outputs", exist_ok=True)
    out_df = pd.DataFrame(master_records)
    out_df.to_csv("outputs/master_entities.csv", index=False)
    print(f"✅ Entity resolution complete. {len(out_df)} unique persons saved.")

if __name__ == "__main__":
    run_entity_resolution()
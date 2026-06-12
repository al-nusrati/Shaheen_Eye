import os
import pandas as pd
import networkx as nx
import pickle

def construct_graph(input_csv="outputs/master_entities.csv", output_pkl="outputs/shaheen_graph.pkl"):
    print(f"Loading master entities from {input_csv} to build Knowledge Graph...")
    if not os.path.exists(input_csv):
        print(f"Error: {input_csv} not found. Please run entity_resolution.py first.")
        return
        
    df = pd.read_csv(input_csv)
    G = nx.Graph()
    
    # 1. Add Nodes and Asset Edges
    for idx, row in df.iterrows():
        pid = row['master_person_id']
        name = row['full_name']
        
        # Add Person Node
        G.add_node(pid, type='Person', name=name, city=row.get('city', ''), score=0)
        
        # Add Vehicle Node if exists
        if row.get('max_vehicle_cc', 0) > 0:
            vid = f"V_{pid}"
            G.add_node(vid, type='Vehicle', make_model=row.get('vehicle_make_model', ''), cc=row.get('max_vehicle_cc', 0))
            G.add_edge(pid, vid, type='OWNS')
            
        # Add Property Node if exists
        if row.get('property_count', 0) > 0:
            prid = f"P_{pid}"
            G.add_node(prid, type='Property', address=row.get('reported_address', ''), value=row.get('total_property_value', 0), area=row.get('area_marla', 0))
            G.add_edge(pid, prid, type='OWNS')
            
        # Add Electric Meter Node if exists
        if row.get('avg_monthly_bill_pkr', 0) > 0:
            mid = f"M_{pid}"
            G.add_node(mid, type='ElectricMeter', monthly_bill=row.get('avg_monthly_bill_pkr', 0))
            G.add_edge(pid, mid, type='CONSUMES')
            
        # Add Tax Filing Node
        fid = f"FBR_{pid}"
        G.add_node(fid, type='TaxFiling', declared_income=row.get('declared_income_pkr', 0), status=row.get('filer_status', ''))
        G.add_edge(pid, fid, type='FILED')

    # 2. Add SHARES_ADDRESS Edges (Guilt-by-Association/Family Rings)
    print("Mapping shared addresses for fraud ring detection...")
    grouped = df.groupby('address_id')
    for addr_id, group in grouped:
        if len(group) > 1 and addr_id != "UNKNOWN":
            pids = group['master_person_id'].tolist()
            for i in range(len(pids)):
                for j in range(i + 1, len(pids)):
                    u, v = pids[i], pids[j]
                    if G.has_edge(u, v):
                        existing = G[u][v].get('type', '')
                        if 'SHARES_ADDRESS' not in existing:
                            new_type = existing + ',SHARES_ADDRESS' if existing else 'SHARES_ADDRESS'
                            G[u][v]['type'] = new_type
                    else:
                        G.add_edge(u, v, type='SHARES_ADDRESS')

    # 3. Add SHARES_PHONE edges
    phone_groups = df.groupby('phone_number')
    for phone, group in phone_groups:
        if phone and str(phone).strip() not in ('', 'N/A', 'nan', 'None') and len(group) > 1:
            pids = group['master_person_id'].tolist()
            for i in range(len(pids)):
                for j in range(i+1, len(pids)):
                    u, v = pids[i], pids[j]
                    if G.has_edge(u, v):
                        existing = G[u][v].get('type', '')
                        if 'SHARES_PHONE' not in existing:
                            new_type = existing + ',SHARES_PHONE' if existing else 'SHARES_PHONE'
                            G[u][v]['type'] = new_type
                    else:
                        G.add_edge(u, v, type='SHARES_PHONE')

    # 4. Add SHARES_FBR_ID edges
    fbr_groups = df.groupby('fbr_id')
    for fbr, group in fbr_groups:
        if fbr and str(fbr).strip() not in ('', 'N/A', 'nan', 'None') and len(group) > 1:
            pids = group['master_person_id'].tolist()
            for i in range(len(pids)):
                for j in range(i+1, len(pids)):
                    u, v = pids[i], pids[j]
                    if G.has_edge(u, v):
                        existing = G[u][v].get('type', '')
                        if 'SHARES_FBR_ID' not in existing:
                            new_type = existing + ',SHARES_FBR_ID' if existing else 'SHARES_FBR_ID'
                            G[u][v]['type'] = new_type
                    else:
                        G.add_edge(u, v, type='SHARES_FBR_ID')

    # 5. Save the Graph
    os.makedirs(os.path.dirname(output_pkl), exist_ok=True)
    with open(output_pkl, 'wb') as f:
        pickle.dump(G, f)
    
    # Print edge statistics
    address_edges = sum(1 for u,v,d in G.edges(data=True) if 'SHARES_ADDRESS' in d.get('type',''))
    phone_edges = sum(1 for u,v,d in G.edges(data=True) if 'SHARES_PHONE' in d.get('type',''))
    fbr_edges = sum(1 for u,v,d in G.edges(data=True) if 'SHARES_FBR_ID' in d.get('type',''))
    print(f"✅ Knowledge Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
    print(f"   SHARES_ADDRESS edges: {address_edges}, SHARES_PHONE: {phone_edges}, SHARES_FBR_ID: {fbr_edges}")

if __name__ == "__main__":
    construct_graph()
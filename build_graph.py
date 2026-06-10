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
        G.add_node(pid, type='Person', name=name, city=row['city'], score=0)
        
        # Add Vehicle Node if exists
        if row['max_vehicle_cc'] > 0:
            vid = f"V_{pid}"
            G.add_node(vid, type='Vehicle', make_model=row['vehicle_make_model'], cc=row['max_vehicle_cc'])
            G.add_edge(pid, vid, type='OWNS')
            
        # Add Property Node if exists
        if row['property_count'] > 0:
            prid = f"P_{pid}"
            G.add_node(prid, type='Property', address=row['reported_address'], value=row['total_property_value'], area=row['area_marla'])
            G.add_edge(pid, prid, type='OWNS')
            
        # Add Electric Meter Node if exists
        if row['avg_monthly_bill_pkr'] > 0:
            mid = f"M_{pid}"
            G.add_node(mid, type='ElectricMeter', monthly_bill=row['avg_monthly_bill_pkr'])
            G.add_edge(pid, mid, type='CONSUMES')
            
        # Add Tax Filing Node
        fid = f"FBR_{pid}"
        G.add_node(fid, type='TaxFiling', declared_income=row['declared_income_pkr'], status=row['filer_status'])
        G.add_edge(pid, fid, type='FILED')

    # 2. Add SHARES_ADDRESS Edges (Guilt-by-Association/Family Rings)
    print("Mapping shared addresses for fraud ring detection...")
    # Group by address_id to find people living at the same place
    grouped = df.groupby('address_id')
    for addr_id, group in grouped:
        if len(group) > 1 and addr_id != "UNKNOWN":
            pids = group['master_person_id'].tolist()
            # Connect every person sharing this address with a SHARES_ADDRESS edge
            for i in range(len(pids)):
                for j in range(i + 1, len(pids)):
                    G.add_edge(pids[i], pids[j], type='SHARES_ADDRESS')

    # 3. Save the Graph
    os.makedirs(os.path.dirname(output_pkl), exist_ok=True)
    with open(output_pkl, 'wb') as f:
        pickle.dump(G, f)
    print(f"✅ Knowledge Graph successfully built and saved to {output_pkl} with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges!")

if __name__ == "__main__":
    construct_graph()
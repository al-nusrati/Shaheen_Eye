# ring_detection.py
import pandas as pd
import networkx as nx
import pickle
import os
from collections import defaultdict

# Correct import for python-louvain (installs as 'community')
try:
    import community as community_louvain
except ImportError:
    raise ImportError("python-louvain not installed. Run: pip install python-louvain")

# Guard against the wrong 'community' package
if not hasattr(community_louvain, 'best_partition'):
    raise RuntimeError("Wrong 'community' package installed. Run: pip uninstall community -y && pip install python-louvain")

def detect_fraud_rings(graph_path="outputs/shaheen_graph.pkl",
                       scored_path="outputs/scored_entities.csv",
                       resolution=1.0):
    """
    Load graph, extract person-only subgraph with SHARES_* edges,
    run Louvain community detection, compute ring-level aggregates.
    Returns (rings_df, person_to_ring).
    """
    if not os.path.exists(graph_path):
        return pd.DataFrame(), {}

    with open(graph_path, "rb") as f:
        G_full = pickle.load(f)

    # --- Build person-only graph using only SHARES_* edges ---
    person_nodes = [n for n, d in G_full.nodes(data=True) if d.get('type') == 'Person']
    shares_edges = []
    for u, v, d in G_full.edges(data=True):
        edge_type = d.get('type', '')
        if 'SHARES_' in edge_type and u in person_nodes and v in person_nodes:
            shares_edges.append((u, v))

    G_persons = nx.Graph()
    G_persons.add_nodes_from(person_nodes)
    G_persons.add_edges_from(shares_edges)
    G_persons.remove_nodes_from(list(nx.isolates(G_persons)))

    if G_persons.number_of_nodes() == 0:
        return pd.DataFrame(), {}

    # --- Louvain community detection ---
    partition = community_louvain.best_partition(G_persons, resolution=resolution)

    # --- Load scored entities ---
    if os.path.exists(scored_path):
        df = pd.read_csv(scored_path)
        if 'master_person_id' not in df.columns:
            df['master_person_id'] = df.index.astype(str)
        df.set_index('master_person_id', inplace=True)
    else:
        df = pd.DataFrame()

    # --- Aggregate rings ---
    ring_members = defaultdict(list)
    for node, ring_id in partition.items():
        ring_members[ring_id].append(node)

    rings_data = []
    person_to_ring = {}

    for ring_id, members in ring_members.items():
        if len(members) < 2:
            for m in members:
                person_to_ring[m] = -1
            continue

        total_declared = 0
        total_assets = 0
        total_vehicles = 0
        total_properties = 0
        non_filer_count = 0
        members_info = []

        anchor = None
        highest_assets = -1

        for pid in members:
            person_to_ring[pid] = ring_id
            if pid in df.index:
                row = df.loc[pid]
                inc = float(row.get('declared_income_pkr', 0))
                assets = float(row.get('total_assets_estimated', 0))
                vehicles = int(row.get('vehicle_count', 0))
                props = int(row.get('property_count', 0))
                filer = str(row.get('filer_status', ''))
                risk = str(row.get('risk_category', 'UNKNOWN'))

                total_declared += inc
                total_assets += assets
                total_vehicles += vehicles
                total_properties += props
                if filer == 'Non-ATL':
                    non_filer_count += 1

                members_info.append({
                    'person_id': pid,
                    'name': row.get('full_name', pid),
                    'income': inc,
                    'assets': assets,
                    'risk': risk,
                    'filer': filer
                })

                # Anchor: highest assets (tie‑breaker: Non-ATL)
                if assets > highest_assets:
                    highest_assets = assets
                    anchor = pid
                elif assets == highest_assets and anchor is not None:
                    current_filer = members_info[-1]['filer']
                    anchor_filer = next((m['filer'] for m in members_info if m['person_id'] == anchor), '')
                    if current_filer == 'Non-ATL' and anchor_filer != 'Non-ATL':
                        anchor = pid
            else:
                # Should not happen (all nodes are persons), but fallback
                members_info.append({'person_id': pid, 'name': pid, 'income': 0, 'assets': 0,
                                     'risk': 'UNKNOWN', 'filer': 'Unknown'})
                if anchor is None:
                    anchor = pid

        if anchor is None:
            anchor = members[0]

        tax_gap = total_assets * 0.15
        risk_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "COMPLIANT": 0, "UNKNOWN": 0}
        max_risk_val = max((risk_order.get(m['risk'], 0) for m in members_info), default=0)
        ring_risk = {4: "CRITICAL", 3: "HIGH", 2: "MEDIUM", 1: "LOW", 0: "COMPLIANT"}[max_risk_val]

        anchor_name = next((m['name'] for m in members_info if m['person_id'] == anchor), 'Unknown')
        anchor_income = next((m['income'] for m in members_info if m['person_id'] == anchor), 0)

        rings_data.append({
            'ring_id': ring_id,
            'size': len(members),
            'total_declared_income': total_declared,
            'total_estimated_assets': total_assets,
            'estimated_tax_gap': tax_gap,
            'total_vehicles': total_vehicles,
            'total_properties': total_properties,
            'non_filer_count': non_filer_count,
            'anchor_person_id': anchor,
            'anchor_name': anchor_name,
            'anchor_income': anchor_income,
            'risk_level': ring_risk,
            'members': members,
        })

    rings_df = pd.DataFrame(rings_data)
    if not rings_df.empty:
        rings_df = rings_df.sort_values('estimated_tax_gap', ascending=False).reset_index(drop=True)
    return rings_df, person_to_ring

def get_ring_evidence_chain(ring_id, rings_df, graph, persons_df, max_lines=12):
    """Generate human-readable evidence chain for a ring."""
    if ring_id not in rings_df['ring_id'].values:
        return "No ring data."
    row = rings_df[rings_df['ring_id'] == ring_id].iloc[0]
    members = row['members']
    evidence = []

    # Helper to get name
    def get_name(pid):
        if persons_df is not None and not persons_df.empty and pid in persons_df['master_person_id'].values:
            return persons_df[persons_df['master_person_id'] == pid]['full_name'].values[0]
        return pid

    # Collect SHARES_* edges among members
    edge_summary = {}
    for u in members:
        for v in members:
            if u < v and graph.has_edge(u, v):
                typ = graph.get_edge_data(u, v).get('type', '')
                if typ and 'SHARES_' in typ:
                    edge_summary[(u, v)] = typ

    for (u, v), typ in edge_summary.items():
        u_name = get_name(u)
        v_name = get_name(v)
        if typ == 'SHARES_ADDRESS':
            evidence.append(f"🏠 **{u_name}** and **{v_name}** share the same residential address.")
        elif typ == 'SHARES_PHONE':
            evidence.append(f"📞 **{u_name}** and **{v_name}** share the same phone number.")
        elif typ == 'SHARES_FBR_ID':
            evidence.append(f"🆔 **{u_name}** and **{v_name}** share the same FBR ID (strong identity link).")
        elif ',' in typ:
            types = typ.split(',')
            desc = []
            if 'SHARES_ADDRESS' in types: desc.append("same address")
            if 'SHARES_PHONE' in types: desc.append("same phone")
            if 'SHARES_FBR_ID' in types: desc.append("same FBR ID")
            evidence.append(f"🔗 **{u_name}** and **{v_name}** are connected by multiple signals: {', '.join(desc)}.")
        else:
            evidence.append(f"🔗 **{u_name}** and **{v_name}** are linked (type: {typ}).")

    if not evidence:
        return "No direct SHARES_* edges found among ring members (they may be connected indirectly via other persons)."

    non_filers = row['non_filer_count']
    if non_filers > 0:
        evidence.insert(0, f"📊 **Ring summary:** {non_filers} out of {row['size']} members are Non‑Filers (ATL‑), yet they collectively control Rs. {row['total_estimated_assets']/1e6:.1f}M in assets.")

    return "\n".join(evidence[:max_lines])

if __name__ == "__main__":
    rings_df, _ = detect_fraud_rings()
    print(f"Detected {len(rings_df)} rings with at least 2 persons")
    if not rings_df.empty:
        print(rings_df[['ring_id', 'size', 'estimated_tax_gap', 'anchor_name']].head())
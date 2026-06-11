import os
import pickle
import pandas as pd
import numpy as np
import re
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import networkx as nx
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ── Safe conversion helpers ────────────────────────────────────────────────────
def _safe_float(val, default=0.0):
    try:
        v = float(val)
        return v if (pd.notna(v) and np.isfinite(v)) else default
    except (TypeError, ValueError):
        return default

def _safe_int(val, default=0):
    try:
        v = int(float(val))
        return v if pd.notna(v) else default
    except (TypeError, ValueError):
        return default

def _safe_str(val, default="N/A"):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "none", "nat") else default

# ── Outlier caps ─────────────────────────────────────────────────────────────
_INCOME_CAP = 50_000_000      # 5 crore
_ASSET_CAP  = 500_000_000     # 50 crore

class ShaheenForensicEngine:
    
    def __init__(self):
        self.market_rates = {
            "dha": 3500000, "defence": 4000000, "bahria": 2200000,
            "gulberg": 3000000, "e-11": 4500000, "f-6": 5000000,
            "f-7": 4800000, "g-10": 2500000, "g-11": 2800000,
            "clifton": 4000000, "pechs": 2800000, "nazimabad": 1800000,
            "johar": 1600000, "faisalabad": 1200000, "multan": 1000000,
            "rawalpindi": 1800000, "peshawar": 1500000, "default": 800000
        }
        self.proxy_occupations = [
            'driver', 'housewife', 'student', 'peon', 'servant',
            'retired', 'unemployed', 'security guard', 'cook',
            'gardener', 'clerk', 'dependent', 'none'
        ]
        self.luxury_vehicles = [
            'land cruiser', 'prado', 'fortuner', 'lexus', 'bmw',
            'mercedes', 'audi', 'porsche', 'range rover', 'hilux',
            'camry', 'crown'
        ]
        self.vehicle_values = {
            (0,    800):  800_000,
            (800,  1000): 1_200_000,
            (1000, 1300): 2_200_000,
            (1300, 1600): 3_000_000,
            (1600, 1800): 3_500_000,
            (1800, 2000): 5_000_000,
            (2000, 2500): 8_000_000,
            (2500, 3000): 10_000_000,
            (3000, 9999): 15_000_000,
        }

    def get_vehicle_value(self, cc):
        cc = _safe_float(cc)
        for (lo, hi), val in self.vehicle_values.items():
            if lo <= cc < hi:
                return val
        return 800_000

    def get_market_rate(self, address):
        addr = str(address).lower()
        for area, rate in self.market_rates.items():
            if area in addr:
                return rate
        return self.market_rates["default"]

    # ── 18 forensic modules ───────────────────────────────────────────────────
    def detect_benami_proxy(self, occupation, total_assets, declared_income):
        score = 0
        occ = _safe_str(occupation, "").lower()
        if any(p in occ for p in self.proxy_occupations):
            if total_assets > 5_000_000:
                score += 65
            elif total_assets > 2_000_000:
                score += 40
        if declared_income < 400_000 and total_assets > 10_000_000:
            score += 40
        return min(score, 100)

    def detect_family_ring(self, person_id, graph):
        if graph is None:
            return 0
        try:
            neighbors = list(graph.neighbors(person_id))
            sa = [n for n in neighbors
                  if graph.edges.get((person_id, n), {}).get('type') == 'SHARES_ADDRESS'
                  or graph.edges.get((n, person_id), {}).get('type') == 'SHARES_ADDRESS']
            if len(sa) >= 2:
                return 55
            elif len(sa) == 1:
                return 25
        except Exception:
            pass
        return 0

    def detect_corporate_shield(self, buyer_name):
        kw = ['enterprises', 'associates', 'holdings', 'trust', 'pvt',
              'limited', 'brothers', 'sons', 'trading']
        if any(k in _safe_str(buyer_name, "").lower() for k in kw):
            return 45
        return 0

    def detect_dc_rate_underinvoicing(self, declared_val, area_marla, address):
        market_rate   = self.get_market_rate(address)
        real_val      = _safe_float(area_marla) * market_rate
        if real_val == 0:
            return 0
        ratio = _safe_float(declared_val) / real_val
        if ratio < 0.15: return 55
        if ratio < 0.30: return 45
        if ratio < 0.50: return 25
        return 0

    def detect_file_trading(self, registry_type, filer_status):
        file_types = ['file', 'allotment letter', 'transfer letter', 'open file']
        rt = _safe_str(registry_type, "").lower()
        if any(f in rt for f in file_types):
            return 40 if filer_status == 'Non-ATL' else 20
        return 0

    def detect_property_flipping(self, transfer_count, years_span, declared_income):
        tc = _safe_int(transfer_count)
        if tc == 0:
            return 0
        velocity = tc / max(_safe_float(years_span, 1), 0.5)
        score = 0
        if velocity > 3:   score += 40
        elif velocity > 1.5: score += 25
        if _safe_float(declared_income) < 1_000_000 and tc > 2:
            score += 20
        return min(score, 60)

    def detect_illegal_society(self, noc_status, property_value):
        illegal = ['unapproved', 'illegal', 'pending', 'cancelled', 'encroachment']
        if any(s in _safe_str(noc_status, "").lower() for s in illegal):
            return 35 if _safe_float(property_value) > 10_000_000 else 20
        return 0

    def detect_agri_shield(self, income_source, declared_income, total_assets):
        if 'agri' in _safe_str(income_source, "").lower():
            if total_assets > 50_000_000: return 40
            if total_assets > 20_000_000: return 25
        return 0

    def detect_section_111_abuse(self, wealth_source, total_assets, prior_income):
        kw = ['remittance', 'foreign transfer', 'overseas', 'nrp', 'gift from abroad']
        ws = _safe_str(wealth_source, "").lower()
        if any(k in ws for k in kw):
            if _safe_float(total_assets) > 20_000_000 and _safe_float(prior_income) < 2_000_000:
                return 50
            if _safe_float(total_assets) > 10_000_000:
                return 30
        return 0

    def detect_gift_declaration(self, wealth_source, asset_value):
        kw = ['gift', 'inheritance', 'hiba', 'donation', 'bequest']
        ws = _safe_str(wealth_source, "").lower()
        if any(k in ws for k in kw):
            av = _safe_float(asset_value)
            if av > 20_000_000: return 50
            if av > 10_000_000: return 35
            if av > 5_000_000:  return 20
        return 0

    def detect_prize_bond_laundering(self, income_source, declared_amount):
        src = _safe_str(income_source, "").lower()
        if 'prize' in src or 'bond' in src:
            if _safe_float(declared_amount) > 10_000_000:
                return 35
        return 0

    def detect_vehicle_underinvoicing(self, declared_import_value, vehicle_model, engine_cc):
        div = _safe_float(declared_import_value)
        if div == 0:
            return 0
        estimated = self.get_vehicle_value(engine_cc)
        is_luxury  = any(lv in _safe_str(vehicle_model, "").lower()
                         for lv in self.luxury_vehicles)
        if is_luxury:
            estimated *= 1.5
        ratio = div / estimated
        if ratio < 0.10: return 55
        if ratio < 0.25: return 40
        if ratio < 0.50: return 20
        return 0

    def detect_nonfiler_surcharge_buyin(self, filer_status, vehicle_value, years_as_nonfiler):
        if filer_status == 'Non-ATL' and _safe_float(vehicle_value) > 3_000_000:
            return 40 if _safe_int(years_as_nonfiler) > 3 else 25
        return 0

    def detect_baggage_scheme_abuse(self, import_type, vehicle_count, **_):
        if 'baggage' in _safe_str(import_type, "").lower():
            if _safe_int(vehicle_count) > 1:
                return 45
        return 0

    def detect_duplicate_registry(self, registry_no, df):
        rno = _safe_str(registry_no, "")
        if df is None or not rno or rno == "N/A":
            return 0
        try:
            count = df[df['registry_no'] == rno]['master_person_id'].nunique()
            if count > 1:
                return 60
        except Exception:
            pass
        return 0

    def detect_hawala_signature(self, total_assets, declared_income, wealth_source, has_bank_account):
        score = 0
        cash_srcs = ['cash', 'unknown', 'undisclosed', 'none', '']
        ws = _safe_str(wealth_source, "").lower()
        ta = _safe_float(total_assets)
        di = _safe_float(declared_income)
        if ta > 20_000_000 and di < 500_000:
            if any(c in ws for c in cash_srcs):
                score += 55
            if not has_bank_account:
                score += 20
        return min(score, 75)

    def detect_rental_concealment(self, property_count, income_source, filer_status):
        if _safe_int(property_count) >= 2:
            src = _safe_str(income_source, "").lower()
            if 'rental' not in src and 'rent' not in src:
                return 35 if filer_status == 'Non-ATL' else 15
        return 0

    # ── ML / graph helpers ────────────────────────────────────────────────────
    def compute_isolation_score(self, feature_df: pd.DataFrame) -> np.ndarray:
        features = [
            'declared_income_pkr', 'total_asset_value', 'vehicle_count',
            'max_vehicle_cc', 'property_count', 'avg_monthly_bill_pkr',
            'annual_utility_bill', 'transfer_count'
        ]
        available = [f for f in features if f in feature_df.columns]
        X = feature_df[available].fillna(0).copy()

        X['declared_income_pkr']  = X.get('declared_income_pkr',  pd.Series(dtype=float)).clip(upper=_INCOME_CAP)
        X['total_asset_value']     = X.get('total_asset_value',     pd.Series(dtype=float)).clip(upper=_ASSET_CAP)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        iso = IsolationForest(contamination=0.15, random_state=42, n_estimators=100)
        iso.fit(X_scaled)
        raw = iso.decision_function(X_scaled)
        rng = raw.max() - raw.min()
        normalized = 1 - (raw - raw.min()) / (rng + 1e-9)
        return normalized * 100

    def compute_graph_features(self, graph, person_ids):
        centrality_scores = {}
        if graph is not None:
            try:
                betweenness = nx.betweenness_centrality(graph)
                degree      = nx.degree_centrality(graph)
                for pid in person_ids:
                    bc = betweenness.get(pid, 0)
                    dc = degree.get(pid, 0)
                    centrality_scores[pid] = min((bc + dc) * 100, 15)
            except Exception:
                centrality_scores = {pid: 0 for pid in person_ids}
        return centrality_scores

    def compute_risk_contamination(self, person_id, base_scores, graph):
        if graph is None:
            return 0
        try:
            neighbors = list(graph.neighbors(person_id))
            if not neighbors:
                return 0
            avg_n = np.mean([base_scores.get(n, 0) for n in neighbors])
            return min(avg_n * 0.15, 15)
        except Exception:
            return 0

    # ── Master scorer ─────────────────────────────────────────────────────────
    def calculate_master_score(self, row, df_full=None, graph=None,
                                base_scores=None, precomputed_centralities=None):
        pid          = _safe_str(row.get('master_person_id'), '')
        vehicle_val  = self.get_vehicle_value(row.get('max_vehicle_cc', 0)) \
                       * _safe_int(row.get('vehicle_count', 0))
        property_val = _safe_float(row.get('total_property_value', 0))
        total_assets = vehicle_val + property_val

        annual_util     = _safe_float(row.get('avg_monthly_bill_pkr', 0)) * 12
        declared_income = _safe_float(row.get('declared_income_pkr', 0))

        # ── Lifestyle score ────────────────────────────────────────────────
        lifestyle_cost = annual_util + (total_assets * 0.05)
        if declared_income <= 0:
            base_lifestyle = min(lifestyle_cost / 200_000 * 10, 100)
        else:
            ratio = lifestyle_cost / declared_income
            base_lifestyle = min(ratio * 8, 100)

        # ── Forensic modules ───────────────────────────────────────────────
        forensic_scores = {
            'benami_proxy':          self.detect_benami_proxy(
                                         row.get('occupation'), total_assets, declared_income),
            'family_ring':           self.detect_family_ring(pid, graph),
            'corporate_shield':      self.detect_corporate_shield(row.get('buyer_name')),
            'dc_underinvoicing':     self.detect_dc_rate_underinvoicing(
                                         row.get('property_value_pkr', 0),
                                         row.get('area_marla', 0),
                                         row.get('reported_address', '')),
            'file_trading':          self.detect_file_trading(
                                         row.get('registry_type'), row.get('filer_status')),
            'property_flipping':     self.detect_property_flipping(
                                         row.get('transfer_count', 0),
                                         row.get('years_active', 2),
                                         declared_income),
            'illegal_society':       self.detect_illegal_society(
                                         row.get('noc_status'), property_val),
            'agri_shield':           self.detect_agri_shield(
                                         row.get('income_source'), declared_income, total_assets),
            'section_111_abuse':     self.detect_section_111_abuse(
                                         row.get('wealth_source'), total_assets, declared_income),
            'gift_declaration':      self.detect_gift_declaration(
                                         row.get('wealth_source'), total_assets),
            'prize_bond':            self.detect_prize_bond_laundering(
                                         row.get('income_source'), declared_income),
            'vehicle_underinvoicing':self.detect_vehicle_underinvoicing(
                                         row.get('declared_import_value_pkr', 0),
                                         row.get('vehicle_make_model'),
                                         row.get('max_vehicle_cc', 0)),
            'nonfiler_surcharge':    self.detect_nonfiler_surcharge_buyin(
                                         row.get('filer_status'), vehicle_val,
                                         row.get('years_as_nonfiler', 0)),
            'hawala_signature':      self.detect_hawala_signature(
                                         total_assets, declared_income,
                                         row.get('wealth_source'),
                                         row.get('has_bank_account', True)),
            'rental_concealment':    self.detect_rental_concealment(
                                         row.get('property_count', 0),
                                         row.get('income_source'),
                                         row.get('filer_status')),
            'duplicate_registry':    self.detect_duplicate_registry(
                                         row.get('registry_no'), df_full),
            'baggage_scheme':        self.detect_baggage_scheme_abuse(
                                         row.get('import_type'),
                                         row.get('vehicle_count', 0)),
        }

        fired_flags    = {k: v for k, v in forensic_scores.items() if v > 0}
        top_flags      = sorted(fired_flags.items(), key=lambda x: x[1], reverse=True)[:3]
        forensic_total = sum(forensic_scores.values())

        centrality_bonus = (precomputed_centralities or {}).get(pid, 0)
        contamination    = self.compute_risk_contamination(pid, base_scores or {}, graph)

        # ── Final weighted formula ─────────────────────────────────────────
        final_score = (
            base_lifestyle   * 0.20 +
            forensic_total   * 0.55 +
            centrality_bonus * 0.10 +
            contamination    * 0.15
        )

        # Extreme-income, clean-profile guard (fixes outlier score of 62 for Rs.100B income)
        if (declared_income > _INCOME_CAP and
                forensic_total < 20 and
                _safe_str(row.get('filer_status')) == 'ATL'):
            final_score = min(final_score, 30)

        return {
            'deviation_score':        min(round(final_score, 1), 100),
            'total_assets_estimated': total_assets,
            'lifestyle_cost_annual':  lifestyle_cost,
            'top_fraud_flags':        top_flags,
            'forensic_breakdown':     forensic_scores,
            'risk_category':          self._categorize(min(final_score, 100)),
        }

    def _categorize(self, score):
        if   score >= 80: return 'CRITICAL'
        elif score >= 65: return 'HIGH'
        elif score >= 45: return 'MEDIUM'
        elif score >= 25: return 'LOW'
        else:             return 'COMPLIANT'


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline entry point
# ══════════════════════════════════════════════════════════════════════════════
def process_master_csv(input_csv="outputs/master_entities.csv",
                       output_csv="outputs/scored_entities.csv"):
    print(f"Loading data from {input_csv}...")
    try:
        df = pd.read_csv(input_csv)
    except FileNotFoundError:
        print(f"Error: {input_csv} not found. Run entity_resolution.py first.")
        return

    engine = ShaheenForensicEngine()

    # Load graph
    graph = None
    graph_path = "outputs/shaheen_graph.pkl"
    if os.path.exists(graph_path):
        try:
            with open(graph_path, 'rb') as f:
                graph = pickle.load(f)
            print("Graph loaded.")
        except Exception as e:
            print(f"Graph load error: {e}")

    # Precompute centralities once
    precomputed_centralities = None
    if graph is not None:
        print("Computing graph centralities…")
        precomputed_centralities = engine.compute_graph_features(
            graph, df['master_person_id'].tolist())

    # ── Pass 1: base scores (no contamination) ────────────────────────────
    print("Pass 1 — base scores…")
    base_scores = {}
    pass1_results = []
    for idx, row in df.iterrows():
        res = engine.calculate_master_score(
            row, df_full=df, graph=graph,
            base_scores=None,
            precomputed_centralities=precomputed_centralities)
        base_scores[row['master_person_id']] = res['deviation_score']
        pass1_results.append(res)

    # ── Pass 2: add contamination ──────────────────────────────────────────
    print("Pass 2 — risk contamination…")
    final_results = []
    for idx, row in df.iterrows():
        res = engine.calculate_master_score(
            row, df_full=df, graph=graph,
            base_scores=base_scores,
            precomputed_centralities=precomputed_centralities)
        final_results.append(res)

    # ── Isolation Forest ───────────────────────────────────────────────────
    print("Running Isolation Forest…")
    for col in ['declared_income_pkr', 'total_asset_value', 'vehicle_count',
                'max_vehicle_cc', 'property_count', 'avg_monthly_bill_pkr',
                'annual_utility_bill', 'transfer_count']:
        if col not in df.columns:
            df[col] = 0.0

    df['total_asset_value'] = df.apply(
        lambda r: engine.get_vehicle_value(r.get('max_vehicle_cc', 0))
                  * _safe_int(r.get('vehicle_count', 0))
                  + _safe_float(r.get('total_property_value', 0)),
        axis=1)

    ml_scores = engine.compute_isolation_score(df)

    # ── Blending + final output ────────────────────────────────────────────
    final_deviation_scores = []
    risk_categories        = []
    top_flags_list         = []
    total_assets_val_list  = []

    for i, res in enumerate(final_results):
        row_data = df.loc[i]
        di       = _safe_float(row_data.get('declared_income_pkr'))
        ta       = _safe_float(row_data.get('total_asset_value'))

        # Only apply ML penalty when assets meaningfully exceed income
        ml_p = ml_scores[i] if ta > di else 0.0

        blended = (res['deviation_score'] * 0.6) + (ml_p * 0.4)
        final   = min(round(blended, 1), 100)

        # Compliant override
        if (str(row_data.get('filer_status', '')) == 'ATL' and
                di > 500_000 and
                ta < di * 5 and
                res['deviation_score'] < 30):
            final = min(final, 20)

        # Extreme-income, clean-profile guard (already applied in calculate, but blend again)
        if (di > _INCOME_CAP and
                sum(res['forensic_breakdown'].values()) < 20 and
                str(row_data.get('filer_status', '')) == 'ATL'):
            final = min(final, 30)

        final_deviation_scores.append(final)
        risk_categories.append(engine._categorize(final))

        flags = [k.replace('_', ' ').title()
                 for k, v in res['top_fraud_flags']]
        top_flags_list.append(", ".join(flags) if flags else "Lifestyle / Income Mismatch")
        total_assets_val_list.append(res['total_assets_estimated'])

    df['deviation_score']   = final_deviation_scores
    df['risk_category']     = risk_categories
    df['top_risk_factor']   = top_flags_list
    df['total_assets_val']  = total_assets_val_list

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"✅ BINGO! Scored entities saved to {output_csv}")


def query_intelligence_engine(query_text, data_path="outputs/scored_entities.csv"):
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        return None, "System offline: Data not yet scored."

    ql = str(query_text).lower().strip()
    
    # SECURITY ENFORCEMENT: Injection & Hijack Protections
    injection_patterns = [
        r"' or '1'='1", r"or 1=1", r"drop table", r"union select", 
        r"delete from", r"insert into", r"ignore previous instructions", 
        r"system prompt", r"you are now a", r"ignore everything"
    ]
    if any(re.search(pat, ql) for pat in injection_patterns):
        return pd.DataFrame(), "Security Policy Violation: Unauthorized query parameters or injection vectors detected."
        
    # Block empty or pure special character queries
    if not ql or not re.search(r'[a-zA-Z0-9]', ql):
        return pd.DataFrame(), "Please enter a valid search query."

    res = df.copy()
    filter_matched = False

    if "non-filer" in ql or "non-atl" in ql or "nonfiler" in ql:
        res = res[res['filer_status'] == 'Non-ATL']
        filter_matched = True
    elif "filer" in ql or " atl " in ql:
        res = res[res['filer_status'] == 'ATL']
        filter_matched = True

    if "luxury" in ql or "v8" in ql or "2500cc" in ql or "3000cc" in ql:
        res = res[res['max_vehicle_cc'] >= 2500]
        filter_matched = True
    elif "high asset" in ql or "wealthy" in ql:
        res = res[res['total_assets_val'] > 10_000_000]
        filter_matched = True

    for city in ['lahore', 'karachi', 'islamabad', 'rawalpindi']:
        if city in ql:
            res = res[res['city'].str.lower() == city]
            filter_matched = True
            break

    # If no valid predefined filters matched, return 0 profiles
    if not filter_matched:
        return pd.DataFrame(), "No profiles match. Try different terms."

    results = res.head(15)
    summary = f"Query found {len(res)} profiles."
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content":
                f"One sentence for FBR auditor: '{query_text}' → "
                f"{len(res)} profiles, avg score "
                f"{res['deviation_score'].mean():.0f}/100."}],
            temperature=0.1, max_tokens=100)
        summary = response.choices[0].message.content.strip()
    except Exception:
        pass

    return results, summary


if __name__ == "__main__":
    process_master_csv()
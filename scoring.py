import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import networkx as nx

class ShaheenForensicEngine:
    
    def __init__(self):
        # City-specific market rates per marla (PKR) - Updated 2025
        self.market_rates = {
            "dha": 3500000, "defence": 4000000, "bahria": 2200000,
            "gulberg": 3000000, "e-11": 4500000, "f-6": 5000000,
            "f-7": 4800000, "g-10": 2500000, "g-11": 2800000,
            "clifton": 4000000, "pechs": 2800000, "nazimabad": 1800000,
            "johar": 1600000, "faisalabad": 1200000, "multan": 1000000,
            "rawalpindi": 1800000, "peshawar": 1500000, "default": 800000
        }
        
        # Proxy/Benami occupation list
        self.proxy_occupations = [
            'driver', 'housewife', 'student', 'peon', 'servant',
            'retired', 'unemployed', 'security guard', 'cook',
            'gardener', 'clerk', 'dependent', 'none'
        ]
        
        # Luxury vehicle makes for import fraud detection
        self.luxury_vehicles = [
            'land cruiser', 'prado', 'fortuner', 'lexus', 'bmw',
            'mercedes', 'audi', 'porsche', 'range rover', 'hilux',
            'camry', 'crown'
        ]
        
        # Vehicle market value lookup (PKR)
        self.vehicle_values = {
            (0, 800): 800000,
            (800, 1000): 1200000,
            (1000, 1300): 2200000,
            (1300, 1600): 3000000,
            (1600, 1800): 3500000,
            (1800, 2000): 5000000,
            (2000, 2500): 8000000,
            (2500, 3000): 10000000,
            (3000, 9999): 15000000
        }

    # ==========================================
    # UTILITY FUNCTIONS
    # ==========================================
    
    def get_vehicle_value(self, cc):
        cc = float(cc) if cc else 0
        for (low, high), val in self.vehicle_values.items():
            if low <= cc < high:
                return val
        return 800000

    def get_market_rate(self, address):
        addr = str(address).lower()
        for area, rate in self.market_rates.items():
            if area in addr:
                return rate
        return self.market_rates["default"]

    # ==========================================
    # CATEGORY 1: BENAMI / ASSET CONCEALMENT
    # ==========================================
    
    def detect_benami_proxy(self, occupation, total_assets, declared_income):
        """Fraud 1: Low-income proxy holding high-value assets"""
        score = 0
        occ = str(occupation).lower()
        if any(p in occ for p in self.proxy_occupations):
            if total_assets > 5000000:
                score += 65
            elif total_assets > 2000000:
                score += 40
        if declared_income < 400000 and total_assets > 10000000:
            score += 40
        return min(score, 100)

    def detect_family_ring(self, person_id, graph):
        """Fraud 2: Zero-income family ring sharing address"""
        if graph is None:
            return 0
        try:
            neighbors = list(graph.neighbors(person_id))
            shared_addr_neighbors = [
                n for n in neighbors
                if graph.edges[person_id, n].get('type') == 'SHARES_ADDRESS'
            ]
            if len(shared_addr_neighbors) >= 2:
                return 55
            elif len(shared_addr_neighbors) == 1:
                return 25
        except:
            pass
        return 0

    def detect_corporate_shield(self, buyer_name):
        """Fraud 3: Shell company or trust holding assets"""
        shield_keywords = [
            'enterprises', 'associates', 'holdings', 'trust',
            'pvt', 'limited', 'brothers', 'sons', 'trading'
        ]
        name = str(buyer_name).lower()
        if any(k in name for k in shield_keywords):
            return 45
        return 0

    # ==========================================
    # CATEGORY 2: PROPERTY FRAUD
    # ==========================================
    
    def detect_dc_rate_underinvoicing(self, declared_val, area_marla, address):
        """Fraud 4: Property declared at DC rate, paid at market rate in cash"""
        market_rate = self.get_market_rate(address)
        real_market_val = float(area_marla or 0) * market_rate
        if real_market_val == 0:
            return 0
        ratio = float(declared_val or 0) / real_market_val
        if ratio < 0.15:
            return 55  # Declared < 15% of market = extreme under-invoicing
        elif ratio < 0.30:
            return 45  # Declared < 30% = significant under-invoicing
        elif ratio < 0.50:
            return 25  # Declared < 50% = moderate under-invoicing
        return 0

    def detect_file_trading(self, registry_type, filer_status):
        """Fraud 5: Off-radar property file trading to avoid FBR documentation"""
        file_types = ['file', 'allotment letter', 'transfer letter', 'open file']
        rtype = str(registry_type).lower()
        if any(f in rtype for f in file_types) and filer_status == 'Non-ATL':
            return 40
        elif any(f in rtype for f in file_types):
            return 20
        return 0

    def detect_property_flipping(self, transfer_count, years_span, declared_income):
        """Fraud 6: Rapid property flipping to cycle black money"""
        if transfer_count is None:
            return 0
        velocity = float(transfer_count) / max(float(years_span or 1), 0.5)
        score = 0
        if velocity > 3:  # More than 3 sales per year
            score += 40
        elif velocity > 1.5:
            score += 25
        if float(declared_income or 0) < 1000000 and float(transfer_count or 0) > 2:
            score += 20
        return min(score, 60)

    def detect_illegal_society(self, noc_status, property_value):
        """Fraud 7: Investment in unapproved housing society"""
        illegal_statuses = ['unapproved', 'illegal', 'pending', 'cancelled', 'encroachment']
        status = str(noc_status).lower()
        if any(s in status for s in illegal_statuses):
            if float(property_value or 0) > 10000000:
                return 35
            return 20
        return 0

    # ==========================================
    # CATEGORY 3: INCOME WHITENING
    # ==========================================
    
    def detect_agri_shield(self, income_source, declared_income, total_assets):
        """Fraud 8: Using tax-exempt agricultural income to justify luxury assets"""
        if 'agri' in str(income_source).lower():
            if total_assets > 50000000:
                return 40
            elif total_assets > 20000000:
                return 25
        return 0

    def detect_section_111_abuse(self, wealth_source, total_assets, prior_income_history):
        """Fraud 9: Hawala loop — send black money abroad, receive back as 'remittance'"""
        remittance_keywords = ['remittance', 'foreign transfer', 'overseas', 'nrp', 'gift from abroad']
        ws = str(wealth_source).lower()
        if any(k in ws for k in remittance_keywords):
            if float(total_assets or 0) > 20000000 and float(prior_income_history or 0) < 2000000:
                return 50  # Sudden massive wealth with no income history
            elif float(total_assets or 0) > 10000000:
                return 30
        return 0

    def detect_gift_declaration(self, wealth_source, asset_value):
        """Fraud 10: Claiming luxury assets as 'gifts' to avoid source explanation"""
        gift_keywords = ['gift', 'inheritance', 'hiba', 'donation', 'bequest']
        ws = str(wealth_source).lower()
        if any(k in ws for k in gift_keywords):
            if float(asset_value or 0) > 20000000:
                return 50
            elif float(asset_value or 0) > 10000000:
                return 35
            elif float(asset_value or 0) > 5000000:
                return 20
        return 0

    def detect_prize_bond_laundering(self, income_source, declared_amount):
        """Fraud 11: Using prize bonds to launder black money"""
        if 'prize' in str(income_source).lower() or 'bond' in str(income_source).lower():
            if float(declared_amount or 0) > 10000000:
                return 35
        return 0

    # ==========================================
    # CATEGORY 4: VEHICLE FRAUD
    # ==========================================
    
    def detect_vehicle_underinvoicing(self, declared_import_value, vehicle_make_model, engine_cc):
        """Fraud 12: Luxury vehicle under-invoiced at customs using Hawala"""
        if not declared_import_value or float(declared_import_value) == 0:
            return 0
        estimated_market = self.get_vehicle_value(engine_cc)
        model = str(vehicle_make_model).lower()
        is_luxury = any(lv in model for lv in self.luxury_vehicles)
        if is_luxury:
            estimated_market *= 1.5  # Luxury premium
        ratio = float(declared_import_value) / estimated_market
        if ratio < 0.10:
            return 55  # Declared < 10% = extreme fraud (like the Rs.17,635 Land Cruiser case)
        elif ratio < 0.25:
            return 40
        elif ratio < 0.50:
            return 20
        return 0

    def detect_nonfiler_surcharge_buyin(self, filer_status, vehicle_value, years_as_nonfiler):
        """Fraud 13: Non-filer treating surcharge as a 'fee' to stay undocumented"""
        if filer_status == 'Non-ATL' and float(vehicle_value or 0) > 3000000:
            if int(years_as_nonfiler or 0) > 3:
                return 40  # Deliberately staying non-ATL for years
            return 25
        return 0

    def detect_baggage_scheme_abuse(self, import_type, vehicle_count, vehicle_values_list):
        """Fraud 14: Fake overseas Pakistani using baggage scheme repeatedly"""
        if 'baggage' in str(import_type).lower():
            if int(vehicle_count or 0) > 1:
                return 45  # One vehicle allowed per returning Pakistani
        return 0

    # ==========================================
    # CATEGORY 5: NETWORK/STRUCTURAL FRAUD
    # ==========================================
    
    def detect_duplicate_registry(self, registry_no, df):
        """Fraud 15: Same plot sold to multiple buyers (double registry)"""
        if df is None or not registry_no:
            return 0
        try:
            count = df[df['registry_no'] == registry_no]['master_person_id'].nunique()
            if count > 1:
                return 60
        except:
            pass
        return 0

    def detect_hawala_signature(self, total_assets, declared_income, wealth_source, has_bank_account):
        """Fraud 16: Profile consistent with Hawala/cash-based wealth"""
        score = 0
        cash_sources = ['cash', 'unknown', 'undisclosed', 'none', '']
        ws = str(wealth_source).lower()
        if float(total_assets or 0) > 20000000 and float(declared_income or 0) < 500000:
            if any(c in ws for c in cash_sources):
                score += 55
            if not has_bank_account:
                score += 20
        return min(score, 75)

    def detect_rental_concealment(self, property_count, income_source, filer_status):
        """Fraud 18: Multiple properties, zero rental income declared"""
        if int(property_count or 0) >= 2:
            if 'rental' not in str(income_source).lower() and 'rent' not in str(income_source).lower():
                if filer_status == 'Non-ATL':
                    return 35
                return 15
        return 0

    # ==========================================
    # ML LAYER: ISOLATION FOREST
    # ==========================================
    
    def compute_isolation_score(self, feature_df):
        """Unsupervised ML anomaly detection on the full population"""
        features = [
            'declared_income_pkr', 'total_asset_value', 'vehicle_count',
            'max_vehicle_cc', 'property_count', 'avg_monthly_bill_pkr',
            'annual_utility_bill', 'transfer_count'
        ]
        available = [f for f in features if f in feature_df.columns]
        X = feature_df[available].fillna(0)
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        iso = IsolationForest(contamination=0.15, random_state=42, n_estimators=100)
        iso.fit(X_scaled)
        
        raw_scores = iso.decision_function(X_scaled)
        # Normalize to 0-100: more negative = more anomalous = higher score
        normalized = 1 - (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-9)
        return normalized * 100

    # ==========================================
    # GRAPH LAYER: CENTRALITY + COMMUNITY
    # ==========================================
    
    def compute_graph_features(self, graph, person_ids):
        """Compute betweenness centrality and community membership"""
        centrality_scores = {}
        community_risk = {}
        
        if graph is not None:
            try:
                betweenness = nx.betweenness_centrality(graph)
                degree = nx.degree_centrality(graph)
                for pid in person_ids:
                    if pid in betweenness:
                        # Normalize centrality to 0-15 bonus points
                        bc = betweenness.get(pid, 0)
                        dc = degree.get(pid, 0)
                        centrality_scores[pid] = min((bc + dc) * 100, 15)
                    else:
                        centrality_scores[pid] = 0
            except:
                centrality_scores = {pid: 0 for pid in person_ids}
        
        return centrality_scores

    # ==========================================
    # RISK PROPAGATION: CONTAMINATION
    # ==========================================
    
    def compute_risk_contamination(self, person_id, base_scores, graph):
        """Guilt-by-association: connected high-risk people raise your score"""
        if graph is None:
            return 0
        try:
            neighbors = list(graph.neighbors(person_id))
            if not neighbors:
                return 0
            neighbor_scores = [base_scores.get(n, 0) for n in neighbors]
            avg_neighbor_score = np.mean(neighbor_scores)
            return min(avg_neighbor_score * 0.15, 15)  # Max 15 contamination points
        except:
            return 0

    # ==========================================
    # MASTER INTEGRATOR
    # ==========================================
    
    def calculate_master_score(self, row, df_full=None, graph=None, base_scores=None):
        """
        The complete forensic scoring engine.
        Combines 18 fraud modules + Isolation Forest + Graph Centrality + Contamination
        """
        pid = row.get('master_person_id', '')
        
        # Compute all assets value
        vehicle_val = self.get_vehicle_value(row.get('max_vehicle_cc', 0)) * int(row.get('vehicle_count', 0) or 0)
        property_val = float(row.get('total_property_value', 0) or 0)
        total_assets = vehicle_val + property_val
        
        annual_utility = float(row.get('avg_monthly_bill_pkr', 0) or 0) * 12
        declared_income = float(row.get('declared_income_pkr', 0) or 0)
        
        # BASE LIFESTYLE SCORE
        lifestyle_cost = annual_utility + (total_assets * 0.05)
        if declared_income <= 0:
            base_lifestyle = min(lifestyle_cost / 200000 * 10, 100)
        else:
            ratio = lifestyle_cost / declared_income
            base_lifestyle = min(ratio * 8, 100)
        
        # ALL 18 FORENSIC MODULE SCORES
        forensic_scores = {
            'benami_proxy': self.detect_benami_proxy(
                row.get('occupation', ''), total_assets, declared_income),
            'family_ring': self.detect_family_ring(pid, graph),
            'corporate_shield': self.detect_corporate_shield(row.get('buyer_name', '')),
            'dc_underinvoicing': self.detect_dc_rate_underinvoicing(
                row.get('property_value_pkr', 0), row.get('area_marla', 0), row.get('reported_address', '')),
            'file_trading': self.detect_file_trading(
                row.get('registry_type', ''), row.get('filer_status', '')),
            'property_flipping': self.detect_property_flipping(
                row.get('transfer_count', 0), row.get('years_active', 2), declared_income),
            'illegal_society': self.detect_illegal_society(
                row.get('noc_status', ''), property_val),
            'agri_shield': self.detect_agri_shield(
                row.get('income_source', ''), declared_income, total_assets),
            'section_111_abuse': self.detect_section_111_abuse(
                row.get('wealth_source', ''), total_assets, declared_income),
            'gift_declaration': self.detect_gift_declaration(
                row.get('wealth_source', ''), total_assets),
            'prize_bond': self.detect_prize_bond_laundering(
                row.get('income_source', ''), declared_income),
            'vehicle_underinvoicing': self.detect_vehicle_underinvoicing(
                row.get('declared_import_value_pkr', 0),
                row.get('vehicle_make_model', ''), row.get('max_vehicle_cc', 0)),
            'nonfiler_surcharge': self.detect_nonfiler_surcharge_buyin(
                row.get('filer_status', ''), vehicle_val, row.get('years_as_nonfiler', 0)),
            'hawala_signature': self.detect_hawala_signature(
                total_assets, declared_income,
                row.get('wealth_source', ''), row.get('has_bank_account', True)),
            'rental_concealment': self.detect_rental_concealment(
                row.get('property_count', 0), row.get('income_source', ''), row.get('filer_status', '')),
            'duplicate_registry': self.detect_duplicate_registry(
                row.get('registry_no', ''), df_full),
        }
        
        # TOP FRAUD FLAGS (for UI display — what fired)
        fired_flags = {k: v for k, v in forensic_scores.items() if v > 0}
        top_flags = sorted(fired_flags.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # COMBINED FORENSIC TOTAL
        forensic_total = sum(forensic_scores.values())
        
        # GRAPH CENTRALITY BONUS
        centrality_bonus = 0
        if graph is not None:
            try:
                bc = nx.betweenness_centrality(graph).get(pid, 0)
                dc = nx.degree_centrality(graph).get(pid, 0)
                centrality_bonus = min((bc + dc) * 100, 15)
            except:
                pass
        
        # CONTAMINATION SCORE
        contamination = self.compute_risk_contamination(pid, base_scores or {}, graph)
        
        # FINAL WEIGHTED SCORE
        final_score = (
            base_lifestyle * 0.20 +      # 20% lifestyle math
            forensic_total * 0.55 +       # 55% forensic modules (the beef)
            centrality_bonus * 0.10 +     # 10% graph centrality
            contamination * 0.15          # 15% guilt-by-association
        )
        
        return {
            'deviation_score': min(round(final_score, 1), 100),
            'total_assets_estimated': total_assets,
            'lifestyle_cost_annual': lifestyle_cost,
            'top_fraud_flags': top_flags,
            'forensic_breakdown': forensic_scores,
            'risk_category': self._categorize(final_score)
        }
    
    def _categorize(self, score):
        if score >= 80: return 'CRITICAL'
        elif score >= 65: return 'HIGH'
        elif score >= 45: return 'MEDIUM'
        elif score >= 25: return 'LOW'
        else: return 'COMPLIANT'
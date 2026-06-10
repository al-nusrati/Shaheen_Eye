import os
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class ShaheenScorer:
    def __init__(self):
        self.vehicle_weights = {
            "luxury": 10.0,   # > 2500cc
            "premium": 5.0,   # 1800cc - 2500cc
            "standard": 1.5,  # 1000cc - 1300cc
            "economy": 0.5    # < 1000cc
        }

    def get_vehicle_tier(self, cc):
        if cc >= 2500: return "luxury"
        if cc >= 1800: return "premium"
        if cc >= 1000: return "standard"
        return "economy"

    def calculate_deviation(self, income, assets_value, annual_bill):
        estimated_annual_expense = (annual_bill * 12) + (assets_value * 0.05)
        if income <= 0:
            score = (estimated_annual_expense / 100000) * 2 
        else:
            ratio = estimated_annual_expense / income
            score = ratio * 10
        return min(max(score, 0), 100)

    def run_ml_anomaly(self, df):
        features = ['declared_income', 'total_assets_val', 'annual_utility_bill']
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(df[features])
        model = IsolationForest(contamination=0.1, random_state=42)
        outlier_scores = model.decision_function(scaled_data)
        ml_scores = (outlier_scores - outlier_scores.min()) / (outlier_scores.max() - outlier_scores.min())
        return (1 - ml_scores) * 100

    def get_final_score(self, rule_score, ml_score):
        return (rule_score * 0.6) + (ml_score * 0.4)

# ---------------------------------------------------------
# pipeline functions
# ---------------------------------------------------------

def process_master_csv(input_csv="outputs/master_entities.csv", output_csv="outputs/scored_entities.csv"):
    """Reads Person 1's data, applies scores, and creates the file Person C needs for the Dashboard."""
    print(f"Loading data from {input_csv}...")
    try:
        df = pd.read_csv(input_csv)
    except FileNotFoundError:
        print(f"Waiting for Person 1 to generate {input_csv}...")
        return
    
    scorer = ShaheenScorer()
    final_scores = []
    risk_factors = []
    
    for idx, row in df.iterrows():
        rule_score = scorer.calculate_deviation(
            income=row['declared_income'], 
            assets_value=row['total_assets_val'], 
            annual_bill=row['annual_utility_bill']
        )
        
        if row['declared_income'] == 0 and row['total_assets_val'] > 5000000:
            risk = "Zero Filer with High Assets"
        elif row['max_vehicle_cc'] >= 2500:
            risk = "Luxury Vehicle Flag"
        elif row['annual_utility_bill'] > 1000000 and row['filer_status'] == 'Non-ATL':
            risk = "Excessive Utility Consumption"
        else:
            risk = "Lifestyle / Income Mismatch"
            
        final_scores.append(rule_score)
        risk_factors.append(risk)
        
    df['deviation_score'] = final_scores
    df['top_risk_factor'] = risk_factors
    
    os.makedirs("outputs", exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"✅ Scored Data successfully saved to {output_csv} for Person C's Dashboard!")


def query_intelligence_engine(query_text, data_path="outputs/scored_entities.csv"):
    """
    Screen 4 Brain: Natural Language Query Processor.
    Filters database using keywords and uses Groq to generate a 1-line summary.
    """
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        return None, "System offline: Data not yet scored."

    query_text = query_text.lower()
    filtered_df = df.copy()

    # 1. Apply Rule Filters based on keywords
    if "non-filer" in query_text or "non-atl" in query_text:
        filtered_df = filtered_df[filtered_df['filer_status'] == 'Non-ATL']
    elif "filer" in query_text or "atl" in query_text:
        filtered_df = filtered_df[filtered_df['filer_status'] == 'ATL']

    if "luxury" in query_text or "v8" in query_text or "2500cc" in query_text:
        filtered_df = filtered_df[filtered_df['max_vehicle_cc'] >= 2500]
    elif "high asset" in query_text:
        filtered_df = filtered_df[filtered_df['total_assets_val'] > 10000000]

    # City filter matches
    for city in ['lahore', 'karachi', 'islamabad', 'rawalpindi']:
        if city in query_text:
            filtered_df = filtered_df[filtered_df['city'].str.lower() == city]

    # Limit to top 15 results for safety
    results = filtered_df.head(15)
    
    # 2. Use LLM to write a 1-line Smart Executive Summary
    summary_prompt = f"""
    You are an FBR Intelligence analyst. Write exactly ONE short, professional sentence
    summarizing this query result.
    Query: '{query_text}'
    Result count: {len(filtered_df)} profiles found out of {len(df)} total.
    """
    
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.1,
            max_tokens=100
        )
        summary = response.choices[0].message.content.strip()
    except Exception:
        summary = f"Query found {len(filtered_df)} profiles matching criteria."

    return results, summary


if __name__ == "__main__":
    scorer = ShaheenScorer()
    test_score = scorer.calculate_deviation(income=0, assets_value=12000000, annual_bill=300000)
    print(f"Testing Math Formula -> Score: {test_score}/100")
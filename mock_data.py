import pandas as pd

def get_mock_entities():
    return pd.DataFrame([
        {"master_person_id": "PK-001", "full_name": "Ch. Muhammad Arshad",
         "city": "Lahore", "deviation_score": 97, "risk_category": "CRITICAL",
         "filer_status": "Non-ATL", "declared_income_pkr": 0,
         "total_assets_estimated": 14500000, "vehicle_make_model": "Toyota Land Cruiser",
         "max_vehicle_cc": 3000, "avg_monthly_bill_pkr": 280000,
         "top_fraud_flags": "Benami Proxy, DC Rate Fraud, File Trading",
         "occupation": "Businessman", "property_count": 1, "vehicle_count": 1},
        # Add all 10 personas here with their exact scores
        {"master_person_id": "PK-010", "full_name": "Ali Raza",
         "city": "Islamabad", "deviation_score": 11, "risk_category": "COMPLIANT",
         "filer_status": "ATL", "declared_income_pkr": 1800000,
         "total_assets_estimated": 850000, "vehicle_make_model": "Suzuki Alto",
         "max_vehicle_cc": 660, "avg_monthly_bill_pkr": 8000,
         "top_fraud_flags": "None", "occupation": "Engineer",
         "property_count": 0, "vehicle_count": 1},
    ])
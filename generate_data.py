import os
import pandas as pd
import random

def build_raw_datasets():
    # Setup folders matching the repo structure
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("outputs/reports", exist_ok=True)
    
    # --- Persona Data definitions ---
    personas = {
        "P1": {"name": "Ch. Muhammad Arshad", "phone": "0300-1112223", "address": "DHA Phase 6, Lahore"},
        "P2": {"name": "Farhan Ahmed", "phone": "0300-0000001", "address": "House 5, Street 2, Gulberg III, Lahore"},
        "P3": {"name": "Rabia Ahmed", "phone": "0300-0000002", "address": "House 5, Street 2, Gulberg III, Lahore"},
        "P4": {"name": "Kamran Ahmed", "phone": "0300-0000003", "address": "House 5, Street 2, Gulberg III, Lahore"},
        "P5": {"name": "Bashir Ahmed", "phone": "0300-0000004", "address": "House 5, Street 2, Gulberg III, Lahore"},
        "P6": {"name": "Syed Bilal Hassan", "phone": "0321-5556667", "address": "Sector C, Bahria Town, Rawalpindi"},
        "P7": {"name": "Dr. Ayesha Malik", "phone": "0333-9998887", "address": "Bahria Town Phase 7, Islamabad"},
        "P8": {"name": "Haji Abdul Razzaq", "phone": "0345-4443332", "address": "Pechs Block 2, Karachi"},
        "P9": {"name": "Tariq Mehmood", "phone": "0312-8887776", "address": "Phase 2, Hayatabad, Peshawar"},
        "P10": {"name": "Ali Raza", "phone": "0322-7776665", "address": "Flat 4, Block D, I-8, Islamabad"}
    }

    # 1. FBR TAX RECORDS
    fbr_records = [
        {"fbr_id": "FBR-7712", "full_name": personas["P1"]["name"], "declared_income_pkr": 0, "tax_paid_pkr": 0, "filer_status": "Non-ATL", "reported_address": personas["P1"]["address"], "phone_number": personas["P1"]["phone"], "income_source": "Cash", "wealth_source": "Cash", "occupation": "Businessman", "years_as_nonfiler": 5, "has_bank_account": False},
        {"fbr_id": "FBR-9012", "full_name": personas["P2"]["name"], "declared_income_pkr": 0, "tax_paid_pkr": 0, "filer_status": "Non-ATL", "reported_address": personas["P2"]["address"], "phone_number": personas["P2"]["phone"], "income_source": "Cash", "wealth_source": "Cash", "years_as_nonfiler": 4, "has_bank_account": False},
        {"fbr_id": "FBR-9013", "full_name": personas["P3"]["name"], "declared_income_pkr": 0, "tax_paid_pkr": 0, "filer_status": "Non-ATL", "reported_address": personas["P3"]["address"], "phone_number": personas["P3"]["phone"], "income_source": "None", "wealth_source": "Gift", "years_as_nonfiler": 3, "has_bank_account": True},
        {"fbr_id": "FBR-9014", "full_name": personas["P4"]["name"], "declared_income_pkr": 180000, "tax_paid_pkr": 0, "filer_status": "Non-ATL", "reported_address": personas["P4"]["address"], "phone_number": personas["P4"]["phone"], "income_source": "Salary", "wealth_source": "Savings", "years_as_nonfiler": 2, "has_bank_account": True},
        {"fbr_id": "FBR-9015", "full_name": personas["P5"]["name"], "declared_income_pkr": 180000, "tax_paid_pkr": 0, "filer_status": "Non-ATL", "reported_address": personas["P5"]["address"], "phone_number": personas["P5"]["phone"], "income_source": "Salary", "wealth_source": "Cash", "years_as_nonfiler": 1, "has_bank_account": False},
        {"fbr_id": "FBR-5124", "full_name": personas["P6"]["name"], "declared_income_pkr": 600000, "tax_paid_pkr": 15000, "filer_status": "ATL", "reported_address": personas["P6"]["address"], "phone_number": personas["P6"]["phone"], "income_source": "Salary", "wealth_source": "Foreign Remittance", "years_as_nonfiler": 0, "has_bank_account": True},
        {"fbr_id": "FBR-1189", "full_name": personas["P7"]["name"], "declared_income_pkr": 2400000, "tax_paid_pkr": 240000, "filer_status": "ATL", "reported_address": personas["P7"]["address"], "phone_number": personas["P7"]["phone"], "income_source": "Agriculture", "wealth_source": "Savings", "years_as_nonfiler": 0, "has_bank_account": True},
        {"fbr_id": "FBR-3321", "full_name": personas["P8"]["name"], "declared_income_pkr": 0, "tax_paid_pkr": 0, "filer_status": "Non-ATL", "reported_address": personas["P8"]["address"], "phone_number": personas["P8"]["phone"], "income_source": "None", "wealth_source": "Cash", "years_as_nonfiler": 7, "has_bank_account": False},
        {"fbr_id": "FBR-8890", "full_name": personas["P9"]["name"], "declared_income_pkr": 1200000, "tax_paid_pkr": 60000, "filer_status": "ATL", "reported_address": personas["P9"]["address"], "phone_number": personas["P9"]["phone"], "income_source": "Business", "wealth_source": "Savings", "years_as_nonfiler": 0, "has_bank_account": True},
        {"fbr_id": "FBR-4412", "full_name": personas["P10"]["name"], "declared_income_pkr": 1800000, "tax_paid_pkr": 180000, "filer_status": "ATL", "reported_address": personas["P10"]["address"], "phone_number": personas["P10"]["phone"], "income_source": "Salary", "wealth_source": "Savings", "years_as_nonfiler": 0, "has_bank_account": True}
    ]
    
    first_names = ["Muhammad", "Ali", "Ahmed", "Fatima", "Ayesha", "Zainab", "Osman", "Hamza", "Bilal", "Sana"]
    last_names = ["Khan", "Sheikh", "Malik", "Ahmed", "Raza", "Hassan", "Siddiqui", "Bibi", "Javed", "Iqbal"]
    cities = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Peshawar", "Faisalabad"]
    occupations = ["Engineer", "Teacher", "Doctor", "Driver", "Businessman", "Unemployed"]

    for i in range(11, 501):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        income = random.choice([0, 300000, 600000, 1200000, 2500000])
        status = "ATL" if income > 500000 and random.random() > 0.3 else "Non-ATL"
        fbr_records.append({
            "fbr_id": f"FBR-{1000 + i}", "full_name": name, "declared_income_pkr": income,
            "tax_paid_pkr": int(income * 0.1), "filer_status": status,
            "reported_address": f"House {random.randint(1,100)}, Sector {random.choice(['A', 'B', 'C', 'D'])}, {random.choice(cities)}",
            "phone_number": f"0300-{random.randint(1000000, 9999999)}", "income_source": random.choice(["Salary", "Business", "Agriculture"]),
            "wealth_source": "Savings", "occupation": random.choice(occupations),
            "years_as_nonfiler": random.randint(0, 5) if status == "Non-ATL" else 0, "has_bank_account": random.choice([True, False])
        })
    pd.DataFrame(fbr_records).to_csv("data/raw/fbr_tax_records.csv", index=False)

    # 2. EXCISE VEHICLES
    excise_records = [
        {"vehicle_reg_no": "LED-1234", "owner_name": "M. Arshad", "engine_capacity_cc": 3000, "vehicle_make_model": "Toyota Land Cruiser", "registration_year": 2025, "owner_address": "DHA Phase 6, Lahore", "import_type": "Baggage Scheme", "declared_import_value_pkr": 20000},
        {"vehicle_reg_no": "LEG-5678", "owner_name": "Farhan Ahmed", "engine_capacity_cc": 2700, "vehicle_make_model": "Toyota Fortuner", "registration_year": 2024, "owner_address": "House 5, Street 2, Gulberg III, Lahore", "import_type": "Local", "declared_import_value_pkr": 0},
        {"vehicle_reg_no": "LEH-9012", "owner_name": "Rabia Ahmed", "engine_capacity_cc": 1800, "vehicle_make_model": "Honda Civic", "registration_year": 2023, "owner_address": "House 5, Street 2, Gulberg III, Lahore", "import_type": "Local", "declared_import_value_pkr": 0},
        {"vehicle_reg_no": "LEJ-3456", "owner_name": "Kamran Ahmed", "engine_capacity_cc": 1300, "vehicle_make_model": "Toyota Corolla", "registration_year": 2022, "owner_address": "House 5, Street 2, Gulberg III, Lahore", "import_type": "Local", "declared_import_value_pkr": 0},
        {"vehicle_reg_no": "LEK-7890", "owner_name": "Bashir Ahmed", "engine_capacity_cc": 2000, "vehicle_make_model": "Toyota Prado", "registration_year": 2025, "owner_address": "House 5, Street 2, Gulberg III, Lahore", "import_type": "Local", "declared_import_value_pkr": 0},
        {"vehicle_reg_no": "Rin-2412", "owner_name": "Syed Bilal Hassan", "engine_capacity_cc": 1800, "vehicle_make_model": "Honda Civic", "registration_year": 2021, "owner_address": "Sector C, Bahria Town, Rawalpindi", "import_type": "Local", "declared_import_value_pkr": 0},
        {"vehicle_reg_no": "IDN-9980", "owner_name": "Dr. Ayesha Malik", "engine_capacity_cc": 2700, "vehicle_make_model": "Toyota Fortuner", "registration_year": 2024, "owner_address": "Bahria Town Phase 7, Islamabad", "import_type": "Local", "declared_import_value_pkr": 0},
        {"vehicle_reg_no": "IDN-1122", "owner_name": "Tariq Mehmood", "engine_capacity_cc": 3444, "vehicle_make_model": "Toyota Land Cruiser", "registration_year": 2025, "owner_address": "Phase 2, Hayatabad, Peshawar", "import_type": "Regular Import", "declared_import_value_pkr": 17635},
        {"vehicle_reg_no": "IDN-4455", "owner_name": "Ali Raza", "engine_capacity_cc": 660, "vehicle_make_model": "Suzuki Alto", "registration_year": 2021, "owner_address": "Flat 4, Block D, I-8, Islamabad", "import_type": "Local", "declared_import_value_pkr": 850000}
    ]
    for i in range(10, 300):
        excise_records.append({
            "vehicle_reg_no": f"REG-{random.randint(1000, 9999)}",
            "owner_name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "engine_capacity_cc": random.choice([660, 1000, 1300, 1800, 2700]),
            "vehicle_make_model": random.choice(["Suzuki Alto", "Toyota Corolla", "Honda Civic"]),
            "registration_year": random.randint(2018, 2026),
            "owner_address": f"Street {random.randint(1,10)}, Phase {random.randint(1,8)}, {random.choice(cities)}",
            "import_type": "Local", "declared_import_value_pkr": 0
        })
    pd.DataFrame(excise_records).to_csv("data/raw/excise_vehicles.csv", index=False)

    # 3. DISCO UTILITY CONSUMPTION
    disco_records = [
        {"meter_ref_no": "MTR-1001", "consumer_name": "Muhammad Arshad", "installation_address": "DHA Phase 6, Lahore", "avg_monthly_bill_pkr": 280000, "connection_type": "Domestic"},
        {"meter_ref_no": "MTR-1002", "consumer_name": "Farhan Ahmed", "installation_address": "House 5, Street 2, Gulberg III, Lahore", "avg_monthly_bill_pkr": 120000, "connection_type": "Domestic"},
        {"meter_ref_no": "MTR-1003", "consumer_name": "Haji Abdul Razzaq", "installation_address": "Pechs Block 2, Karachi", "avg_monthly_bill_pkr": 150000, "connection_type": "Commercial"},
        {"meter_ref_no": "MTR-1004", "consumer_name": "Ali Raza", "installation_address": "Flat 4, Block D, I-8, Islamabad", "avg_monthly_bill_pkr": 8000, "connection_type": "Domestic"}
    ]
    for i in range(5, 400):
        disco_records.append({
            "meter_ref_no": f"MTR-{2000 + i}",
            "consumer_name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "installation_address": f"House {random.randint(1,100)}, Street {random.randint(1,10)}, {random.choice(cities)}",
            "avg_monthly_bill_pkr": random.randint(5000, 45000), "connection_type": "Domestic"
        })
    pd.DataFrame(disco_records).to_csv("data/raw/disco_consumption.csv", index=False)

    # 4. PROPERTY TRANSFERS
    prop_records = [
        {"registry_no": "REG-PRO-101", "buyer_name": "Muhammad Arshad", "seller_name": "Malik Riaz", "property_address": "DHA Phase 6, Lahore", "property_value_pkr": 2500000, "transfer_date": "2025-01-15", "area_marla": 20, "property_type": "Residential", "registry_type": "File", "noc_status": "Approved", "society_name": "DHA Lahore", "plot_number": "Plot 14"},
        {"registry_no": "REG-PRO-102", "buyer_name": "Farhan Ahmed", "seller_name": "Zubair Khan", "property_address": "House 5, Street 2, Gulberg III, Lahore", "property_value_pkr": 80000000, "transfer_date": "2024-03-10", "area_marla": 20, "property_type": "Residential", "registry_type": "Registry", "noc_status": "Approved", "society_name": "Gulberg", "plot_number": "House 5"},
        {"registry_no": "REG-PRO-103", "buyer_name": "Syed Bilal Hassan", "seller_name": "Properties Ltd", "property_address": "Sector C, Bahria Town, Rawalpindi", "property_value_pkr": 15000000, "transfer_date": "2025-02-20", "area_marla": 10, "property_type": "Residential", "registry_type": "File", "noc_status": "Approved", "society_name": "Bahria Town", "plot_number": "Plot 99"},
        {"registry_no": "REG-PRO-104", "buyer_name": "Dr. Ayesha Malik", "seller_name": "Capital Builders", "property_address": "Bahria Town Phase 7, Islamabad", "property_value_pkr": 30000000, "transfer_date": "2024-06-12", "area_marla": 8, "property_type": "Apartment", "registry_type": "Registry", "noc_status": "Approved", "society_name": "Bahria Town", "plot_number": "Apartment 3A"},
        {"registry_no": "REG-PRO-105", "buyer_name": "Haji Abdul Razzaq", "seller_name": "Ali Hassan", "property_address": "Pechs Block 2, Karachi", "property_value_pkr": 80000000, "transfer_date": "2019-11-05", "area_marla": 40, "property_type": "Commercial", "registry_type": "Registry", "noc_status": "Approved", "society_name": "Pechs Karachi", "plot_number": "Plaza 4"}
    ]
    for i in range(6, 150):
        prop_records.append({
            "registry_no": f"REG-PRO-{200 + i}",
            "buyer_name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "seller_name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "property_address": f"Plot {random.randint(10,500)}, Sector {random.choice(['A','B','C'])}, {random.choice(cities)}",
            "property_value_pkr": random.randint(3000000, 25000000),
            "transfer_date": f"{random.randint(2018,2026)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "area_marla": random.choice([5, 10, 20]), "property_type": "Residential",
            "registry_type": random.choice(["Registry", "File"]), "noc_status": random.choice(["Approved", "Unapproved", "Pending"]),
            "society_name": "Local Scheme", "plot_number": f"Plot {random.randint(1,500)}"
        })
    pd.DataFrame(prop_records).to_csv("data/raw/property_transfers.csv", index=False)
    print("✅ Step 1 complete. Raw data created in data/raw/")

if __name__ == "__main__":
    build_raw_datasets()
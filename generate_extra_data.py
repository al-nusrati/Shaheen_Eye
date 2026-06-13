"""
generate_minimal_rings.py — Generate minimal dataset (8 people) with two fraud rings.
Outputs (./test_rings_minimal/):
    fbr_tax_records_mini.csv
    excise_vehicles_mini.csv
    disco_consumption_mini.csv
    property_transfers_mini.csv
Run: python generate_minimal_rings.py
"""
import os
import random
import pandas as pd

random.seed(42)

# ----------------------------------------------------------------------
# Data for rings
# ----------------------------------------------------------------------
RING_ADDRESS = "House 10, Gulberg, Lahore"
RING_PHONE = "0300-1234567"

# Ring 1: 3 persons sharing same address
ring1_names = ["Ayesha Siddiqui", "Bilal Ahmed", "Fatima Raza"]
# Ring 2: 3 persons sharing same phone
ring2_names = ["Hassan Ali", "Zara Malik", "Omar Farooq"]
# Singletons: 2 individuals with unique details
singleton_names = ["Sana Khan", "Usman Chaudhry"]

# ----------------------------------------------------------------------
# FBR records
# ----------------------------------------------------------------------
fbr_records = []

def generate_phone():
    return f"03{random.randint(10,49)}-{random.randint(1000000, 9999999)}"

next_id = 8000

# Ring 1 – shared address, different phones, low income, Non-ATL
for name in ring1_names:
    fbr_records.append({
        "fbr_id": f"FBR-{next_id}",
        "full_name": name,
        "declared_income_pkr": random.choice([0, 240000]),
        "tax_paid_pkr": 0,
        "filer_status": "Non-ATL",
        "reported_address": RING_ADDRESS,
        "phone_number": generate_phone(),
        "income_source": "Cash",
        "wealth_source": "Cash",
        "occupation": random.choice(["Driver", "Housewife", "Student"]),
        "years_as_nonfiler": random.randint(2, 5),
        "has_bank_account": False,
    })
    next_id += 1

# Ring 2 – shared phone, different addresses, higher income, ATL
for name in ring2_names:
    city = random.choice(["Lahore", "Karachi"])
    area = random.choice(["DHA", "Gulberg"])
    fbr_records.append({
        "fbr_id": f"FBR-{next_id}",
        "full_name": name,
        "declared_income_pkr": random.choice([1200000, 1800000]),
        "tax_paid_pkr": random.randint(10000, 50000),
        "filer_status": "ATL",
        "reported_address": f"House {random.randint(1,50)}, {area}, {city}",
        "phone_number": RING_PHONE,
        "income_source": "Salary",
        "wealth_source": "Savings",
        "occupation": random.choice(["Engineer", "Businessman"]),
        "years_as_nonfiler": 0,
        "has_bank_account": True,
    })
    next_id += 1

# Singletons – unique address and phone
for name in singleton_names:
    city = random.choice(["Islamabad", "Rawalpindi"])
    area = random.choice(["F-7", "Bahria Town"])
    fbr_records.append({
        "fbr_id": f"FBR-{next_id}",
        "full_name": name,
        "declared_income_pkr": random.choice([480000, 960000]),
        "tax_paid_pkr": random.randint(5000, 20000),
        "filer_status": "ATL" if random.random() > 0.3 else "Non-ATL",
        "reported_address": f"House {random.randint(1,100)}, {area}, {city}",
        "phone_number": generate_phone(),
        "income_source": random.choice(["Salary", "Business"]),
        "wealth_source": "Savings",
        "occupation": random.choice(["Teacher", "Doctor"]),
        "years_as_nonfiler": 0 if random.random() > 0.5 else random.randint(1,3),
        "has_bank_account": True,
    })
    next_id += 1

# ----------------------------------------------------------------------
# Excise vehicles – each person may have a vehicle
# ----------------------------------------------------------------------
VEHICLES = [(660, "Suzuki Alto"), (1300, "Toyota Corolla"), (1800, "Honda Civic"),
            (2000, "Toyota Prado"), (2700, "Toyota Fortuner")]
excise_records = []
for idx, person in enumerate(fbr_records):
    if random.random() < 0.6:   # 60% own a vehicle
        cc, model = random.choice(VEHICLES)
        excise_records.append({
            "vehicle_reg_no": f"MINI-{idx}{random.randint(100,999)}",
            "owner_name": person["full_name"],
            "engine_capacity_cc": cc,
            "vehicle_make_model": model,
            "registration_year": random.randint(2018, 2025),
            "owner_address": person["reported_address"],
            "import_type": "Local" if cc < 2000 else random.choice(["Local", "Imported"]),
            "declared_import_value_pkr": 0 if cc < 2000 else random.randint(500000, 2000000),
        })

# ----------------------------------------------------------------------
# DISCO utility records – one per person
# ----------------------------------------------------------------------
disco_records = []
for idx, person in enumerate(fbr_records):
    # Higher bill for Gulberg addresses (ring1)
    if "Gulberg" in person["reported_address"]:
        bill = random.randint(80000, 150000)
    else:
        bill = random.randint(5000, 50000)
    disco_records.append({
        "meter_ref_no": f"MTR-MINI{idx+1}",
        "consumer_name": person["full_name"],
        "installation_address": person["reported_address"],
        "avg_monthly_bill_pkr": bill,
        "connection_type": "Domestic",
    })

# ----------------------------------------------------------------------
# Property transfers – about 30% own property
# ----------------------------------------------------------------------
property_records = []
for idx, person in enumerate(fbr_records):
    if random.random() < 0.3:
        area_marla = random.choice([5, 10, 20])
        value = area_marla * random.randint(800000, 3500000)
        property_records.append({
            "registry_no": f"REG-MINI-{idx+100}",
            "buyer_name": person["full_name"],
            "seller_name": random.choice(["ABC Builders", "XYZ Estate"]),
            "property_address": person["reported_address"],
            "property_value_pkr": value,
            "transfer_date": f"202{random.randint(2,5)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "area_marla": area_marla,
            "property_type": "Residential",
            "registry_type": random.choice(["Registry", "File"]),
            "noc_status": random.choice(["Approved", "Approved", "Pending"]),
            "society_name": random.choice(["DHA", "Bahria Town"]),
            "plot_number": f"Plot {random.randint(1,300)}",
        })

# ----------------------------------------------------------------------
# Save to folder (static name, will overwrite previous runs)
# ----------------------------------------------------------------------
out_dir = "test_rings_minimal"
os.makedirs(out_dir, exist_ok=True)

pd.DataFrame(fbr_records).to_csv(f"{out_dir}/fbr_tax_records_mini.csv", index=False)
pd.DataFrame(excise_records).to_csv(f"{out_dir}/excise_vehicles_mini.csv", index=False)
pd.DataFrame(disco_records).to_csv(f"{out_dir}/disco_consumption_mini.csv", index=False)
pd.DataFrame(property_records).to_csv(f"{out_dir}/property_transfers_mini.csv", index=False)

print(f"✅ Generated {len(fbr_records)} people ({len(ring1_names)} address ring, {len(ring2_names)} phone ring, {len(singleton_names)} singles).")
print(f"Files saved in ./{out_dir}/")
print("\nAfter uploading & merging these files, the Fraud Rings page will show:")
print("  - Ring 1 (shared address):", ", ".join(ring1_names))
print("  - Ring 2 (shared phone):   ", ", ".join(ring2_names))
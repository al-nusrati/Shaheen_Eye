import os
import json
import pandas as pd
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are a Senior Forensic Investigator at the FBR Intelligence & Investigation Wing (IIW), 
Islamabad. You specialize in detecting Pakistani tax evasion tactics.

When analyzing a citizen profile, specifically identify which of these 
Pakistani-specific evasion methods are present:

BENAMI: Assets registered under drivers, housewives, students, or retired parents
DC-RATE FRAUD: Property declared at DC value while market value is 4-10x higher  
FILE TRADING: Assets held as open allotment files to avoid formal land registry
SECTION 111(4) ABUSE: Black money sent abroad via Hawala, returned as 'remittance'
AGRICULTURAL SHIELD: Using tax-exempt agri-income to justify unexplained luxury
GIFT DECLARATION: Claiming crore-value assets as family gifts
HAWALA SIGNATURE: High-value assets with zero documented income trail
NON-FILER SURCHARGE BUY-IN: Paying penalty once to buy luxury, never filing again
ILLEGAL SOCIETY: Investment in NOC-unapproved housing schemes

Write exactly 3 paragraphs:
PARAGRAPH 1: Identify the specific Jugaar(s) detected. Use exact figures. Name the scam.
PARAGRAPH 2: Cite the violated law — Benami Transactions (Prohibition) Act 2017, 
             Income Tax Ordinance 2001 Section 111/37/68, or Anti-Money Laundering Act 2010.
PARAGRAPH 3: Recommended action — "Issue show-cause notice under Section 122(9)", 
             "Freeze assets under Benami Act Section 24", or "Refer to FIA for AML investigation."

Tone: Cold. Legal. Authoritative. No hedging. Write as if this document will be used in court.
"""

def generate_fbr_report(person_name, asset_details, score):
    user_content = f"SUBJECT: {person_name}, SCORE: {score}/100, ASSETS: {asset_details}"
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Error: {str(e)}"

def cache_target_personas_reports(scored_csv="outputs/scored_entities.csv", output_json="outputs/audit_trails.json"):
    """
    Scans the scored entities, finds the 10 critical personas, 
    generates their legal reports, and caches them to disk.
    """
    print("Reading scored entities...")
    if not os.path.exists(scored_csv):
        print(f"Error: {scored_csv} not found. Run scoring.py first.")
        return
        
    df = pd.read_csv(scored_csv)
    
    # List of our 10 presentation targets
    target_names = [
        "Ch. Muhammad Arshad", "Farhan Ahmed", "Rabia Ahmed", "Kamran Ahmed", 
        "Bashir Ahmed", "Syed Bilal Hassan", "Dr. Ayesha Malik", 
        "Haji Abdul Razzaq", "Tariq Mehmood", "Ali Raza"
    ]
    
    cache = {}
    
    # Load existing cache if it exists to avoid rewriting
    if os.path.exists(output_json):
        try:
            with open(output_json, 'r') as f:
                cache = json.load(f)
        except:
            pass

    print(f"Generating and caching reports for {len(target_names)} personas...")
    for name in target_names:
        matched = df[df['full_name'] == name]
        if matched.empty:
            print(f"⚠️ Warning: Persona '{name}' not found in the database. Check generate_data.py")
            continue
            
        row = matched.iloc[0]
        pid = row['master_person_id']
        
        # Skip if already cached
        if pid in cache:
            print(f"✓ '{name}' already cached. Skipping.")
            continue
            
        print(f"Generating report for: {name} (Score: {row['deviation_score']})")
        assets = row.get('asset_summary', f"CC: {row['max_vehicle_cc']}, Properties: {row['property_count']}")
        report_text = generate_fbr_report(name, assets, row['deviation_score'])
        
        cache[pid] = report_text

    # Write out the JSON cache file
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, 'w') as f:
        json.dump(cache, f, indent=4)
        
    print(f"✅ Step complete. Audit trail cache saved to {output_json}")

if __name__ == "__main__":
    cache_target_personas_reports()
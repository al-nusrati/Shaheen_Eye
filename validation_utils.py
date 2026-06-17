import re
import pandas as pd
from datetime import datetime, timedelta

def validate_cnic(cnic_str: str) -> dict:
    """
    Validates a Pakistani CNIC (13 digits, optionally hyphenated: XXXXX-XXXXXXX-X)
    and extracts geographical and gender information according to NADRA guidelines.
    """
    if not cnic_str:
        return {"valid": False, "reason": "Empty input."}
        
    # Clean string and extract digits
    digits = re.sub(r'\D', '', cnic_str)
    
    if len(digits) != 13:
        return {"valid": False, "reason": f"CNIC must contain exactly 13 digits (found {len(digits)})."}
        
    # First digit decodes the province
    prov_code = int(digits[0])
    provinces = {
        1: "Khyber Pakhtunkhwa (KPK)",
        2: "Federally Administered Tribal Areas (FATA)",
        3: "Punjab",
        4: "Sindh",
        5: "Balochistan",
        6: "Islamabad (Capital Territory)",
        7: "Gilgit-Baltistan"
    }
    
    # Third digit decodes tehsil/district info (general validation range 1-9)
    district_code = int(digits[2])
    
    # Last digit decodes gender (Odd = Male, Even = Female)
    gender_digit = int(digits[12])
    gender = "Male" if gender_digit % 2 != 0 else "Female"
    
    province_name = provinces.get(prov_code)
    if not province_name:
        return {"valid": False, "reason": f"Invalid province code '{prov_code}' in starting digit."}
        
    formatted_cnic = f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
    
    return {
        "valid": True,
        "cnic": formatted_cnic,
        "province": province_name,
        "gender": gender,
        "region_code": digits[:5]
    }

def validate_ntn(ntn_str: str) -> dict:
    """
    Validates a Pakistani National Tax Number (NTN) using Modulus-11 checksum.
    Standard format: XXXXXXX-X (7 digits + 1 check digit)
    """
    if not ntn_str:
        return {"valid": False, "reason": "Empty input."}
        
    # Clean string and extract digits
    digits = re.sub(r'\D', '', ntn_str)
    
    if len(digits) != 8:
        return {"valid": False, "reason": f"NTN must contain exactly 8 digits (found {len(digits)})."}
        
    # Modulus 11 algorithm weights
    weights = [8, 7, 6, 5, 4, 3, 2]
    
    total = sum(int(digits[i]) * weights[i] for i in range(7))
    remainder = total % 11
    
    # Calculate check digit
    check_digit = (11 - remainder) % 11
    if check_digit == 10:
        check_digit = 0  # 10 is normalized to 0 in standard FBR checks
        
    provided_check = int(digits[7])
    is_valid = (check_digit == provided_check)
    
    formatted_ntn = f"{digits[:7]}-{digits[7]}"
    
    if is_valid:
        return {
            "valid": True,
            "ntn": formatted_ntn
        }
    else:
        return {
            "valid": False,
            "reason": f"Checksum failed. Calculated check digit is {check_digit}, but provided was {provided_check}.",
            "ntn": formatted_ntn
        }

def detect_smurfing_structuring(df_transactions: pd.DataFrame, 
                                threshold: float = 2500000.0, 
                                margin: float = 150000.0, 
                                days_window: int = 3) -> pd.DataFrame:
    """
    Detects potential 'Smurfing' (transaction structuring) patterns.
    Looks for multiple transactions from the same entity that are slightly
    below the FMU cash reporting threshold (e.g. 2.5 Million PKR) within a rolling window.
    
    Parameters:
    - df_transactions: DataFrame containing columns: ['sender_id', 'amount', 'date']
      where 'date' can be parsed as a datetime.
    - threshold: The reporting limit (default 2,500,000 PKR).
    - margin: How close to the limit to look (e.g. between 2.35M and 2.49M).
    - days_window: Rolling time window size in days.
    """
    # Ensure correct types
    df = df_transactions.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['sender_id', 'date'])
    
    # Filter transactions within suspicious margin: [threshold - margin, threshold]
    lower_bound = threshold - margin
    suspicious_txs = df[(df['amount'] >= lower_bound) & (df['amount'] < threshold)].copy()
    
    flags = []
    
    # Group by sender to inspect transaction history
    for sender_id, group in suspicious_txs.groupby('sender_id'):
        if len(group) < 2:
            continue
            
        group = group.reset_index(drop=True)
        
        # Slide window across transactions
        for i in range(len(group)):
            start_date = group.loc[i, 'date']
            end_date = start_date + timedelta(days=days_window)
            
            # Find all suspicious transactions inside this window
            window_txs = group[(group['date'] >= start_date) & (group['date'] <= end_date)]
            
            if len(window_txs) >= 2:
                total_value = window_txs['amount'].sum()
                tx_dates = [d.strftime('%Y-%m-%d %H:%M') for d in window_txs['date']]
                tx_amounts = window_txs['amount'].tolist()
                
                flags.append({
                    "sender_id": sender_id,
                    "suspicious_tx_count": len(window_txs),
                    "total_structured_amount": total_value,
                    "window_start": start_date.strftime('%Y-%m-%d'),
                    "window_end": end_date.strftime('%Y-%m-%d'),
                    "transaction_dates": tx_dates,
                    "transaction_amounts": tx_amounts
                })
                
    # Deduplicate overlapping flags for same sender
    if not flags:
        return pd.DataFrame(columns=[
            "sender_id", "suspicious_tx_count", "total_structured_amount", 
            "window_start", "window_end", "transaction_dates", "transaction_amounts"
        ])
        
    flags_df = pd.DataFrame(flags)
    flags_df = flags_df.drop_duplicates(subset=['sender_id', 'suspicious_tx_count', 'total_structured_amount'])
    return flags_df.sort_values(by="total_structured_amount", ascending=False)

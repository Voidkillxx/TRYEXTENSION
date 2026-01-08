import requests
import zipfile
import io
import os

# --- CONFIGURATION ---
WHITELIST_FILE = "whitelist.txt"
TOP_N = 1000000  
TRANCO_URL = "https://tranco-list.eu/top-1m.csv.zip"

# Your specific PH focus list (Manual Override)
MANUAL_LIST = [
    "google.com", "forms.gle", "docs.google.com", "drive.google.com", "accounts.google.com",
    "youtube.com", "gmail.com", "pinnacle.pnc.edu.ph", "pnc.edu.ph", "globalreporting.org",
    "facebook.com", "messenger.com", "microsoft.com", "apple.com", "netflix.com",
    "abs-cbn.com", "gmanetwork.com", "rappler.com", "inquirer.net", "gcash.com",
    "maya.ph", "mayabank.ph", "coins.ph", "grab.com", "shopeepay.com.ph",
    "gotyme.com.ph", "tonikbank.com", "uniondigitalbank.io", "uno.bank", "ofbank.com.ph",
    "bdo.com.ph", "bpi.com.ph", "metrobank.com.ph", "unionbankph.com", "pnb.com.ph",
    "rcbc.com", "securitybank.com", "landbank.com", "chinabank.ph", "psbank.com.ph",
    "shopee.ph", "lazada.com.ph", "foodpanda.ph", "toktok.ph", "gov.ph",
    "sss.gov.ph", "pagibigfund.gov.ph", "philhealth.gov.ph", "bir.gov.ph",
    "dti.gov.ph", "sec.gov.ph", "dfa.gov.ph", "poea.gov.ph", "prc.gov.ph","pinnacle.pnc.edu.ph"
]

def update_whitelist():
    print(f"🌍 Downloading Top {TOP_N} Global Sites (Tranco List)...")
    final_domains = set()

    # 1. Add Manual List first (Priority)
    for domain in MANUAL_LIST:
        final_domains.add(domain.strip().lower())
    print(f"   ✅ Added {len(final_domains)} manual PH domains.")

    # 2. Download & Parse Global List
    try:
        r = requests.get(TRANCO_URL)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        
        # The zip contains a CSV like: "1,google.com"
        with z.open(z.namelist()[0]) as f:
            for i, line in enumerate(f):
                if i >= TOP_N: 
                    break
                # Decode bytes to string, split by comma, get the domain part
                parts = line.decode('utf-8').strip().split(',')
                if len(parts) >= 2:
                    domain = parts[1]
                    final_domains.add(domain)
                    
        print(f"   ✅ Merged with Global Top {TOP_N} sites.")
        
    except Exception as e:
        print(f"   ❌ Error fetching global list: {e}")
        print("   ⚠️ Saving only manual list.")

    # 3. Save to file
    with open(WHITELIST_FILE, "w") as f:
        for domain in sorted(final_domains):
            f.write(domain + "\n")

    print(f"💾 Saved {len(final_domains)} safe domains to {WHITELIST_FILE}")

if __name__ == "__main__":
    update_whitelist()
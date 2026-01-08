import sqlite3
import pandas as pd
import kagglehub
import os
from ucimlrepo import fetch_ucirepo 

# --- CONFIGURATION ---
DB_NAME = "threats.db"

def get_kaggle_data():
    print("⬇️ Fetching Kaggle Data...")
    try:
        path = kagglehub.dataset_download("harisudhan411/phishing-and-legitimate-urls")
        csv_file = None
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(".csv"):
                    csv_file = os.path.join(root, file)
                    break
        
        if csv_file:
            df = pd.read_csv(csv_file)
            df.columns = [c.lower() for c in df.columns]
            if 'status' in df.columns: df = df.rename(columns={'status': 'label'})
            print(f"   ✅ Loaded {len(df)} rows from Kaggle")
            return df[['url', 'label']]
    except Exception as e:
        print(f"   ❌ Kaggle Error: {e}")
    return pd.DataFrame()

def get_phiusiil_data():
    print("⬇️ Fetching PhiUSIIL Data (UCI)...")
    try:
        phiusiil = fetch_ucirepo(id=967) 
        df = phiusiil.data.original
        df.columns = [c.lower() for c in df.columns]
        print(f"   ✅ Loaded {len(df)} rows from PhiUSIIL")
        return df[['url', 'label']]
    except Exception as e:
        print(f"   ❌ PhiUSIIL Error: {e}")
    return pd.DataFrame()

def standardize_label(val):
    """
    STRICT LOGIC FIX (User Request):
    0 = Phishing (DANGER)
    1 = Safe (SAFE)
    """
    val_str = str(val).lower().strip()
    
    # DANGER GROUP
    # Includes: '0', 'phishing', 'bad', 'malicious'
    if val_str in ['0', 'phishing', 'bad', 'danger', 'malicious']:
        return "DANGER"
    
    # SAFE GROUP
    # Includes: '1', 'legitimate', 'safe', 'good'
    elif val_str in ['1', 'legitimate', 'safe', 'good', 'benign']:
        return "SAFE"
        
    return "DANGER" # Fail-safe: Assume danger if unsure

# --- MAIN EXECUTION ---
print("--- 🛠️ FIXING DATABASE LABELS ---")

# 1. Get Data
df1 = get_kaggle_data()
df2 = get_phiusiil_data()

# 2. Merge
print("🔄 Merging Datasets...")
df_final = pd.concat([df1, df2], ignore_index=True)

# 3. Clean & Standardize
print("🧹 Applying NEW Logic (0=Danger, 1=Safe)...")
df_final.drop_duplicates(subset=['url'], inplace=True)

# Apply the fixed function
df_final['status'] = df_final['label'].apply(standardize_label)

# Rename url to content for DB match
df_final.rename(columns={'url': 'content'}, inplace=True)
df_db = df_final[['content', 'status']]

# 4. Save to Database
print(f"💾 Overwriting database with {len(df_db)} corrected rows...")
try:
    conn = sqlite3.connect(DB_NAME)
    # 'if_exists="replace"' deletes the old bad data and writes the new good data
    df_db.to_sql('training_samples', conn, if_exists='replace', index=False)
    conn.close()
    print("✅ SUCCESS! Database repaired.")
    print("   Example check: 'firebaseapp' entries should now be DANGER.")
except Exception as e:
    print(f"❌ Database Error: {e}")
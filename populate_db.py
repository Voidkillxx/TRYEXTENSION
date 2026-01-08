import sqlite3
import pandas as pd
import kagglehub
import os
import time
import threading
import sys
from ucimlrepo import fetch_ucirepo 

# --- CONFIGURATION ---
DB_NAME = "threats.db"

# --- LIVE TIMER HELPER ---
class LiveTimer:
    def __init__(self, message="Processing"):
        self.message = message
        self.stop_event = threading.Event()
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._run)

    def start(self):
        self.stop_event.clear()
        self.start_time = time.time()
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join()
        sys.stdout.write("\n") 

    def _run(self):
        while not self.stop_event.is_set():
            elapsed = int(time.time() - self.start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            sys.stdout.write(f"\r⏳ {self.message}... [ {minutes:02d}m {seconds:02d}s ]")
            sys.stdout.flush()
            time.sleep(1)

# --- DATA FUNCTIONS ---

def get_kaggle_data():
    timer = LiveTimer("Fetching Kaggle Data")
    timer.start()
    df_result = pd.DataFrame()
    
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
            timer.stop()
            print(f"✅ Loaded {len(df)} rows from Kaggle")
            return df[['url', 'label']]
            
    except Exception as e:
        timer.stop()
        print(f"❌ Kaggle Error: {e}")
    
    timer.stop()
    return df_result

def get_phiusiil_data():
    print("⬇️  Checking for PhiUSIIL Data...")
    
    possible_files = [
        "phiusiil_cached.csv",
        "PhiUSIIL_Phishing_URL_Dataset.csv"
    ]

    for filename in possible_files:
        if os.path.exists(filename):
            print(f"   📂 Found local file: {filename}")
            try:
                df = pd.read_csv(filename)
                df.columns = [c.lower() for c in df.columns]
                print(f"   ✅ Loaded {len(df)} rows from local file (Instant)")
                return df[['url', 'label']]
            except Exception as e:
                print(f"   ❌ Error reading {filename}: {e}")

    # Download from UCI if local file missing
    timer = LiveTimer("Downloading from UCI")
    timer.start()
    try:
        phiusiil = fetch_ucirepo(id=967) 
        df = phiusiil.data.original
        df.columns = [c.lower() for c in df.columns]
        df.to_csv("phiusiil_cached.csv", index=False)
        timer.stop()
        print(f"   ✅ Downloaded {len(df)} rows and SAVED to phiusiil_cached.csv")
        return df[['url', 'label']]
    except Exception as e:
        timer.stop()
        print(f"   ⚠️ UCI Download failed: {e}")

    return pd.DataFrame()

# --- NEW: PHISHTANK LOADER ---
def get_phishtank_data():
    print("⬇️  Checking for PhishTank Data...")
    filename = "verified_online.csv"

    if os.path.exists(filename):
        print(f"   📂 Found local file: {filename}")
        try:
            df = pd.read_csv(filename)
            # PhishTank file has a 'url' column. All entries in this file are confirmed phishing.
            # We select only the URL and manually assign the label.
            df = df[['url']].copy()
            df['label'] = 'phishing' 
            print(f"   ✅ Loaded {len(df)} rows from PhishTank")
            return df
        except Exception as e:
            print(f"   ❌ Error reading {filename}: {e}")
    else:
        print(f"   ⚠️ File {filename} not found. Skipping PhishTank.")

    return pd.DataFrame()

# --- HELPER LOGIC ---

def standardize_label(label):
    """
    Standardizes labels to 'phishing' or 'legitimate'
    """
    s = str(label).lower().strip()
    
    # Check for Phishing (0, 'phishing', 'verified')
    if s == '0' or s == 'phishing' or s == 'verified':
        return 'phishing'
    
    # Check for Legitimate (1, 'legitimate')
    if s == '1' or s == 'legitimate':
        return 'legitimate'
        
    return 'legitimate' # Default fallback

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("--- 🛠️ FIXING DATABASE LABELS ---")
    
    # 1. Get All Datasets
    df1 = get_kaggle_data()
    df2 = get_phiusiil_data()
    df3 = get_phishtank_data() # New PhishTank Data

    if df1.empty and df2.empty and df3.empty:
        print("❌ CRITICAL ERROR: No data loaded. Please check your internet or files.")
        exit()

    # 2. Merge
    print("🔄 Merging Datasets...")
    df_final = pd.concat([df1, df2, df3], ignore_index=True)

    # 3. Clean
    print("🧹 Cleaning & Applying CORRECTED Logic...")
    df_final.drop_duplicates(subset=['url'], inplace=True)
    
    # Apply standardizer
    df_final['status'] = df_final['label'].apply(standardize_label)
    
    df_final.rename(columns={'url': 'content'}, inplace=True)
    df_db = df_final[['content', 'status']]

    # 4. Save
    print(f"💾 Saving {len(df_db)} rows to database...")
    save_timer = LiveTimer("Writing to Disk")
    save_timer.start()
    
    try:
        conn = sqlite3.connect(DB_NAME)
        df_db.to_sql('training_samples', conn, if_exists='replace', index=False)
        conn.close()
        save_timer.stop()
        print("✅ SUCCESS! Database updated with PhishTank data.")
    except Exception as e:
        save_timer.stop()
        print(f"❌ Database Error: {e}")
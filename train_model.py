import sqlite3
import pandas as pd
import joblib
import math
import gc  # <--- Garbage Collector (Frees RAM)
from collections import Counter
from urllib.parse import urlparse
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# --- CONFIGURATION ---
DB_PATH = "threats.db"
MODEL_FILE = "phiusiil_model.pkl"

def calculate_entropy(text):
    if not text: return 0
    entropy = 0
    total = len(text)
    for count in Counter(text).values():
        p = count / total
        entropy -= p * math.log2(p)
    return entropy

def extract_features(df):
    print("   🧪 Extracting Features (Optimized)...")
    df['url'] = df['content'].astype(str)
    
    # Use smaller data types to save RAM
    df['url_len'] = df['url'].apply(len).astype('int32')
    df['hostname_len'] = df['url'].apply(lambda x: len(urlparse(x).netloc) if urlparse(x).netloc else 0).astype('int32')
    df['entropy'] = df['url'].apply(calculate_entropy).astype('float32')
    df['count_dots'] = df['url'].apply(lambda x: x.count('.')).astype('int16')
    df['count_dashes'] = df['url'].apply(lambda x: x.count('-')).astype('int16')
    df['count_at'] = df['url'].apply(lambda x: x.count('@')).astype('int16')
    df['count_digits'] = df['url'].apply(lambda x: sum(c.isdigit() for c in x)).astype('int16')
    
    sus_keywords = ['login', 'verify', 'update', 'account', 'secure', 'banking']
    df['sus_word_count'] = df['url'].apply(lambda x: sum(1 for w in sus_keywords if w in x.lower())).astype('int8')
    
    bad_tlds = ['.xyz', '.top', '.club', '.info', '.site', '.cn']
    df['is_bad_tld'] = df['url'].apply(lambda x: 1 if any(tld in x.lower() for tld in bad_tlds) else 0).astype('int8')
    
    df['is_https'] = df['url'].apply(lambda x: 1 if x.startswith('https') else 0).astype('int8')
    
    return df

if __name__ == "__main__":
    print("🧠 Loading Data...")
    conn = sqlite3.connect(DB_PATH)
    # Load in chunks if needed, but for 1M rows, standard load is okay if we clean up
    df = pd.read_sql("SELECT content, status FROM training_samples", conn)
    conn.close()

    # --- LABEL MAPPING ---
    df['status'] = df['status'].astype(str).str.lower().str.strip()
    label_map = {'legitimate': 1, 'safe': 1, '1': 1, 'phishing': 0, 'danger': 0, '0': 0}
    df['target'] = df['status'].map(label_map)
    df = df.dropna(subset=['target'])
    
    # Free up memory
    del label_map
    gc.collect()

    # --- EXTRACT ---
    df = extract_features(df)
    
    feature_cols = ['url_len', 'hostname_len', 'entropy', 'count_dots', 'count_dashes', 
                    'count_at', 'count_digits', 'sus_word_count', 'is_bad_tld', 'is_https']
    
    X = df[feature_cols]
    y = df['target']

    # Free up the big DataFrame before training
    del df
    gc.collect()
    print("   🧹 RAM Cleaned. Starting Training...")

    # --- TRAINING ---
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Reduced n_estimators to 100 (Faster, Less RAM)
    # Reduced n_jobs to 4 (Prevents crashing)
    model = RandomForestClassifier(n_estimators=100, n_jobs=4, random_state=42)
    model.fit(X_train, y_train)
    
    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"🚀 ACCURACY: {acc*100:.2f}%")
    
    joblib.dump({"model": model, "features": feature_cols}, MODEL_FILE)
    print("✅ Model Saved.")
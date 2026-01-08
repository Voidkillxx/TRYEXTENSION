from flask import Flask, request, jsonify
import pandas as pd
import joblib
import os
import math
import re
import requests # <--- NEEDED FOR UNROLLING
from urllib.parse import urlparse
from collections import Counter

app = Flask(__name__)

# --- CONFIGURATION ---
MODEL_FILE = "phiusiil_model.pkl"
WHITELIST_FILE = "whitelist.txt"

# --- GLOBAL VARIABLES ---
model = None
feature_names = None
whitelist = set()

# --- 1. LOAD RESOURCES ---
def load_whitelist():
    global whitelist
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, "r") as f:
            whitelist = set(line.strip().lower() for line in f)
        print(f"✅ Loaded Whitelist: {len(whitelist)} domains")
    else:
        print("⚠️ Whitelist file not found.")

def load_model():
    global model, feature_names
    if os.path.exists(MODEL_FILE):
        artifact = joblib.load(MODEL_FILE)
        if isinstance(artifact, dict):
            model = artifact["model"]
            feature_names = artifact["features"]
        else:
            model = artifact
            feature_names = ['url_len', 'hostname_len', 'count_dots', 'count_dashes', 
                             'count_at', 'count_digits', 'sus_word_count', 'is_bad_tld', 'is_https']
        print(f"✅ AI Model Loaded (Expecting {len(feature_names)} features)")
    else:
        print("❌ Model not found! Run train_model.py")

# --- 2. THE UNROLLER (New Feature) ---
def resolve_redirects(url):
    """
    Follows bit.ly/etc to find the REAL destination.
    """
    try:
        # We use a HEAD request because it's faster (doesn't download the body)
        response = requests.head(url, allow_redirects=True, timeout=3)
        real_url = response.url
        if real_url != url:
            print(f"   🔄 Unrolled: {url}  --->  {real_url}")
        return real_url
    except:
        return url # If it fails, just analyze the original

# --- 3. FEATURE EXTRACTION ---
def calculate_entropy(text):
    if not text: return 0
    entropy = 0
    total = len(text)
    for count in Counter(text).values():
        p = count / total
        entropy -= p * math.log2(p)
    return entropy

def check_impersonation(url, domain):
    brands = {
        'google': 'google.com', 'facebook': 'facebook.com', 'amazon': 'amazon.com',
        'paypal': 'paypal.com', 'netflix': 'netflix.com', 'microsoft': 'microsoft.com',
        'apple': 'apple.com', 'instagram': 'instagram.com', 'whatsapp': 'whatsapp.com',
        'bdo': 'bdo.com.ph', 'bpi': 'bpi.com.ph', 'metrobank': 'metrobank.com.ph',
        'gcash': 'gcash.com'
    }
    for brand, legit_domain in brands.items():
        if brand in url and legit_domain not in domain:
            return 1 
    return 0

def extract_features(url):
    features = {}
    url = str(url).lower()
    try:
        parsed = urlparse(url)
        if not parsed.scheme: parsed = urlparse("http://" + url)
        hostname = parsed.netloc
        path = parsed.path
    except:
        hostname = url
        path = ""

    features['url_len'] = len(url)
    features['hostname_len'] = len(hostname)
    features['path_len'] = len(path)
    features['entropy'] = calculate_entropy(url)
    features['count_dots'] = url.count('.')
    features['count_dashes'] = url.count('-')
    features['count_at'] = url.count('@')
    features['count_qmark'] = url.count('?')
    features['count_digits'] = sum(c.isdigit() for c in url)
    
    sus_keywords = ['login', 'verify', 'update', 'account', 'secure', 'banking']
    features['sus_word_count'] = sum(1 for w in sus_keywords if w in url)
    
    bad_tlds = ['.xyz', '.top', '.club', '.info', '.site', '.cn']
    features['is_bad_tld'] = 1 if any(tld in url for tld in bad_tlds) else 0
    
    features['is_https'] = 1 if url.startswith('https') else 0
    features['is_impersonating'] = check_impersonation(url, hostname)
    
    return features

# Initialize
load_whitelist()
load_model()

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response

# --- ROUTES ---
@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        data = request.json
        original_url = data.get('url', '').strip() # Keep case for unrolling
        if not original_url: return jsonify({'error': 'No URL'}), 400

        print(f"🔎 Analyzing: {original_url}")

        # 1. UNROLL SHORTENED LINKS
        # Check if it looks like a shortener before wasting time
        shorteners = ['bit.ly', 'goo.gl', 'tinyurl', 't.co', 'is.gd', 'ow.ly']
        if any(s in original_url.lower() for s in shorteners):
            final_url = resolve_redirects(original_url)
        else:
            final_url = original_url

        # Lowercase for analysis
        url_for_ai = final_url.lower()

        # 2. WHITELIST CHECK (On the FINAL URL)
        try:
            parsed = urlparse(url_for_ai)
            if not parsed.scheme: parsed = urlparse("http://" + url_for_ai)
            domain = parsed.netloc.replace("www.", "")
        except:
            domain = url_for_ai

        if domain in whitelist:
            print(f"   ✅ Whitelisted ({domain})")
            return jsonify({'url': original_url, 'result': 'SAFE'})

        # 3. AI PREDICTION
        if not model: return jsonify({'error': 'Model not loaded'}), 500
        
        feats = extract_features(url_for_ai)
        df = pd.DataFrame([feats])
        df = df.reindex(columns=feature_names, fill_value=0)
        
        pred = model.predict(df)[0]
        result = "SAFE" if pred == 1 else "DANGER"
        
        print(f"   🤖 AI Says: {result}")
        return jsonify({'url': original_url, 'result': result})

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    from waitress import serve
    print("--- 🚀 SERVER STARTED (With Link Unrolling) ---")
    print("    ✅ Serving on http://127.0.0.1:5000")
    serve(app, host='0.0.0.0', port=5000)
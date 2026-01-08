import re, sqlite3, datetime, joblib, os, requests
import pandas as pd
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

MAX_URL_LENGTH = 500
SHORTENERS = {'bit.ly', 'goo.gl', 'tinyurl.com', 't.co', 'is.gd', 'buff.ly', 'adf.ly', 'ow.ly', 'tr.im'}

def init_db():
    try:
        conn = sqlite3.connect("threats.db")
        conn.execute("PRAGMA journal_mode=WAL;") 
        conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, content TEXT, status TEXT, date TEXT)")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Init Error: {e}")

init_db()

WHITELIST = set()
def load_whitelist():
    global WHITELIST
    try:
        if os.path.exists("whitelist.txt"):
            with open("whitelist.txt", "r") as f:
                for line in f:
                    site = line.strip().lower()
                    if site:
                        WHITELIST.add(site)
                        WHITELIST.add(site.split('.')[0]) 
            print(f"Loaded {len(WHITELIST)} trusted entities.")
    except:
        pass

load_whitelist()

# Load AI Model
try:
    model = joblib.load("phiusiil_model.pkl")
    trained_features = joblib.load("feature_names.pkl")
    print("AI Model loaded successfully.")
except:
    print("Model not found. Please run train_model.py first.")

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

class ThreatRequest(BaseModel):
    url: str

def log_to_db(url, status):
    if len(url) > MAX_URL_LENGTH: return 
    try:
        conn = sqlite3.connect("threats.db", timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM logs WHERE content = ?", (url,))
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO logs (content, status, date) VALUES (?, ?, ?)", 
                         (url, status, str(datetime.datetime.now())))
            conn.commit()
        conn.close()
    except:
        pass

def unshorten_url(url):
    try:
        domain = url.split("//")[-1].split("/")[0].lower()
        if domain in SHORTENERS:
            response = requests.head(url, allow_redirects=True, timeout=3)
            return response.url
    except:
        pass
    return url

@app.post("/analyze")
async def analyze_threat(data: ThreatRequest, background_tasks: BackgroundTasks):
    original_url = data.url.lower().strip()
    url = unshorten_url(original_url)
    
    if not re.match(r'^https?://[\w.-]+\.[a-z]{2,}', url):
        return {"result": "SKIPPED"} 

    domain_part = url.split("//")[-1].split("/")[0]
    for trusted_site in WHITELIST:
        if trusted_site in domain_part:
            return {"result": "SAFE"}

    try:
        # Match features with training logic
        features = pd.DataFrame([{
            "URLLength": len(url), 
            "NoOfSubDomain": domain_part.count('.') - 1,
            "IsHttps": 1 if url.startswith('https') else 0
        }])
        
        # Align columns
        for col in trained_features:
            if col not in features.columns: features[col] = 0
        
        prediction = model.predict(features[trained_features])[0]
        
        # 1 = Safe, 0 = Danger
        status = "SAFE" if prediction == 1 else "DANGER"
    except:
        status = "SAFE" 

    background_tasks.add_task(log_to_db, url, status)
    return {"result": status}

# Report Incorrect Endpoint
@app.post("/report_safe")
async def report_safe(data: ThreatRequest):
    url = data.url.lower().strip()
    domain = url.split("//")[-1].split("/")[0]
    
    WHITELIST.add(domain)
    with open("whitelist.txt", "a") as f:
        f.write(f"\n{domain}")
    
    return {"status": "success", "message": f"{domain} whitelisted."}

# History Dashboard Endpoint
@app.get("/history")
async def get_history():
    try:
        conn = sqlite3.connect("threats.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT content, date FROM logs WHERE status='DANGER' ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()
        return {"history": [{"url": r['content'], "date": r['date']} for r in rows]}
    except:
        return {"history": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
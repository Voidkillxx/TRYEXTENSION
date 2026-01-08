import re, sqlite3, datetime, joblib
import pandas as pd
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load resources
WHITELIST = ["pnc.edu.ph", "abs-cbn.com", "facebook.com", "google.com"]
model = joblib.load("phiusiil_model.pkl")
trained_features = joblib.load("feature_names.pkl")

class ThreatRequest(BaseModel):
    url: str

# ⚡ FUNCTION TO LOG IN BACKGROUND (Doesn't slow down the user)
def log_to_db(url: str, status: str):
    try:
        conn = sqlite3.connect("threats.db")
        conn.execute("INSERT INTO logs (content, status, date) VALUES (?, ?, ?)",
                     (url[:200], status, str(datetime.datetime.now())))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Logging Error: {e}")

@app.post("/analyze")
async def analyze_threat(data: ThreatRequest, background_tasks: BackgroundTasks):
    url = data.url.lower()
    
    # 1. Whitelist Check
    if any(site in url for site in WHITELIST):
        status = "SAFE"
    else:
        # 2. AI Feature Extraction
        domain = url.split("//")[-1].split("/")[0]
        features = pd.DataFrame([{"URLLength": len(url), "NoOfSubDomain": domain.count('.') - 1}])
        for col in trained_features:
            if col not in features.columns: features[col] = 0
        
        prediction = model.predict(features[trained_features])[0]
        status = "SAFE" if prediction == 1 else "DANGER"

    # 3. ⚡ Add Logging to Background Task (Instant Response)
    background_tasks.add_task(log_to_db, url, status)

    return {"result": status}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
import sqlite3
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

print("🧠 1. Loading Corrected Data from Database...")
db_path = "threats.db"

try:
    conn = sqlite3.connect(db_path)
    # Load all data
    query = "SELECT content, status FROM training_samples"
    df = pd.read_sql(query, conn)
    conn.close()
    print(f"   ✅ Loaded {len(df)} rows.")
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit()

print("⚙️ 2. Processing Data...")
# Map Text to Numbers for AI
# SAFE -> 1
# DANGER -> 0
df['label'] = df['status'].map({'SAFE': 1, 'DANGER': 0})
df = df.dropna(subset=['label'])

print("🔍 3. Extracting Features...")
# Feature 1: Length
df['URLLength'] = df['content'].astype(str).apply(len)
# Feature 2: Dots
df['NoOfSubDomain'] = df['content'].astype(str).apply(lambda x: x.split('//')[-1].split('/')[0].count('.') - 1)
# Feature 3: HTTPS
df['IsHttps'] = df['content'].astype(str).apply(lambda x: 1 if x.startswith('https') else 0)

# Define Features
feature_names = ['URLLength', 'NoOfSubDomain', 'IsHttps']
X = df[feature_names]
y = df['label']

print(f"🌲 4. Training Model (300 Trees)...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train
model = RandomForestClassifier(n_estimators=300, class_weight='balanced', n_jobs=-1, random_state=42)
model.fit(X_train, y_train)

# Evaluate
predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
print(f"🚀 NEW ACCURACY: {accuracy * 100:.2f}%")

# Save
joblib.dump(model, "phiusiil_model.pkl")
joblib.dump(feature_names, "feature_names.pkl")
print("💾 Saved corrected 'phiusiil_model.pkl'.")
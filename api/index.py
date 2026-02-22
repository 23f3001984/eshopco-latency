from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import os

app = FastAPI()

# --- CRITICAL FIX: CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (POST, GET, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)
# --------------------------

# Path setup (same as before)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "q-vercel-latency.json")

class TelemetryInput(BaseModel):
    regions: list[str]
    threshold_ms: float

# Load data once
df = None
if os.path.exists(DATA_PATH):
    try:
        df = pd.read_json(DATA_PATH)
        df.columns = df.columns.str.lower().str.strip()
        # Rename columns to standard names if needed
        rename_map = {}
        if 'latency_ms' in df.columns: rename_map['latency_ms'] = 'latency'
        if 'uptime_pct' in df.columns: rename_map['uptime_pct'] = 'uptime'
        if rename_map: df.rename(columns=rename_map, inplace=True)
    except Exception as e:
        print(f"Error loading data: {e}")

@app.post("/api")
def get_metrics(params: TelemetryInput):
    if df is None or df.empty:
        raise HTTPException(status_code=500, detail="Data not loaded")

    # Filter
    target_regions = [r.lower() for r in params.regions]
    filtered = df[df['region'].str.lower().isin(target_regions)]
    
    if filtered.empty:
        return {
            "avg_latency": 0.0, "p95_latency": 0.0,
            "avg_uptime": 0.0, "breaches": 0
        }

    # Calculate
    avg_latency = float(filtered['latency'].mean())
    p95_latency = float(filtered['latency'].quantile(0.95))
    avg_uptime = float(filtered['uptime'].mean())
    breaches = int((filtered['latency'] > params.threshold_ms).sum())

    return {
        "avg_latency": round(avg_latency, 2),
        "p95_latency": round(p95_latency, 2),
        "avg_uptime": round(avg_uptime, 4),
        "breaches": breaches
    }

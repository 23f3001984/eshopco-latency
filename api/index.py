from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import os

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to the JSON file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "q-vercel-latency.json") # Ensure file is named telemetry.json

class TelemetryInput(BaseModel):
    regions: list[str]
    threshold_ms: float

# Global variable
df = None

def load_data():
    global df
    if df is not None:
        return
    
    if not os.path.exists(DATA_PATH):
        print(f"File not found at {DATA_PATH}")
        return

    try:
        df = pd.read_json(DATA_PATH)
        
        # Standardize columns to lowercase
        df.columns = df.columns.str.lower().str.strip()
        
        # RENAME columns to match logic if necessary
        # We need 'latency' and 'uptime' for the calculations below
        rename_map = {}
        if 'latency_ms' in df.columns:
            rename_map['latency_ms'] = 'latency'
        if 'uptime_pct' in df.columns:
            rename_map['uptime_pct'] = 'uptime'
            
        if rename_map:
            df.rename(columns=rename_map, inplace=True)
            
    except Exception as e:
        print(f"Error loading data: {e}")

@app.post("/api")
def get_metrics(params: TelemetryInput):
    load_data()
    
    if df is None or df.empty:
        # Try to reload if empty (cold start edge case)
        return {"error": "Data not loaded"}

    # Filter regions (case-insensitive)
    target_regions = [r.lower() for r in params.regions]
    filtered = df[df['region'].str.lower().isin(target_regions)]
    
    if filtered.empty:
        return {
            "avg_latency": 0.0,
            "p95_latency": 0.0,
            "avg_uptime": 0.0,
            "breaches": 0
        }

    # Calculate Metrics
    # round() is used to make the output cleaner
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

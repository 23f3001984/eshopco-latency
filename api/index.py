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
    allow_methods=["*"],  # Allow all methods including POST
    allow_headers=["*"],
)

# Path to the JSON file
# Ensure your folder structure is:
# /api/index.py
# /data/telemetry.json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "q-vercel-latency.json")

# Input Schema
class TelemetryInput(BaseModel):
    regions: list[str]
    threshold_ms: float

# Global variable to cache data
df = None

def load_data():
    global df
    if df is not None:
        return
    
    if not os.path.exists(DATA_PATH):
        print(f"File not found at {DATA_PATH}")
        return

    try:
        # Load JSON data
        df = pd.read_json(DATA_PATH)
        
        # Standardize column names (lowercase)
        df.columns = df.columns.str.lower().str.strip()
        
    except Exception as e:
        print(f"Error loading data: {e}")
        df = pd.DataFrame() # Create empty DF on error to prevent crashes

@app.post("/api")
def get_metrics(params: TelemetryInput):
    load_data()
    
    if df is None or df.empty:
        raise HTTPException(status_code=500, detail="Telemetry data not loaded or empty")

    # Filter by regions requested (case-insensitive)
    target_regions = [r.lower() for r in params.regions]
    
    # Filter the DataFrame
    # Assumes 'region' column exists. If it's nested JSON, pandas usually flattens it well,
    # but simple list-of-dicts is best.
    filtered = df[df['region'].str.lower().isin(target_regions)]
    
    if filtered.empty:
        return {
            "avg_latency": 0.0,
            "p95_latency": 0.0,
            "avg_uptime": 0.0,
            "breaches": 0
        }

    # Calculate Metrics
    # We use .astype(float) to ensure JSON serialization works (numpy types can be tricky)
    avg_latency = float(filtered['latency'].mean())
    p95_latency = float(filtered['latency'].quantile(0.95))
    avg_uptime = float(filtered['uptime'].mean())
    
    # Count breaches (records where latency > threshold)
    breaches = int((filtered['latency'] > params.threshold_ms).sum())

    return {
        "avg_latency": round(avg_latency, 2),
        "p95_latency": round(p95_latency, 2),
        "avg_uptime": round(avg_uptime, 4), # Uptime usually needs more precision
        "breaches": breaches
    }
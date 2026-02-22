from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
import os

app = FastAPI()

# --- 1. DEFINE CORS HEADERS HERE ---
# (We fixed the smart quotes to standard quotes)
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}

# --- 2. HANDLE PREFLIGHT REQUESTS ---
# This manually tells the browser "Yes, you can send POST requests"
@app.options("/api")
async def preflight_handler():
    return JSONResponse(content={}, headers=CORS_HEADERS)

# Path to the JSON file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "q-vercel-latency.json")

class TelemetryInput(BaseModel):
    regions: list[str]
    threshold_ms: float

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
        df.columns = df.columns.str.lower().str.strip()
        
        # --- 3. FIX COLUMN NAMES ---
        # Your file has 'latency_ms' and 'uptime_pct', but code needs 'latency' and 'uptime'
        rename_map = {}
        if 'latency_ms' in df.columns: rename_map['latency_ms'] = 'latency'
        if 'uptime_pct' in df.columns: rename_map['uptime_pct'] = 'uptime'
        if rename_map: df.rename(columns=rename_map, inplace=True)
            
    except Exception as e:
        print(f"Error loading data: {e}")
        df = pd.DataFrame()

@app.post("/api")
def get_metrics(params: TelemetryInput):
    load_data()
    
    if df is None or df.empty:
        # Returns 500 with CORS headers so the browser can actually see the error
        return JSONResponse(
            status_code=500, 
            content={"detail": "Telemetry data not loaded"}, 
            headers=CORS_HEADERS
        )

    target_regions = [r.lower() for r in params.regions]
    
    # Check if 'region' column exists
    if 'region' not in df.columns:
         return JSONResponse(
             status_code=500, 
             content={"detail": "Column 'region' not found"}, 
             headers=CORS_HEADERS
         )

    filtered = df[df['region'].str.lower().isin(target_regions)]
    
    if filtered.empty:
        result = {
            "avg_latency": 0.0, "p95_latency": 0.0,
            "avg_uptime": 0.0, "breaches": 0
        }
        return JSONResponse(content=result, headers=CORS_HEADERS)

    # Calculate Metrics
    avg_latency = float(filtered['latency'].mean())
    p95_latency = float(filtered['latency'].quantile(0.95))
    avg_uptime = float(filtered['uptime'].mean())
    breaches = int((filtered['latency'] > params.threshold_ms).sum())

    result = {
        "avg_latency": round(avg_latency, 2),
        "p95_latency": round(p95_latency, 2),
        "avg_uptime": round(avg_uptime, 4),
        "breaches": breaches
    }
    
    # --- 4. RETURN WITH HEADERS ---
    return JSONResponse(content=result, headers=CORS_HEADERS)

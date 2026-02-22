from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os

app = FastAPI()

# --- CORS HEADERS ---
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Expose-Headers": "Access-Control-Allow-Origin",
}

# --- PREFLIGHT HANDLER ---
@app.options("/{path:path}")
async def preflight_handler(path: str):
    return JSONResponse(content={}, headers=CORS_HEADERS)

# --- DATA LOADING ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "telemetry.json")

df = None

def load_data():
    global df
    if df is not None: return
    if not os.path.exists(DATA_PATH): return

    try:
        df = pd.read_json(DATA_PATH)
        # Ensure column names are clean and match your snippet's expectations
        df.columns = df.columns.str.lower().str.strip()
        # The file has 'latency_ms' and 'uptime_pct', so we don't rename them.
    except Exception as e:
        print(f"Error loading data: {e}")
        df = pd.DataFrame()

class TelemetryInput(BaseModel):
    regions: list[str]
    threshold_ms: float

@app.post("/api")
def get_metrics(params: TelemetryInput):
    load_data()
    
    if df is None or df.empty:
        return JSONResponse(content={"error": "Data not loaded"}, status_code=500, headers=CORS_HEADERS)

    result = {}
    
    # Iterate through each requested region (Per your snippet logic)
    for region in params.regions:
        # Filter for specific region (case-insensitive match)
        region_data = df[df['region'].str.lower() == region.lower()]

        if region_data.empty:
            continue

        # Extract series
        latencies = region_data['latency_ms']
        uptimes = region_data['uptime_pct']
        threshold = params.threshold_ms

        # Calculate Metrics
        metrics = {
            "avg_latency": round(float(latencies.mean()), 2),
            "p95_latency": round(float(latencies.quantile(0.95)), 2),
            "avg_uptime": round(float(uptimes.mean()), 2),
            "breaches": int((latencies > threshold).sum())
        }
        
        # Add to result dictionary
        result[region] = metrics

    return JSONResponse(content=result, headers=CORS_HEADERS)

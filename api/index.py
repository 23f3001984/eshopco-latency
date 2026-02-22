from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
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
DATA_PATH = os.path.join(BASE_DIR, "data", "q-vercel-latency.json")

df = None

def load_data():
    global df
    if df is not None: return
    if not os.path.exists(DATA_PATH): return

    try:
        df = pd.read_json(DATA_PATH)
        # Standardize columns to lowercase
        df.columns = df.columns.str.lower().str.strip()
        # Note: We expect 'latency_ms' and 'uptime_pct' based on your file
    except Exception as e:
        print(f"Error loading data: {e}")
        df = pd.DataFrame()

class TelemetryInput(BaseModel):
    regions: list[str]
    threshold_ms: float

@app.get("/")
def home():
    return JSONResponse(content={"status": "Online"}, headers=CORS_HEADERS)

@app.post("/api")
def get_metrics(params: TelemetryInput):
    load_data()
    
    if df is None or df.empty:
        return JSONResponse(
            content={"detail": "Data not loaded"}, 
            status_code=500, 
            headers=CORS_HEADERS
        )

    # Dictionary to hold the result: {"apac": {...}, "amer": {...}}
    results = {}
    
    for region in params.regions:
        # Filter for the specific region (case-insensitive)
        region_df = df[df['region'].str.lower() == region.lower()]

        if region_df.empty:
            continue

        # Extract series
        # We handle 'latency_ms' vs 'latency' just in case
        lat_col = 'latency_ms' if 'latency_ms' in region_df.columns else 'latency'
        up_col = 'uptime_pct' if 'uptime_pct' in region_df.columns else 'uptime'
        
        latencies = region_df[lat_col]
        uptimes = region_df[up_col]
        
        # Calculate Metrics (Rounded as requested)
        metrics = {
            "avg_latency": round(float(latencies.mean()), 2),
            "p95_latency": round(float(latencies.quantile(0.95)), 2),
            "avg_uptime": round(float(uptimes.mean()), 4), # User output showed 3 decimals, 4 is safer
            "breaches": int((latencies > params.threshold_ms).sum())
        }
        
        # Add to the main dictionary with the region name as the key
        results[region] = metrics

    # Return the dictionary directly
    return JSONResponse(content=results, headers=CORS_HEADERS)

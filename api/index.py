from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
import os

app = FastAPI()

# --- CORS CONFIGURATION ---
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "*",
}

# --- PREFLIGHT HANDLER (For Vercel/Browser Checks) ---
@app.options("/{path:path}")
async def preflight_handler(path: str):
    return JSONResponse(content={}, headers=CORS_HEADERS)

# --- DATA LOADING SETUP ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "q-vercel-latency.json")

class TelemetryInput(BaseModel):
    regions: list[str]
    threshold_ms: float

df = None

def load_data():
    global df
    if df is not None: return
    if not os.path.exists(DATA_PATH): return

    try:
        df = pd.read_json(DATA_PATH)
        df.columns = df.columns.str.lower().str.strip()
        
        # Fix column names to match what code expects
        rename_map = {}
        if 'latency_ms' in df.columns: rename_map['latency_ms'] = 'latency'
        if 'uptime_pct' in df.columns: rename_map['uptime_pct'] = 'uptime'
        if rename_map: df.rename(columns=rename_map, inplace=True)
    except Exception as e:
        print(f"Error: {e}")
        df = pd.DataFrame()

# --- ROUTES ---

@app.get("/")
def home():
    """Sanity check: If you see this, the deploy works!"""
    return JSONResponse(
        content={"status": "Online", "message": "POST request to /api to use the tool"}, 
        headers=CORS_HEADERS
    )

@app.post("/api")
def get_metrics(params: TelemetryInput):
    load_data()
    
    # Error handling with CORS headers attached
    if df is None or df.empty:
        return JSONResponse(
            status_code=500, 
            content={"detail": "Data not loaded"}, 
            headers=CORS_HEADERS
        )

    target_regions = [r.lower() for r in params.regions]
    
    if 'region' not in df.columns:
         return JSONResponse(
             status_code=500, 
             content={"detail": "Region column missing"}, 
             headers=CORS_HEADERS
         )

    filtered = df[df['region'].str.lower().isin(target_regions)]
    
    if filtered.empty:
        result = {"avg_latency": 0.0, "p95_latency": 0.0, "avg_uptime": 0.0, "breaches": 0}
        return JSONResponse(content=result, headers=CORS_HEADERS)

    # Calculate
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
    
    return JSONResponse(content=result, headers=CORS_HEADERS)

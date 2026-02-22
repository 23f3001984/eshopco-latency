from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd

app = FastAPI()

# --- EMBEDDED DATA (Prevents file loading errors) ---
RAW_DATA = [
  {"region": "apac", "service": "recommendations", "latency_ms": 178.01, "uptime_pct": 97.714},
  {"region": "apac", "service": "analytics", "latency_ms": 140.7, "uptime_pct": 98.16},
  {"region": "apac", "service": "checkout", "latency_ms": 207.31, "uptime_pct": 98.868},
  {"region": "apac", "service": "support", "latency_ms": 179.51, "uptime_pct": 97.851},
  {"region": "apac", "service": "checkout", "latency_ms": 175.55, "uptime_pct": 98.642},
  {"region": "apac", "service": "catalog", "latency_ms": 203.63, "uptime_pct": 98.104},
  {"region": "apac", "service": "catalog", "latency_ms": 193.61, "uptime_pct": 99.194},
  {"region": "apac", "service": "payments", "latency_ms": 181.09, "uptime_pct": 98.102},
  {"region": "apac", "service": "analytics", "latency_ms": 137.88, "uptime_pct": 97.898},
  {"region": "apac", "service": "catalog", "latency_ms": 145.15, "uptime_pct": 98.239},
  {"region": "apac", "service": "payments", "latency_ms": 187.16, "uptime_pct": 97.601},
  {"region": "apac", "service": "support", "latency_ms": 134.37, "uptime_pct": 98.938},
  {"region": "emea", "service": "support", "latency_ms": 208.08, "uptime_pct": 97.423},
  {"region": "emea", "service": "catalog", "latency_ms": 193.54, "uptime_pct": 97.816},
  {"region": "emea", "service": "analytics", "latency_ms": 108.23, "uptime_pct": 98.788},
  {"region": "emea", "service": "payments", "latency_ms": 177.69, "uptime_pct": 97.787},
  {"region": "emea", "service": "checkout", "latency_ms": 217.53, "uptime_pct": 98.327},
  {"region": "emea", "service": "analytics", "latency_ms": 165.29, "uptime_pct": 97.978},
  {"region": "emea", "service": "payments", "latency_ms": 202.68, "uptime_pct": 98.766},
  {"region": "emea", "service": "payments", "latency_ms": 197.2, "uptime_pct": 98.223},
  {"region": "emea", "service": "checkout", "latency_ms": 222.33, "uptime_pct": 97.606},
  {"region": "emea", "service": "recommendations", "latency_ms": 219.89, "uptime_pct": 97.992},
  {"region": "emea", "service": "support", "latency_ms": 160.89, "uptime_pct": 98.462},
  {"region": "emea", "service": "checkout", "latency_ms": 165.9, "uptime_pct": 98.92},
  {"region": "amer", "service": "catalog", "latency_ms": 201.44, "uptime_pct": 98.737},
  {"region": "amer", "service": "support", "latency_ms": 194.83, "uptime_pct": 97.108},
  {"region": "amer", "service": "recommendations", "latency_ms": 170.96, "uptime_pct": 97.296},
  {"region": "amer", "service": "support", "latency_ms": 133.35, "uptime_pct": 98.793},
  {"region": "amer", "service": "checkout", "latency_ms": 191.54, "uptime_pct": 97.452},
  {"region": "amer", "service": "analytics", "latency_ms": 179.19, "uptime_pct": 99.292},
  {"region": "amer", "service": "catalog", "latency_ms": 221.67, "uptime_pct": 97.673},
  {"region": "amer", "service": "recommendations", "latency_ms": 182.22, "uptime_pct": 99.307},
  {"region": "amer", "service": "catalog", "latency_ms": 213.83, "uptime_pct": 97.343},
  {"region": "amer", "service": "checkout", "latency_ms": 122.84, "uptime_pct": 98.375},
  {"region": "amer", "service": "payments", "latency_ms": 152.86, "uptime_pct": 98.313},
  {"region": "amer", "service": "catalog", "latency_ms": 219.45, "uptime_pct": 98.011}
]

class TelemetryInput(BaseModel):
    regions: list[str]
    threshold_ms: float

# Helper to attach headers to any response
def build_response(content, status_code=200):
    return JSONResponse(
        content=content,
        status_code=status_code,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.options("/api")
async def options_handler():
    # Explicitly say "YES" to the browser's pre-flight check
    return build_response({})

@app.post("/api")
def get_metrics(params: TelemetryInput):
    # 1. Load Data (from embedded list)
    try:
        df = pd.DataFrame(RAW_DATA)
    except Exception as e:
        return build_response({"error": str(e)}, status_code=500)

    # 2. Filter
    target_regions = [r.lower() for r in params.regions]
    filtered = df[df['region'].str.lower().isin(target_regions)]
    
    if filtered.empty:
        return build_response({
            "avg_latency": 0.0, "p95_latency": 0.0,
            "avg_uptime": 0.0, "breaches": 0
        })

    # 3. Calculate
    avg_latency = float(filtered['latency_ms'].mean())
    p95_latency = float(filtered['latency_ms'].quantile(0.95))
    avg_uptime = float(filtered['uptime_pct'].mean())
    breaches = int((filtered['latency_ms'] > params.threshold_ms).sum())

    # 4. Return with headers
    return build_response({
        "avg_latency": round(avg_latency, 2),
        "p95_latency": round(p95_latency, 2),
        "avg_uptime": round(avg_uptime, 4),
        "breaches": breaches
    })

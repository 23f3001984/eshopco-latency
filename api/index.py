from flask import Flask, request, jsonify, make_response
import statistics
from collections import defaultdict

app = Flask(__name__)

TELEMETRY_RAW = [
  {"region":"apac","latency_ms":178.01,"uptime_pct":97.714},
  {"region":"apac","latency_ms":140.7,"uptime_pct":98.16},
  {"region":"apac","latency_ms":207.31,"uptime_pct":98.868},
  {"region":"apac","latency_ms":179.51,"uptime_pct":97.851},
  {"region":"apac","latency_ms":175.55,"uptime_pct":98.642},
  {"region":"apac","latency_ms":203.63,"uptime_pct":98.104},
  {"region":"apac","latency_ms":193.61,"uptime_pct":99.194},
  {"region":"apac","latency_ms":181.09,"uptime_pct":98.102},
  {"region":"apac","latency_ms":137.88,"uptime_pct":97.898},
  {"region":"apac","latency_ms":145.15,"uptime_pct":98.239},
  {"region":"apac","latency_ms":187.16,"uptime_pct":97.601},
  {"region":"apac","latency_ms":134.37,"uptime_pct":98.938},
  {"region":"emea","latency_ms":208.08,"uptime_pct":97.423},
  {"region":"emea","latency_ms":193.54,"uptime_pct":97.816},
  {"region":"emea","latency_ms":108.23,"uptime_pct":98.788},
  {"region":"emea","latency_ms":177.69,"uptime_pct":97.787},
  {"region":"emea","latency_ms":217.53,"uptime_pct":98.327},
  {"region":"emea","latency_ms":165.29,"uptime_pct":97.978},
  {"region":"emea","latency_ms":202.68,"uptime_pct":98.766},
  {"region":"emea","latency_ms":197.2,"uptime_pct":98.223},
  {"region":"emea","latency_ms":222.33,"uptime_pct":97.606},
  {"region":"emea","latency_ms":219.89,"uptime_pct":97.992},
  {"region":"emea","latency_ms":160.89,"uptime_pct":98.462},
  {"region":"emea","latency_ms":165.9,"uptime_pct":98.92},
  {"region":"amer","latency_ms":201.44,"uptime_pct":98.737},
  {"region":"amer","latency_ms":194.83,"uptime_pct":97.108},
  {"region":"amer","latency_ms":170.96,"uptime_pct":97.296},
  {"region":"amer","latency_ms":133.35,"uptime_pct":98.793},
  {"region":"amer","latency_ms":191.54,"uptime_pct":97.452},
  {"region":"amer","latency_ms":179.19,"uptime_pct":99.292},
  {"region":"amer","latency_ms":221.67,"uptime_pct":97.673},
  {"region":"amer","latency_ms":182.22,"uptime_pct":99.307},
  {"region":"amer","latency_ms":213.83,"uptime_pct":97.343},
  {"region":"amer","latency_ms":122.84,"uptime_pct":98.375},
  {"region":"amer","latency_ms":152.86,"uptime_pct":98.313},
  {"region":"amer","latency_ms":219.45,"uptime_pct":98.011},
]

TELEMETRY = defaultdict(list)
for row in TELEMETRY_RAW:
    TELEMETRY[row["region"]].append(row)


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


def compute_metrics(region, threshold_ms):
    records = TELEMETRY.get(region)
    if not records:
        return None
    lats = [r["latency_ms"] for r in records]
    uptimes = [r["uptime_pct"] for r in records]
    sorted_lats = sorted(lats)
    n = len(sorted_lats)
    p95_idx = min(int(0.95 * n), n - 1)
    return {
        "avg_latency": round(statistics.mean(lats), 4),
        "p95_latency": round(sorted_lats[p95_idx], 4),
        "avg_uptime": round(statistics.mean(uptimes), 4),
        "breaches": sum(1 for l in lats if l > threshold_ms),
    }


@app.route("/", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/index", methods=["GET", "POST", "OPTIONS"])
def index():
    if request.method == "OPTIONS":
        return make_response("", 204)
    if request.method == "GET":
        return jsonify({"status": "ok", "regions": list(TELEMETRY.keys())})

    payload = request.get_json(force=True, silent=True) or {}
    regions = payload.get("regions", [])
    threshold_ms = float(payload.get("threshold_ms", 180))

    result = {}
    for region in regions:
        m = compute_metrics(region, threshold_ms)
        result[region] = m if m is not None else {"error": "unknown region"}

    return jsonify(result)

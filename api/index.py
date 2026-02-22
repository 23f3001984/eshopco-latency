from http.server import BaseHTTPRequestHandler
import json
import statistics
from collections import defaultdict

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


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _write_response(self, status, body_dict):
        body = json.dumps(body_dict).encode()
        self.send_response(status)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            payload = json.loads(body)
            regions = payload.get("regions", [])
            threshold_ms = float(payload.get("threshold_ms", 180))
        except Exception as e:
            self._write_response(400, {"error": f"Invalid request: {e}"})
            return

        result = {}
        for region in regions:
            m = compute_metrics(region, threshold_ms)
            result[region] = m if m is not None else {"error": "unknown region"}

        self._write_response(200, result)

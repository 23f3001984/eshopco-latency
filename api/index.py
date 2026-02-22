import json
import statistics
from http.server import BaseHTTPRequestHandler
from collections import defaultdict

# Embedded telemetry data
TELEMETRY_RAW = [
  {"region":"apac","service":"recommendations","latency_ms":178.01,"uptime_pct":97.714,"timestamp":20250301},
  {"region":"apac","service":"analytics","latency_ms":140.7,"uptime_pct":98.16,"timestamp":20250302},
  {"region":"apac","service":"checkout","latency_ms":207.31,"uptime_pct":98.868,"timestamp":20250303},
  {"region":"apac","service":"support","latency_ms":179.51,"uptime_pct":97.851,"timestamp":20250304},
  {"region":"apac","service":"checkout","latency_ms":175.55,"uptime_pct":98.642,"timestamp":20250305},
  {"region":"apac","service":"catalog","latency_ms":203.63,"uptime_pct":98.104,"timestamp":20250306},
  {"region":"apac","service":"catalog","latency_ms":193.61,"uptime_pct":99.194,"timestamp":20250307},
  {"region":"apac","service":"payments","latency_ms":181.09,"uptime_pct":98.102,"timestamp":20250308},
  {"region":"apac","service":"analytics","latency_ms":137.88,"uptime_pct":97.898,"timestamp":20250309},
  {"region":"apac","service":"catalog","latency_ms":145.15,"uptime_pct":98.239,"timestamp":20250310},
  {"region":"apac","service":"payments","latency_ms":187.16,"uptime_pct":97.601,"timestamp":20250311},
  {"region":"apac","service":"support","latency_ms":134.37,"uptime_pct":98.938,"timestamp":20250312},
  {"region":"emea","service":"support","latency_ms":208.08,"uptime_pct":97.423,"timestamp":20250301},
  {"region":"emea","service":"catalog","latency_ms":193.54,"uptime_pct":97.816,"timestamp":20250302},
  {"region":"emea","service":"analytics","latency_ms":108.23,"uptime_pct":98.788,"timestamp":20250303},
  {"region":"emea","service":"payments","latency_ms":177.69,"uptime_pct":97.787,"timestamp":20250304},
  {"region":"emea","service":"checkout","latency_ms":217.53,"uptime_pct":98.327,"timestamp":20250305},
  {"region":"emea","service":"analytics","latency_ms":165.29,"uptime_pct":97.978,"timestamp":20250306},
  {"region":"emea","service":"payments","latency_ms":202.68,"uptime_pct":98.766,"timestamp":20250307},
  {"region":"emea","service":"payments","latency_ms":197.2,"uptime_pct":98.223,"timestamp":20250308},
  {"region":"emea","service":"checkout","latency_ms":222.33,"uptime_pct":97.606,"timestamp":20250309},
  {"region":"emea","service":"recommendations","latency_ms":219.89,"uptime_pct":97.992,"timestamp":20250310},
  {"region":"emea","service":"support","latency_ms":160.89,"uptime_pct":98.462,"timestamp":20250311},
  {"region":"emea","service":"checkout","latency_ms":165.9,"uptime_pct":98.92,"timestamp":20250312},
  {"region":"amer","service":"catalog","latency_ms":201.44,"uptime_pct":98.737,"timestamp":20250301},
  {"region":"amer","service":"support","latency_ms":194.83,"uptime_pct":97.108,"timestamp":20250302},
  {"region":"amer","service":"recommendations","latency_ms":170.96,"uptime_pct":97.296,"timestamp":20250303},
  {"region":"amer","service":"support","latency_ms":133.35,"uptime_pct":98.793,"timestamp":20250304},
  {"region":"amer","service":"checkout","latency_ms":191.54,"uptime_pct":97.452,"timestamp":20250305},
  {"region":"amer","service":"analytics","latency_ms":179.19,"uptime_pct":99.292,"timestamp":20250306},
  {"region":"amer","service":"catalog","latency_ms":221.67,"uptime_pct":97.673,"timestamp":20250307},
  {"region":"amer","service":"recommendations","latency_ms":182.22,"uptime_pct":99.307,"timestamp":20250308},
  {"region":"amer","service":"catalog","latency_ms":213.83,"uptime_pct":97.343,"timestamp":20250309},
  {"region":"amer","service":"checkout","latency_ms":122.84,"uptime_pct":98.375,"timestamp":20250310},
  {"region":"amer","service":"payments","latency_ms":152.86,"uptime_pct":98.313,"timestamp":20250311},
  {"region":"amer","service":"catalog","latency_ms":219.45,"uptime_pct":98.011,"timestamp":20250312},
]

# Pre-group by region
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


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default logging

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
            regions = payload.get("regions", [])
            threshold_ms = float(payload.get("threshold_ms", 180))
        except Exception:
            self.send_response(400)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON body"}).encode())
            return

        result = {}
        for region in regions:
            m = compute_metrics(region, threshold_ms)
            result[region] = m if m is not None else {"error": "unknown region"}

        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
import numpy as np
from pathlib import Path

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

# Path to JSON file (assumed to be in same folder as metrics.py)
data_path = Path(__file__).parent / "q-vercel-latency.json"

# Load telemetry if available
telemetry = []
if data_path.exists():
    with open(data_path, "r") as f:
        telemetry = json.load(f)
else:
    print(f"⚠️ File not found at {data_path}")

@app.get("/")
def root():
    return {"message": "FastAPI app deployed successfully!"}
@app.options("/")
async def options():
    return {}


@app.post("/")
async def metrics(request: Request):
    # If telemetry wasn't loaded at startup, try again on first call
    global telemetry
    if not telemetry:
        if data_path.exists():
            with open(data_path, "r") as f:
                telemetry = json.load(f)
        else:
            return {"error": f"File not found at {data_path.name}"}

    body = await request.json()
    regions = body.get("regions", [])
    threshold = body.get("threshold_ms", 180)

    response = {}
    for region in regions:
        region_data = [r for r in telemetry if r["region"] == region]
        if not region_data:
            continue

        latencies = [r["latency_ms"] for r in region_data]
        uptimes = [r["uptime_pct"] for r in region_data]

        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        avg_uptime = float(np.mean(uptimes))
        breaches = sum(l > threshold for l in latencies)

        response[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 3),
            "breaches": breaches
        }


    return response

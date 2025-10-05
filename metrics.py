from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import numpy as np
from pathlib import Path

app = FastAPI()

# Enable CORS for all methods
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Path to JSON file
data_path = Path(__file__).parent / "q-vercel-latency.json"

# Load telemetry if available
telemetry = []
if data_path.exists():
    with open(data_path, "r") as f:
        telemetry = json.load(f)
else:
    print(f"⚠️ File not found at {data_path}")

@app.options("/{path:path}")
async def options_handler(path: str):
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.get("/")
def root():
    return JSONResponse(
        content={"message": "FastAPI app deployed successfully!"},
        headers={"Access-Control-Allow-Origin": "*"}
    )

@app.post("/")
async def metrics(request: Request):
    global telemetry
    if not telemetry:
        if data_path.exists():
            with open(data_path, "r") as f:
                telemetry = json.load(f)
        else:
            return JSONResponse(
                content={"error": f"File not found at {data_path.name}"},
                headers={"Access-Control-Allow-Origin": "*"}
            )

    body = await request.json()
    regions = body.get("regions", [])
    threshold = body.get("threshold_ms", 180)

    regions_data = []
    
    for region in regions:
        region_entries = [r for r in telemetry if r["region"] == region]
        if not region_entries:
            continue

        latencies = [r["latency_ms"] for r in region_entries]
        uptimes = [r["uptime_pct"] for r in region_entries]

        avg_latency = round(float(np.mean(latencies)), 2)
        p95_latency = round(float(np.percentile(latencies, 95)), 2)
        avg_uptime = round(float(np.mean(uptimes)), 3)
        breaches = sum(l > threshold for l in latencies)

        regions_data.append({
            "region": region,
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        })

    return JSONResponse(
        content={"regions": regions_data},
        headers={"Access-Control-Allow-Origin": "*"}
    )
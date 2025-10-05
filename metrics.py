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
    group_by_service = body.get("group_by_service", False)

    response = {}
    
    for region in regions:
        region_data = [r for r in telemetry if r["region"] == region]
        if not region_data:
            continue

        if group_by_service:
            # Group by service
            services = {}
            for entry in region_data:
                service = entry.get("service", "unknown")
                if service not in services:
                    services[service] = []
                services[service].append(entry)
            
            response[region] = {}
            for service, entries in services.items():
                latencies = [e["latency_ms"] for e in entries]
                uptimes = [e["uptime_pct"] for e in entries]
                
                response[region][service] = {
                    "avg_latency": round(float(np.mean(latencies)), 2),
                    "p95_latency": round(float(np.percentile(latencies, 95)), 2),
                    "avg_uptime": round(float(np.mean(uptimes)), 3),
                    "breaches": sum(l > threshold for l in latencies)
                }
        else:
            # Aggregate all services
            latencies = [r["latency_ms"] for r in region_data]
            uptimes = [r["uptime_pct"] for r in region_data]

            response[region] = {
                "avg_latency": round(float(np.mean(latencies)), 2),
                "p95_latency": round(float(np.percentile(latencies, 95)), 2),
                "avg_uptime": round(float(np.mean(uptimes)), 3),
                "breaches": sum(l > threshold for l in latencies)
            }

    return JSONResponse(
        content=response,
        headers={"Access-Control-Allow-Origin": "*"}
    )
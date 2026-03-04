#!/usr/bin/env python3
"""
Jarvis Quantum Gateway — Unified API
========================================
Routes all quantum requests to the correct module.

Port: 3030

Routes:
  /api/credibility/* -> localhost:3031
  /api/qkd/*         -> localhost:3032
  /api/search/*       -> localhost:3033
  /api/reasoning/*    -> localhost:3034
  /api/emotion/*      -> localhost:3035
  /api/quantum/status -> All module health checks
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import httpx
import time
import os
import asyncio

app = FastAPI(
    title="Jarvis Quantum Gateway",
    description="Unified API gateway for all Jarvis quantum modules",
    version="0.1.0",
)

SERVICE_PORT = int(os.environ.get("GATEWAY_PORT", 3030))

MODULES = {
    "credibility": {"port": 3031, "name": "Credibility Verifier", "prefix": "/api/credibility"},
    "qkd": {"port": 3032, "name": "QKD Secure Comms", "prefix": "/api/qkd"},
    "search": {"port": 3033, "name": "Quantum Search", "prefix": "/api/search"},
    "reasoning": {"port": 3034, "name": "Quantum Reasoning", "prefix": "/api/reasoning"},
    "emotion": {"port": 3035, "name": "Quantum Emotion", "prefix": "/api/emotion"},
}

start_time = time.time()


async def proxy_request(module_key: str, path: str, request: Request):
    """Forward request to the appropriate module."""
    if module_key not in MODULES:
        raise HTTPException(404, f"Unknown module: {module_key}")

    module = MODULES[module_key]
    url = f"http://localhost:{module['port']}{path}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            if request.method == "GET":
                resp = await client.get(url)
            elif request.method == "POST":
                body = await request.body()
                resp = await client.post(
                    url,
                    content=body,
                    headers={"Content-Type": "application/json"},
                )
            elif request.method == "DELETE":
                resp = await client.delete(url)
            else:
                raise HTTPException(405, f"Method {request.method} not supported")

            return JSONResponse(content=resp.json(), status_code=resp.status_code)

        except httpx.ConnectError:
            raise HTTPException(503, f"Module '{module['name']}' not reachable on port {module['port']}")
        except Exception as e:
            raise HTTPException(502, f"Error from {module['name']}: {str(e)}")


@app.get("/api/quantum/status")
async def quantum_status():
    """Health check all quantum modules."""
    results = {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        for key, module in MODULES.items():
            try:
                resp = await client.get(
                    f"http://localhost:{module['port']}{module['prefix']}/health"
                )
                data = resp.json()
                results[key] = {
                    "name": module['name'],
                    "port": module['port'],
                    "status": data.get('status', 'unknown'),
                    "online": True,
                }
            except Exception:
                results[key] = {
                    "name": module['name'],
                    "port": module['port'],
                    "status": "offline",
                    "online": False,
                }

    online = sum(1 for r in results.values() if r['online'])
    total = len(results)

    return {
        "gateway": "healthy",
        "uptime_seconds": round(time.time() - start_time, 1),
        "modules_online": f"{online}/{total}",
        "modules": results,
    }


@app.get("/api/quantum/info")
async def quantum_info():
    """Overview of available quantum modules."""
    return {
        "gateway_port": SERVICE_PORT,
        "modules": {
            key: {
                "name": m['name'],
                "port": m['port'],
                "docs": f"http://localhost:{m['port']}/docs",
                "health": f"http://localhost:{m['port']}{m['prefix']}/health",
            }
            for key, m in MODULES.items()
        },
    }


# Proxy routes for each module
@app.api_route("/api/credibility/{path:path}", methods=["GET", "POST"])
async def proxy_credibility(path: str, request: Request):
    return await proxy_request("credibility", f"/api/credibility/{path}", request)

@app.api_route("/api/qkd/{path:path}", methods=["GET", "POST"])
async def proxy_qkd(path: str, request: Request):
    return await proxy_request("qkd", f"/api/qkd/{path}", request)

@app.api_route("/api/search/{path:path}", methods=["GET", "POST", "DELETE"])
async def proxy_search(path: str, request: Request):
    return await proxy_request("search", f"/api/search/{path}", request)

@app.api_route("/api/reasoning/{path:path}", methods=["GET", "POST"])
async def proxy_reasoning(path: str, request: Request):
    return await proxy_request("reasoning", f"/api/reasoning/{path}", request)

@app.api_route("/api/emotion/{path:path}", methods=["GET", "POST"])
async def proxy_emotion(path: str, request: Request):
    return await proxy_request("emotion", f"/api/emotion/{path}", request)


if __name__ == "__main__":
    print(f"""
    ╔══════════════════════════════════════════════╗
    ║     JARVIS QUANTUM GATEWAY — Port {SERVICE_PORT}      ║
    ╠══════════════════════════════════════════════╣
    ║  Module 4: Credibility  -> localhost:3031    ║
    ║  Module 6: QKD          -> localhost:3032    ║
    ║  Module 3: Search       -> localhost:3033    ║
    ║  Module 2: Reasoning    -> localhost:3034    ║
    ║  Module 5: Emotion      -> localhost:3035    ║
    ╠══════════════════════════════════════════════╣
    ║  Status: http://localhost:{SERVICE_PORT}/api/quantum/status  ║
    ║  Docs:   http://localhost:{SERVICE_PORT}/docs               ║
    ╚══════════════════════════════════════════════╝
    """)
    uvicorn.run("service:app", host="0.0.0.0", port=SERVICE_PORT, reload=False)
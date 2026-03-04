#!/usr/bin/env python3
"""
Module 4: Credibility Verifier — FastAPI Service
==================================================
Jarvis Quantum Microservice

Endpoints:
  POST /api/credibility/verify     — Single statement
  POST /api/credibility/batch      — Multiple statements
  GET  /api/credibility/health     — Health check
  GET  /api/credibility/config     — Current config

Port: 3031 (configurable)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import time
import os

# ================================================================
# API MODELS
# ================================================================

class VerifyRequest(BaseModel):
    claim: str = Field(..., description="Statement to verify", min_length=3)
    source: Optional[str] = Field(None, description="Source of the claim")

class BatchRequest(BaseModel):
    claims: list[str] = Field(..., description="List of statements to verify", min_items=1, max_items=50)

class CredibilityResult(BaseModel):
    credibility_score: float = Field(..., description="0-1 score (1=fully credible)")
    label: str = Field(..., description="CREDIBLE or NOT_CREDIBLE")
    confidence: float = Field(..., description="Model confidence 0-1")
    method: str = Field(..., description="classical, hybrid, or classical_fallback")
    reasoning: str = Field(..., description="Human-readable explanation")
    classical_score: Optional[float] = None
    quantum_score: Optional[float] = None
    processing_time_ms: float = 0

class VerifyResponse(BaseModel):
    status: str = "success"
    result: CredibilityResult

class BatchResponse(BaseModel):
    status: str = "success"
    results: list[CredibilityResult]
    total_time_ms: float

class HealthResponse(BaseModel):
    status: str
    classical_model: str
    quantum_model: str
    uptime_seconds: float
    version: str

# ================================================================
# SERVICE
# ================================================================

app = FastAPI(
    title="Jarvis Credibility Verifier",
    description="Hybrid classical+quantum credibility verification service",
    version="0.1.0",
)

# Global state
pipeline = None
start_time = time.time()
SERVICE_PORT = int(os.environ.get("CREDIBILITY_PORT", 3031))


@app.on_event("startup")
async def load_models():
    """Load models on service startup."""
    global pipeline
    try:
        from hybrid_pipeline import HybridCredibilityPipeline
        threshold = float(os.environ.get("CONFIDENCE_THRESHOLD", 0.65))
        q_weight = float(os.environ.get("QUANTUM_WEIGHT", 0.6))
        pipeline = HybridCredibilityPipeline(
            model_dir="models",
            confidence_threshold=threshold,
            quantum_weight=q_weight,
        )
        print(f"Credibility service ready on port {SERVICE_PORT}")
    except Exception as e:
        print(f"WARNING: Failed to load models: {e}")
        print("Service running in degraded mode (no predictions)")


@app.get("/api/credibility/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for orchestrator."""
    classical_status = "loaded" if pipeline and pipeline.classical else "not_loaded"
    quantum_status = "loaded" if pipeline and pipeline.quantum else "not_loaded"

    return HealthResponse(
        status="healthy" if pipeline else "degraded",
        classical_model=classical_status,
        quantum_model=quantum_status,
        uptime_seconds=round(time.time() - start_time, 1),
        version="0.1.0",
    )


@app.get("/api/credibility/config")
async def get_config():
    """Return current pipeline configuration."""
    if not pipeline:
        return {"error": "Pipeline not loaded"}
    return {
        "confidence_threshold": pipeline.confidence_threshold,
        "quantum_weight": pipeline.quantum_weight,
        "classical_weight": pipeline.classical_weight,
    }


@app.post("/api/credibility/verify", response_model=VerifyResponse)
async def verify_claim(request: VerifyRequest):
    """Verify credibility of a single claim."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Models not loaded")

    t_start = time.time()
    result = pipeline.verify(request.claim)
    elapsed_ms = (time.time() - t_start) * 1000

    return VerifyResponse(
        result=CredibilityResult(
            credibility_score=result['credibility_score'],
            label=result['label'],
            confidence=result['confidence'],
            method=result['method'],
            reasoning=result['reasoning'],
            classical_score=result['classical_result']['probabilities']['credible'],
            quantum_score=(result['quantum_result']['probabilities']['credible']
                          if result['quantum_result'] and result['quantum_result']['prediction'] != -1
                          else None),
            processing_time_ms=round(elapsed_ms, 1),
        )
    )


@app.post("/api/credibility/batch", response_model=BatchResponse)
async def verify_batch(request: BatchRequest):
    """Verify credibility of multiple claims."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Models not loaded")

    t_start = time.time()
    results = []
    for claim in request.claims:
        result = pipeline.verify(claim)
        results.append(CredibilityResult(
            credibility_score=result['credibility_score'],
            label=result['label'],
            confidence=result['confidence'],
            method=result['method'],
            reasoning=result['reasoning'],
            classical_score=result['classical_result']['probabilities']['credible'],
            quantum_score=(result['quantum_result']['probabilities']['credible']
                          if result['quantum_result'] and result['quantum_result']['prediction'] != -1
                          else None),
        ))
    elapsed_ms = (time.time() - t_start) * 1000

    return BatchResponse(
        results=results,
        total_time_ms=round(elapsed_ms, 1),
    )


if __name__ == "__main__":
    uvicorn.run(
        "service:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=False,
    )
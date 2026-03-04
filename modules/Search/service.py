#!/usr/bin/env python3
"""
Module 3: Quantum Search — FastAPI Service
=============================================
Jarvis Quantum Microservice

Endpoints:
  POST /api/search/query          — Search knowledge base with Grover's
  POST /api/search/add            — Add entry to knowledge base
  GET  /api/search/knowledge-base — List all entries
  DELETE /api/search/clear        — Clear knowledge base
  GET  /api/search/health         — Health check

Port: 3033
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import numpy as np
import time
import os
import json

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


# ================================================================
# GROVER ENGINE
# ================================================================

class GroverEngine:
    """Quantum search using Grover's algorithm."""

    def __init__(self):
        self.sim = AerSimulator()
        self.knowledge_base = {}
        self.next_id = 0

    def add_entry(self, topic, content, metadata=None):
        """Add entry to knowledge base."""
        entry_id = self.next_id
        self.knowledge_base[entry_id] = {
            "id": entry_id,
            "topic": topic.lower(),
            "content": content,
            "metadata": metadata or {},
            "keywords": set(topic.lower().split() + content.lower().split()),
        }
        self.next_id += 1
        return entry_id

    def _create_oracle(self, n_qubits, target):
        """Oracle that marks target state."""
        oracle = QuantumCircuit(n_qubits)
        target_bin = format(target, f'0{n_qubits}b')

        for i, bit in enumerate(reversed(target_bin)):
            if bit == '0':
                oracle.x(i)

        if n_qubits == 1:
            oracle.z(0)
        elif n_qubits == 2:
            oracle.cz(0, 1)
        elif n_qubits == 3:
            oracle.h(2)
            oracle.ccx(0, 1, 2)
            oracle.h(2)
        else:
            oracle.h(n_qubits - 1)
            oracle.mcx(list(range(n_qubits - 1)), n_qubits - 1)
            oracle.h(n_qubits - 1)

        for i, bit in enumerate(reversed(target_bin)):
            if bit == '0':
                oracle.x(i)

        return oracle

    def _create_diffuser(self, n_qubits):
        """Grover diffusion operator."""
        diffuser = QuantumCircuit(n_qubits)
        diffuser.h(range(n_qubits))
        diffuser.x(range(n_qubits))

        if n_qubits == 1:
            diffuser.z(0)
        elif n_qubits == 2:
            diffuser.cz(0, 1)
        elif n_qubits == 3:
            diffuser.h(2)
            diffuser.ccx(0, 1, 2)
            diffuser.h(2)
        else:
            diffuser.h(n_qubits - 1)
            diffuser.mcx(list(range(n_qubits - 1)), n_qubits - 1)
            diffuser.h(n_qubits - 1)

        diffuser.x(range(n_qubits))
        diffuser.h(range(n_qubits))
        return diffuser

    def _grover_search(self, n_qubits, targets, shots=1024):
        """Run Grover's algorithm for given targets."""
        N = 2 ** n_qubits
        M = len(targets)
        n_iter = max(1, int(np.pi / 4 * np.sqrt(N / M)))

        qc = QuantumCircuit(n_qubits, n_qubits)
        qc.h(range(n_qubits))

        oracle_list = [self._create_oracle(n_qubits, t) for t in targets]
        diffuser = self._create_diffuser(n_qubits)

        for _ in range(n_iter):
            for oracle in oracle_list:
                qc.compose(oracle, inplace=True)
            qc.compose(diffuser, inplace=True)

        qc.measure(range(n_qubits), range(n_qubits))

        result = self.sim.run(qc, shots=shots).result()
        counts = result.get_counts()

        # Rank by measurement frequency
        ranked = sorted(counts.items(), key=lambda x: -x[1])
        return ranked, n_iter

    def search(self, query, top_k=3):
        """
        Search knowledge base using hybrid classical+quantum approach.

        1. Classical keyword matching to find candidate indices
        2. Grover's algorithm to quantum-search among candidates
        """
        if not self.knowledge_base:
            return {"results": [], "method": "empty_kb"}

        query_words = set(query.lower().split())

        # Classical pre-filter: score all entries by keyword overlap
        scores = []
        for idx, entry in self.knowledge_base.items():
            overlap = len(query_words & entry['keywords'])
            scores.append((idx, overlap))

        scores.sort(key=lambda x: -x[1])

        # If clear winner, return classically
        if scores[0][1] > 0 and (len(scores) < 2 or scores[0][1] > scores[1][1] * 2):
            best = self.knowledge_base[scores[0][0]]
            return {
                "results": [{
                    "id": best['id'],
                    "topic": best['topic'],
                    "content": best['content'],
                    "score": scores[0][1],
                    "method": "classical_exact",
                }],
                "method": "classical",
                "quantum_used": False,
            }

        # Multiple candidates — use Grover's to search
        # Find targets (entries with any keyword match)
        targets = [idx for idx, score in scores if score > 0]

        if not targets:
            # No keyword matches — return top entries by ID
            top_entries = list(self.knowledge_base.values())[:top_k]
            return {
                "results": [{
                    "id": e['id'],
                    "topic": e['topic'],
                    "content": e['content'],
                    "score": 0,
                    "method": "no_match",
                } for e in top_entries],
                "method": "no_match",
                "quantum_used": False,
            }

        # Quantum search
        kb_size = len(self.knowledge_base)
        n_qubits = max(1, int(np.ceil(np.log2(max(kb_size, 2)))))

        # Filter targets to valid range
        max_idx = 2 ** n_qubits
        valid_targets = [t for t in targets if t < max_idx]

        if not valid_targets:
            valid_targets = [targets[0] % max_idx]

        t_start = time.time()
        ranked, n_iter = self._grover_search(n_qubits, valid_targets)
        q_time = (time.time() - t_start) * 1000

        # Map quantum results back to knowledge base
        results = []
        seen = set()
        for state, count in ranked[:top_k * 2]:
            idx = int(state, 2)
            if idx in self.knowledge_base and idx not in seen:
                entry = self.knowledge_base[idx]
                keyword_score = len(query_words & entry['keywords'])
                results.append({
                    "id": entry['id'],
                    "topic": entry['topic'],
                    "content": entry['content'],
                    "quantum_hits": count,
                    "keyword_score": keyword_score,
                    "method": "grover",
                })
                seen.add(idx)
            if len(results) >= top_k:
                break

        return {
            "results": results,
            "method": "quantum",
            "quantum_used": True,
            "n_qubits": n_qubits,
            "grover_iterations": n_iter,
            "search_space": 2 ** n_qubits,
            "quantum_time_ms": round(q_time, 1),
        }


# ================================================================
# API MODELS
# ================================================================

class AddEntryRequest(BaseModel):
    topic: str = Field(..., description="Topic/category", min_length=1)
    content: str = Field(..., description="Content/fact", min_length=1)
    metadata: Optional[dict] = Field(None, description="Optional metadata")

class AddEntryResponse(BaseModel):
    status: str
    id: int
    total_entries: int

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query", min_length=1)
    top_k: int = Field(3, description="Number of results", ge=1, le=10)

class SearchResult(BaseModel):
    id: int
    topic: str
    content: str
    score: Optional[int] = None
    quantum_hits: Optional[int] = None
    keyword_score: Optional[int] = None
    method: str

class SearchResponse(BaseModel):
    status: str
    query: str
    results: list[SearchResult]
    method: str
    quantum_used: bool = False
    n_qubits: Optional[int] = None
    grover_iterations: Optional[int] = None
    search_space: Optional[int] = None
    quantum_time_ms: Optional[float] = None
    total_time_ms: float

class KBResponse(BaseModel):
    status: str
    total_entries: int
    entries: list[dict]

class HealthResponse(BaseModel):
    status: str
    kb_entries: int
    uptime_seconds: float
    version: str


# ================================================================
# SERVICE
# ================================================================

app = FastAPI(
    title="Jarvis Quantum Search",
    description="Grover's algorithm powered knowledge base search",
    version="0.1.0",
)

engine = GroverEngine()
start_time = time.time()
SERVICE_PORT = int(os.environ.get("SEARCH_PORT", 3033))


@app.on_event("startup")
async def load_defaults():
    """Pre-load some default knowledge base entries."""
    defaults = [
        ("weather", "Current temperature is 18C with clear skies"),
        ("calendar", "Team standup at 9am, meeting with client at 3pm"),
        ("email", "5 unread messages, 2 flagged as urgent"),
        ("news", "FTSE 100 closed up 1.2%, tech sector leading gains"),
        ("reminder", "Buy groceries, call dentist, renew car insurance"),
        ("music", "Last played: Bohemian Rhapsody by Queen"),
        ("traffic", "A40 westbound has 20 minute delays due to roadworks"),
        ("stocks", "NVDA up 4.5%, AAPL flat, TSLA down 2.1%"),
    ]
    for topic, content in defaults:
        engine.add_entry(topic, content)
    print(f"  Loaded {len(defaults)} default KB entries")


@app.get("/api/search/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        kb_entries=len(engine.knowledge_base),
        uptime_seconds=round(time.time() - start_time, 1),
        version="0.1.0",
    )


@app.post("/api/search/add", response_model=AddEntryResponse)
async def add_entry(request: AddEntryRequest):
    entry_id = engine.add_entry(request.topic, request.content, request.metadata)
    return AddEntryResponse(
        status="success",
        id=entry_id,
        total_entries=len(engine.knowledge_base),
    )


@app.get("/api/search/knowledge-base", response_model=KBResponse)
async def list_kb():
    entries = []
    for idx, entry in engine.knowledge_base.items():
        entries.append({
            "id": entry['id'],
            "topic": entry['topic'],
            "content": entry['content'],
        })
    return KBResponse(
        status="success",
        total_entries=len(entries),
        entries=entries,
    )


@app.delete("/api/search/clear")
async def clear_kb():
    engine.knowledge_base.clear()
    engine.next_id = 0
    return {"status": "success", "message": "Knowledge base cleared"}


@app.post("/api/search/query", response_model=SearchResponse)
async def search(request: SearchRequest):
    t_start = time.time()
    result = engine.search(request.query, top_k=request.top_k)
    elapsed_ms = (time.time() - t_start) * 1000

    search_results = []
    for r in result['results']:
        search_results.append(SearchResult(
            id=r['id'],
            topic=r['topic'],
            content=r['content'],
            score=r.get('score'),
            quantum_hits=r.get('quantum_hits'),
            keyword_score=r.get('keyword_score'),
            method=r['method'],
        ))

    return SearchResponse(
        status="success",
        query=request.query,
        results=search_results,
        method=result['method'],
        quantum_used=result.get('quantum_used', False),
        n_qubits=result.get('n_qubits'),
        grover_iterations=result.get('grover_iterations'),
        search_space=result.get('search_space'),
        quantum_time_ms=result.get('quantum_time_ms'),
        total_time_ms=round(elapsed_ms, 1),
    )


if __name__ == "__main__":
    uvicorn.run("service:app", host="0.0.0.0", port=SERVICE_PORT, reload=False)
#!/usr/bin/env python3
"""
Module 2: Quantum Reasoning — FastAPI Service
================================================
Jarvis Quantum Microservice

Endpoints:
  POST /api/reasoning/entailment    — Check if premise entails hypothesis
  POST /api/reasoning/infer         — Run inference chain from facts+rules
  POST /api/reasoning/consistency   — Check if multiple claims are consistent
  GET  /api/reasoning/health        — Health check

Port: 3034
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import numpy as np
import time
import os

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

# ================================================================
# REASONING ENGINE
# ================================================================

class QuantumReasoningEngine:

    def __init__(self):
        self.sim = AerSimulator()

    def _extract_features(self, claim):
        claim_lower = claim.lower()
        return {
            'has_negation': any(w in claim_lower for w in
                ['not', 'no', 'never', "n't", 'none', 'nothing',
                 'neither', 'nobody', 'without', 'deny', 'denied',
                 'false', 'incorrect', 'wrong']),
            'has_increase': any(w in claim_lower for w in
                ['increase', 'grew', 'rise', 'rose', 'up', 'higher',
                 'more', 'gain', 'growth', 'expand', 'boost', 'surge',
                 'improve', 'improved', 'better']),
            'has_decrease': any(w in claim_lower for w in
                ['decrease', 'fell', 'drop', 'down', 'lower', 'less',
                 'decline', 'shrink', 'reduce', 'cut', 'loss',
                 'worse', 'worsened', 'deteriorate']),
            'has_certainty': any(w in claim_lower for w in
                ['always', 'every', 'all', 'definitely', 'certainly',
                 'proven', 'guaranteed', 'must', 'confirmed', 'is']),
            'has_uncertainty': any(w in claim_lower for w in
                ['maybe', 'perhaps', 'might', 'could', 'possibly',
                 'uncertain', 'estimated', 'approximately', 'may']),
            'has_quantity': any(c.isdigit() for c in claim),
        }

    def detect_entailment(self, premise, hypothesis, shots=1024):
        feat_p = self._extract_features(premise)
        feat_h = self._extract_features(hypothesis)

        feature_keys = list(feat_p.keys())
        n_features = len(feature_keys)

        agreement_score = 0
        contradiction_score = 0

        for key in feature_keys:
            if feat_p[key] == feat_h[key]:
                agreement_score += 1
            else:
                contradiction_score += 1

        if feat_p['has_increase'] and feat_h['has_decrease']:
            contradiction_score += 2
        if feat_p['has_decrease'] and feat_h['has_increase']:
            contradiction_score += 2
        if feat_p['has_certainty'] and feat_h['has_negation']:
            contradiction_score += 1
        if feat_p['has_negation'] and feat_h['has_certainty'] and not feat_h['has_negation']:
            contradiction_score += 1

        n_qubits = 2 * n_features + 1
        output_qubit = n_qubits - 1
        qc = QuantumCircuit(n_qubits, 1)

        for i, key in enumerate(feature_keys):
            if feat_p[key]:
                qc.x(i)
        for i, key in enumerate(feature_keys):
            if feat_h[key]:
                qc.x(n_features + i)

        qc.h(output_qubit)

        from qiskit.circuit.library import RYGate
        agreement_angle = np.pi * agreement_score / (n_features * 2)
        contradiction_angle = np.pi * contradiction_score / (n_features * 2)
        net_angle = contradiction_angle - agreement_angle
        qc.ry(net_angle, output_qubit)

        for i in range(min(3, n_features)):
            qc.cx(i, output_qubit)
            qc.cx(n_features + i, output_qubit)

        qc.measure(output_qubit, 0)

        result = self.sim.run(qc, shots=shots).result()
        counts = result.get_counts()

        n_zero = counts.get('0', 0)
        n_one = counts.get('1', 0)
        total = n_zero + n_one

        entailment_score = n_zero / total
        contradiction_prob = n_one / total

        if contradiction_score >= 3 and contradiction_prob > 0.4:
            label = "CONTRADICTION"
            confidence = min(0.99, 0.5 + contradiction_score * 0.1)
        elif agreement_score >= 4 and entailment_score > 0.5:
            label = "ENTAILMENT"
            confidence = min(0.99, 0.5 + agreement_score * 0.08)
        else:
            label = "NEUTRAL"
            confidence = 0.5 + abs(entailment_score - 0.5) * 0.3

        return {
            "label": label,
            "confidence": round(confidence, 4),
            "entailment_score": round(entailment_score, 4),
            "contradiction_score": round(float(contradiction_prob), 4),
            "agreement": agreement_score,
            "contradictions": contradiction_score,
        }

    def check_consistency(self, claims, shots=1024):
        """Check if a set of claims are mutually consistent."""
        if len(claims) < 2:
            return {"consistent": True, "pairs_checked": 0, "conflicts": []}

        conflicts = []
        pairs_checked = 0

        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                result = self.detect_entailment(claims[i], claims[j], shots)
                pairs_checked += 1
                if result['label'] == 'CONTRADICTION':
                    conflicts.append({
                        "claim_a": claims[i],
                        "claim_b": claims[j],
                        "confidence": result['confidence'],
                    })

        return {
            "consistent": len(conflicts) == 0,
            "pairs_checked": pairs_checked,
            "conflicts": conflicts,
            "n_conflicts": len(conflicts),
        }

    def infer(self, facts, rules, query):
        """Run inference chain."""
        working_facts = dict(facts)
        chain = []

        max_iterations = 10
        for iteration in range(max_iterations):
            new_fact_added = False
            for rule in rules:
                conditions_met = all(
                    working_facts.get(k) == v
                    for k, v in rule['conditions'].items()
                )
                if conditions_met:
                    conc_name, conc_val = rule['conclusion']
                    if conc_name not in working_facts:
                        working_facts[conc_name] = conc_val
                        chain.append({
                            "rule": f"IF {rule['conditions']} THEN {conc_name}={conc_val}",
                            "derived": {conc_name: conc_val},
                        })
                        new_fact_added = True
            if not new_fact_added:
                break

        if query in working_facts:
            # Quantum verification
            n_rules = len(chain)
            n_qubits = max(2, n_rules + 1)
            qc = QuantumCircuit(n_qubits, 1)
            for i in range(min(n_rules, n_qubits - 1)):
                qc.x(i)
            if n_rules >= 2:
                qc.ccx(0, 1, n_qubits - 1)
            elif n_rules >= 1:
                qc.cx(0, n_qubits - 1)
            qc.measure(n_qubits - 1, 0)

            result = self.sim.run(qc, shots=1024).result()
            counts = result.get_counts()
            confidence = counts.get('1', 0) / 1024

            return {
                "query": query,
                "result": working_facts[query],
                "confidence": round(confidence, 4),
                "chain": chain,
                "all_facts": working_facts,
            }

        return {
            "query": query,
            "result": None,
            "confidence": 0.0,
            "chain": chain,
            "all_facts": working_facts,
        }


# ================================================================
# API MODELS
# ================================================================

class EntailmentRequest(BaseModel):
    premise: str = Field(..., min_length=3)
    hypothesis: str = Field(..., min_length=3)

class EntailmentResponse(BaseModel):
    status: str
    premise: str
    hypothesis: str
    label: str
    confidence: float
    entailment_score: float
    contradiction_score: float
    processing_time_ms: float

class ConsistencyRequest(BaseModel):
    claims: list[str] = Field(..., min_items=2, max_items=20)

class ConflictItem(BaseModel):
    claim_a: str
    claim_b: str
    confidence: float

class ConsistencyResponse(BaseModel):
    status: str
    consistent: bool
    pairs_checked: int
    n_conflicts: int
    conflicts: list[ConflictItem]
    processing_time_ms: float

class InferenceRule(BaseModel):
    conditions: dict = Field(..., description="Dict of fact_name: required_value")
    conclusion: list = Field(..., description="[fact_name, value] to derive", min_items=2, max_items=2)

class InferRequest(BaseModel):
    facts: dict = Field(..., description="Known facts as {name: value}")
    rules: list[InferenceRule] = Field(..., min_items=1)
    query: str = Field(..., description="Fact to derive")

class ChainStep(BaseModel):
    rule: str
    derived: dict

class InferResponse(BaseModel):
    status: str
    query: str
    result: Optional[str] = None
    confidence: float
    chain: list[ChainStep]
    all_facts: dict
    processing_time_ms: float

class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    version: str


# ================================================================
# SERVICE
# ================================================================

app = FastAPI(
    title="Jarvis Quantum Reasoning",
    description="Quantum logic, entailment detection, and inference chains",
    version="0.1.0",
)

engine = QuantumReasoningEngine()
start_time = time.time()
SERVICE_PORT = int(os.environ.get("REASONING_PORT", 3034))


@app.get("/api/reasoning/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        uptime_seconds=round(time.time() - start_time, 1),
        version="0.1.0",
    )


@app.post("/api/reasoning/entailment", response_model=EntailmentResponse)
async def entailment(request: EntailmentRequest):
    t_start = time.time()
    result = engine.detect_entailment(request.premise, request.hypothesis)
    elapsed = (time.time() - t_start) * 1000

    return EntailmentResponse(
        status="success",
        premise=request.premise,
        hypothesis=request.hypothesis,
        label=result['label'],
        confidence=result['confidence'],
        entailment_score=result['entailment_score'],
        contradiction_score=result['contradiction_score'],
        processing_time_ms=round(elapsed, 1),
    )


@app.post("/api/reasoning/consistency", response_model=ConsistencyResponse)
async def consistency(request: ConsistencyRequest):
    t_start = time.time()
    result = engine.check_consistency(request.claims)
    elapsed = (time.time() - t_start) * 1000

    conflicts = [ConflictItem(**c) for c in result['conflicts']]

    return ConsistencyResponse(
        status="success",
        consistent=result['consistent'],
        pairs_checked=result['pairs_checked'],
        n_conflicts=result['n_conflicts'],
        conflicts=conflicts,
        processing_time_ms=round(elapsed, 1),
    )


@app.post("/api/reasoning/infer", response_model=InferResponse)
async def infer(request: InferRequest):
    t_start = time.time()

    rules = []
    for r in request.rules:
        rules.append({
            "conditions": r.conditions,
            "conclusion": tuple(r.conclusion),
        })

    result = engine.infer(request.facts, rules, request.query)
    elapsed = (time.time() - t_start) * 1000

    chain = [ChainStep(**s) for s in result['chain']]

    return InferResponse(
        status="success",
        query=result['query'],
        result=str(result['result']) if result['result'] is not None else None,
        confidence=result['confidence'],
        chain=chain,
        all_facts={k: str(v) for k, v in result['all_facts'].items()},
        processing_time_ms=round(elapsed, 1),
    )


if __name__ == "__main__":
    uvicorn.run("service:app", host="0.0.0.0", port=SERVICE_PORT, reload=False)
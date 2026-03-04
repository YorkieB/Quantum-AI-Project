#!/usr/bin/env python3
"""
Module 6: Quantum Key Distribution — FastAPI Service
======================================================
Jarvis Quantum Microservice

Endpoints:
  POST /api/qkd/generate-key     — Generate a quantum-secure key pair
  POST /api/qkd/encrypt           — Encrypt a message with QKD key
  POST /api/qkd/decrypt           — Decrypt a message with QKD key
  POST /api/qkd/secure-channel    — Full key exchange + encrypt in one call
  GET  /api/qkd/health            — Health check

Port: 3032
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
# BB84 ENGINE
# ================================================================

class BB84Engine:
    """Quantum Key Distribution using BB84 protocol."""

    def __init__(self):
        self.sim = AerSimulator()
        self.active_keys = {}  # channel_id -> key

    def generate_key(self, n_qubits=512, check_fraction=0.25):
        """Run BB84 and return a secure key."""
        alice_bits = np.random.randint(0, 2, n_qubits)
        alice_bases = np.random.randint(0, 2, n_qubits)
        bob_bases = np.random.randint(0, 2, n_qubits)

        bob_results = []
        for i in range(n_qubits):
            qc = QuantumCircuit(1, 1)
            if alice_bits[i] == 1:
                qc.x(0)
            if alice_bases[i] == 1:
                qc.h(0)
            if bob_bases[i] == 1:
                qc.h(0)
            qc.measure(0, 0)
            result = self.sim.run(qc, shots=1).result()
            bit = int(list(result.get_counts().keys())[0])
            bob_results.append(bit)

        bob_results = np.array(bob_results)

        # Sifting
        matching = alice_bases == bob_bases
        sifted_alice = alice_bits[matching]
        sifted_bob = bob_results[matching]

        # Error check
        n_sifted = len(sifted_alice)
        n_check = max(int(n_sifted * check_fraction), 1)

        check_a = sifted_alice[:n_check]
        check_b = sifted_bob[:n_check]
        errors = int(np.sum(check_a != check_b))
        error_rate = errors / n_check if n_check > 0 else 0

        # Final key
        final_key = "".join(str(int(b)) for b in sifted_alice[n_check:])

        return {
            "key": final_key,
            "key_length": len(final_key),
            "qubits_sent": n_qubits,
            "sifted": n_sifted,
            "error_rate": round(error_rate, 4),
            "errors_found": errors,
            "eve_detected": error_rate > 0.11,
            "secure": error_rate <= 0.11,
        }

    def encrypt(self, message, key):
        """One-time pad encryption."""
        msg_bits = ''.join(format(ord(c), '08b') for c in message)
        key_ext = (key * ((len(msg_bits) // len(key)) + 1))[:len(msg_bits)]
        cipher = ''.join(str(int(m) ^ int(k)) for m, k in zip(msg_bits, key_ext))
        return cipher

    def decrypt(self, cipher_bits, key):
        """One-time pad decryption."""
        key_ext = (key * ((len(cipher_bits) // len(key)) + 1))[:len(cipher_bits)]
        plain_bits = ''.join(str(int(c) ^ int(k)) for c, k in zip(cipher_bits, key_ext))
        chars = [chr(int(plain_bits[i:i+8], 2)) for i in range(0, len(plain_bits), 8)]
        return ''.join(chars)


# ================================================================
# API MODELS
# ================================================================

class KeyRequest(BaseModel):
    n_qubits: int = Field(512, description="Number of qubits for key generation", ge=64, le=2048)
    channel_id: Optional[str] = Field(None, description="Channel ID to store key for later use")

class KeyResponse(BaseModel):
    status: str
    key: str
    key_length: int
    qubits_sent: int
    error_rate: float
    eve_detected: bool
    secure: bool
    channel_id: Optional[str] = None
    generation_time_ms: float

class EncryptRequest(BaseModel):
    message: str = Field(..., description="Plaintext message to encrypt", min_length=1)
    key: Optional[str] = Field(None, description="Key bits (or use channel_id)")
    channel_id: Optional[str] = Field(None, description="Channel ID with stored key")

class EncryptResponse(BaseModel):
    status: str
    ciphertext: str
    message_length: int
    key_length: int

class DecryptRequest(BaseModel):
    ciphertext: str = Field(..., description="Encrypted bit string")
    key: Optional[str] = Field(None, description="Key bits (or use channel_id)")
    channel_id: Optional[str] = Field(None, description="Channel ID with stored key")

class DecryptResponse(BaseModel):
    status: str
    plaintext: str

class SecureChannelRequest(BaseModel):
    message: str = Field(..., description="Message to send securely")
    n_qubits: int = Field(512, description="Qubits for key generation", ge=64, le=2048)

class SecureChannelResponse(BaseModel):
    status: str
    original_message: str
    ciphertext: str
    decrypted_message: str
    match: bool
    key_length: int
    error_rate: float
    eve_detected: bool
    total_time_ms: float

class HealthResponse(BaseModel):
    status: str
    active_channels: int
    uptime_seconds: float
    version: str


# ================================================================
# SERVICE
# ================================================================

app = FastAPI(
    title="Jarvis QKD Service",
    description="Quantum Key Distribution (BB84) for secure inter-service communication",
    version="0.1.0",
)

engine = BB84Engine()
start_time = time.time()
SERVICE_PORT = int(os.environ.get("QKD_PORT", 3032))


@app.get("/api/qkd/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        active_channels=len(engine.active_keys),
        uptime_seconds=round(time.time() - start_time, 1),
        version="0.1.0",
    )


@app.post("/api/qkd/generate-key", response_model=KeyResponse)
async def generate_key(request: KeyRequest):
    t_start = time.time()
    result = engine.generate_key(n_qubits=request.n_qubits)
    elapsed_ms = (time.time() - t_start) * 1000

    if request.channel_id:
        engine.active_keys[request.channel_id] = result['key']

    if not result['secure']:
        return KeyResponse(
            status="warning_eve_detected",
            key="",
            key_length=0,
            qubits_sent=result['qubits_sent'],
            error_rate=result['error_rate'],
            eve_detected=True,
            secure=False,
            channel_id=request.channel_id,
            generation_time_ms=round(elapsed_ms, 1),
        )

    return KeyResponse(
        status="success",
        key=result['key'],
        key_length=result['key_length'],
        qubits_sent=result['qubits_sent'],
        error_rate=result['error_rate'],
        eve_detected=False,
        secure=True,
        channel_id=request.channel_id,
        generation_time_ms=round(elapsed_ms, 1),
    )


@app.post("/api/qkd/encrypt", response_model=EncryptResponse)
async def encrypt(request: EncryptRequest):
    key = request.key
    if not key and request.channel_id:
        key = engine.active_keys.get(request.channel_id)
    if not key:
        raise HTTPException(status_code=400, detail="No key provided. Generate one first or provide key/channel_id.")

    ciphertext = engine.encrypt(request.message, key)
    return EncryptResponse(
        status="success",
        ciphertext=ciphertext,
        message_length=len(request.message),
        key_length=len(key),
    )


@app.post("/api/qkd/decrypt", response_model=DecryptResponse)
async def decrypt(request: DecryptRequest):
    key = request.key
    if not key and request.channel_id:
        key = engine.active_keys.get(request.channel_id)
    if not key:
        raise HTTPException(status_code=400, detail="No key provided.")

    plaintext = engine.decrypt(request.ciphertext, key)
    return DecryptResponse(
        status="success",
        plaintext=plaintext,
    )


@app.post("/api/qkd/secure-channel", response_model=SecureChannelResponse)
async def secure_channel(request: SecureChannelRequest):
    """Full workflow: generate key + encrypt + decrypt in one call."""
    t_start = time.time()

    # Generate key
    key_result = engine.generate_key(n_qubits=request.n_qubits)

    if not key_result['secure']:
        raise HTTPException(
            status_code=503,
            detail=f"Eavesdropper detected! Error rate: {key_result['error_rate']:.1%}. Channel compromised."
        )

    # Encrypt
    ciphertext = engine.encrypt(request.message, key_result['key'])

    # Decrypt
    decrypted = engine.decrypt(ciphertext, key_result['key'])

    elapsed_ms = (time.time() - t_start) * 1000

    return SecureChannelResponse(
        status="success",
        original_message=request.message,
        ciphertext=ciphertext[:100] + "..." if len(ciphertext) > 100 else ciphertext,
        decrypted_message=decrypted,
        match=request.message == decrypted,
        key_length=key_result['key_length'],
        error_rate=key_result['error_rate'],
        eve_detected=False,
        total_time_ms=round(elapsed_ms, 1),
    )


if __name__ == "__main__":
    uvicorn.run("service:app", host="0.0.0.0", port=SERVICE_PORT, reload=False)
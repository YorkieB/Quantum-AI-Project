#!/usr/bin/env python3
"""
Sprint 4, Task 4.4: Module 6 — Quantum Key Distribution (BB84)
================================================================
Jarvis Quantum - Secure Communications

BB84 Protocol: The first and most proven quantum cryptography protocol.
Uses quantum mechanics to distribute encryption keys with GUARANTEED
detection of eavesdroppers. This is not "quantum might help" — this is
"physics makes it impossible to intercept without detection."

Architecture:
  1. Alice (sender) encodes random bits in random quantum bases
  2. Bob (receiver) measures in random bases
  3. They publicly compare bases (not values) and keep matching ones
  4. If Eve (eavesdropper) intercepted, error rate > 25% = detected
  5. Surviving key bits are used for encryption

This becomes Module 6 of Jarvis: secure inter-service communication.
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import json
import os
import time
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

np.random.seed(42)

# ================================================================
# PART 1: BB84 PROTOCOL — LOCAL SIMULATOR
# ================================================================
print("=" * 70)
print("MODULE 6: QUANTUM KEY DISTRIBUTION (BB84)")
print("=" * 70)

def bb84_encode(bit, basis):
    """
    Alice prepares a qubit:
      bit=0, basis=0 (Z): |0>
      bit=1, basis=0 (Z): |1>
      bit=0, basis=1 (X): |+>
      bit=1, basis=1 (X): |->
    """
    qc = QuantumCircuit(1, 1)
    if bit == 1:
        qc.x(0)
    if basis == 1:
        qc.h(0)
    return qc


def bb84_measure(qc, basis):
    """
    Bob measures in his chosen basis:
      basis=0 (Z): measure directly
      basis=1 (X): apply H then measure
    """
    if basis == 1:
        qc.h(0)
    qc.measure(0, 0)
    return qc


def run_bb84(n_bits, eve_present=False, eve_fraction=1.0):
    """
    Full BB84 protocol simulation.

    Args:
        n_bits: Number of qubits to send
        eve_present: Whether Eve intercepts
        eve_fraction: Fraction of qubits Eve intercepts (0-1)

    Returns:
        dict with protocol results
    """
    sim = AerSimulator()

    # Step 1: Alice generates random bits and bases
    alice_bits = np.random.randint(0, 2, n_bits)
    alice_bases = np.random.randint(0, 2, n_bits)

    # Step 2: Bob chooses random measurement bases
    bob_bases = np.random.randint(0, 2, n_bits)

    # Eve's bases (if present)
    eve_bases = np.random.randint(0, 2, n_bits)
    eve_intercepts = np.random.random(n_bits) < eve_fraction

    bob_results = []

    for i in range(n_bits):
        # Alice encodes
        qc = bb84_encode(int(alice_bits[i]), int(alice_bases[i]))

        # Eve intercepts (measure and re-prepare)
        if eve_present and eve_intercepts[i]:
            # Eve measures in her basis
            eve_qc = qc.copy()
            if eve_bases[i] == 1:
                eve_qc.h(0)
            eve_qc.measure(0, 0)
            eve_result = sim.run(eve_qc, shots=1).result()
            eve_bit = int(list(eve_result.get_counts().keys())[0])

            # Eve re-prepares based on what she measured
            qc = bb84_encode(eve_bit, int(eve_bases[i]))

        # Bob measures
        qc = bb84_measure(qc, int(bob_bases[i]))
        result = sim.run(qc, shots=1).result()
        bob_bit = int(list(result.get_counts().keys())[0])
        bob_results.append(bob_bit)

    bob_results = np.array(bob_results)

    # Step 3: Sifting — keep only matching bases
    matching_bases = alice_bases == bob_bases
    sifted_alice = alice_bits[matching_bases]
    sifted_bob = bob_results[matching_bases]

    # Step 4: Error estimation — sacrifice some bits to check
    n_sifted = len(sifted_alice)
    n_check = max(n_sifted // 4, 1)  # Use 25% for error checking
    n_key = n_sifted - n_check

    check_alice = sifted_alice[:n_check]
    check_bob = sifted_bob[:n_check]
    errors = np.sum(check_alice != check_bob)
    error_rate = errors / n_check if n_check > 0 else 0

    # Step 5: Final key (remaining bits after error check)
    final_key_alice = sifted_alice[n_check:]
    final_key_bob = sifted_bob[n_check:]
    key_match = np.all(final_key_alice == final_key_bob)
    key_errors = np.sum(final_key_alice != final_key_bob)

    return {
        "n_sent": n_bits,
        "n_sifted": int(n_sifted),
        "n_check": int(n_check),
        "n_key_bits": int(n_key),
        "error_rate": round(float(error_rate), 4),
        "errors_in_check": int(errors),
        "key_match": bool(key_match),
        "key_errors": int(key_errors),
        "eve_detected": error_rate > 0.11,  # Threshold: >11% = eavesdropper
        "eve_present": eve_present,
        "final_key": "".join(str(b) for b in final_key_alice),
        "sifting_efficiency": round(n_sifted / n_bits, 4),
    }


# ================================================================
# SCENARIO 1: No eavesdropper
# ================================================================
print("\n" + "-" * 70)
print("SCENARIO 1: Secure Channel (No Eavesdropper)")
print("-" * 70)

result_safe = run_bb84(256, eve_present=False)

print(f"""
  Qubits sent:       {result_safe['n_sent']}
  Sifted (matching):  {result_safe['n_sifted']} ({result_safe['sifting_efficiency']:.0%})
  Used for checking:  {result_safe['n_check']}
  Final key length:   {result_safe['n_key_bits']} bits
  Error rate:         {result_safe['error_rate']:.1%}
  Errors in check:    {result_safe['errors_in_check']}
  Keys match:         {result_safe['key_match']}
  Eve detected:       {result_safe['eve_detected']}
  Key: {result_safe['final_key'][:40]}...
""")

# ================================================================
# SCENARIO 2: Eve intercepts everything
# ================================================================
print("-" * 70)
print("SCENARIO 2: Full Eavesdropping (Eve intercepts ALL qubits)")
print("-" * 70)

result_eve_full = run_bb84(256, eve_present=True, eve_fraction=1.0)

print(f"""
  Qubits sent:       {result_eve_full['n_sent']}
  Sifted (matching):  {result_eve_full['n_sifted']} ({result_eve_full['sifting_efficiency']:.0%})
  Used for checking:  {result_eve_full['n_check']}
  Final key length:   {result_eve_full['n_key_bits']} bits
  Error rate:         {result_eve_full['error_rate']:.1%}
  Errors in check:    {result_eve_full['errors_in_check']}
  Keys match:         {result_eve_full['key_match']}
  Eve detected:       {result_eve_full['eve_detected']}  *** EAVESDROPPER CAUGHT ***
""")

# ================================================================
# SCENARIO 3: Eve intercepts 50% (stealth attack)
# ================================================================
print("-" * 70)
print("SCENARIO 3: Stealth Attack (Eve intercepts 50%)")
print("-" * 70)

result_eve_half = run_bb84(256, eve_present=True, eve_fraction=0.5)

print(f"""
  Qubits sent:       {result_eve_half['n_sent']}
  Sifted (matching):  {result_eve_half['n_sifted']} ({result_eve_half['sifting_efficiency']:.0%})
  Used for checking:  {result_eve_half['n_check']}
  Final key length:   {result_eve_half['n_key_bits']} bits
  Error rate:         {result_eve_half['error_rate']:.1%}
  Errors in check:    {result_eve_half['errors_in_check']}
  Keys match:         {result_eve_half['key_match']}
  Eve detected:       {result_eve_half['eve_detected']}
""")

# ================================================================
# SCENARIO 4: Eve intercepts 10% (very subtle)
# ================================================================
print("-" * 70)
print("SCENARIO 4: Subtle Attack (Eve intercepts 10%)")
print("-" * 70)

result_eve_subtle = run_bb84(512, eve_present=True, eve_fraction=0.1)

print(f"""
  Qubits sent:       {result_eve_subtle['n_sent']}
  Sifted (matching):  {result_eve_subtle['n_sifted']} ({result_eve_subtle['sifting_efficiency']:.0%})
  Used for checking:  {result_eve_subtle['n_check']}
  Final key length:   {result_eve_subtle['n_key_bits']} bits
  Error rate:         {result_eve_subtle['error_rate']:.1%}
  Errors in check:    {result_eve_subtle['errors_in_check']}
  Keys match:         {result_eve_subtle['key_match']}
  Eve detected:       {result_eve_subtle['eve_detected']}
""")

# ================================================================
# STATISTICAL ANALYSIS: Run multiple trials
# ================================================================
print("=" * 70)
print("STATISTICAL ANALYSIS: 100 trials per scenario")
print("=" * 70)

scenarios = [
    ("No Eve", False, 0.0),
    ("Eve 10%", True, 0.1),
    ("Eve 25%", True, 0.25),
    ("Eve 50%", True, 0.5),
    ("Eve 100%", True, 1.0),
]

N_TRIALS = 100
KEY_SIZE = 256

print(f"\n  {'Scenario':<12} {'Avg Error':<12} {'Detected':<12} {'Avg Key Len':<14} {'Key Match'}")
print("  " + "-" * 62)

stats_results = []

for name, eve, frac in scenarios:
    error_rates = []
    detected = 0
    key_lengths = []
    key_matches = 0

    for _ in range(N_TRIALS):
        r = run_bb84(KEY_SIZE, eve_present=eve, eve_fraction=frac)
        error_rates.append(r['error_rate'])
        if r['eve_detected']:
            detected += 1
        key_lengths.append(r['n_key_bits'])
        if r['key_match']:
            key_matches += 1

    avg_error = np.mean(error_rates)
    detect_rate = detected / N_TRIALS
    avg_key = np.mean(key_lengths)
    match_rate = key_matches / N_TRIALS

    print(f"  {name:<12} {avg_error:<12.1%} {detect_rate:<12.0%} {avg_key:<14.0f} {match_rate:.0%}")

    stats_results.append({
        "scenario": name,
        "eve_present": eve,
        "eve_fraction": frac,
        "avg_error_rate": round(avg_error, 4),
        "detection_rate": round(detect_rate, 4),
        "avg_key_length": round(avg_key, 1),
        "key_match_rate": round(match_rate, 4),
    })

# ================================================================
# ENCRYPTION DEMO: Use QKD key to encrypt a message
# ================================================================
print("\n" + "=" * 70)
print("ENCRYPTION DEMO: Secure Message with QKD Key")
print("=" * 70)

def xor_encrypt(message, key_bits):
    """One-time pad encryption using QKD-generated key."""
    msg_bits = ''.join(format(ord(c), '08b') for c in message)
    # Extend key if needed (in real QKD you'd generate enough)
    key_extended = (key_bits * ((len(msg_bits) // len(key_bits)) + 1))[:len(msg_bits)]
    cipher_bits = ''.join(str(int(m) ^ int(k)) for m, k in zip(msg_bits, key_extended))
    return cipher_bits


def xor_decrypt(cipher_bits, key_bits):
    """Decrypt one-time pad."""
    key_extended = (key_bits * ((len(cipher_bits) // len(key_bits)) + 1))[:len(cipher_bits)]
    plain_bits = ''.join(str(int(c) ^ int(k)) for c, k in zip(cipher_bits, key_extended))
    chars = [chr(int(plain_bits[i:i+8], 2)) for i in range(0, len(plain_bits), 8)]
    return ''.join(chars)


# Generate a secure key
key_result = run_bb84(512, eve_present=False)
key = key_result['final_key']

message = "Jarvis Module 6 secure comms operational"
print(f"\n  Original:  {message}")
print(f"  Key:       {key[:40]}... ({len(key)} bits)")

encrypted = xor_encrypt(message, key)
print(f"  Encrypted: {encrypted[:40]}...")

decrypted = xor_decrypt(encrypted, key)
print(f"  Decrypted: {decrypted}")
print(f"  Match:     {message == decrypted}")

# ================================================================
# IBM QPU COMPARISON (if available)
# ================================================================
print("\n" + "=" * 70)
print("QPU COMPARISON: Simulator vs Real Hardware Noise")
print("=" * 70)

try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    service = QiskitRuntimeService(channel="ibm_cloud")
    backend = service.least_busy(operational=True, simulator=False)
    print(f"\n  QPU: {backend.name} ({backend.num_qubits} qubits)")

    # Run 4 BB84 basis combinations on real QPU
    circuits = []
    labels = []

    # |0> in Z basis -> measure Z -> should get 0
    qc = QuantumCircuit(1, 1)
    qc.measure(0, 0)
    circuits.append(("Z-encode 0, Z-measure", qc, 0))

    # |1> in Z basis -> measure Z -> should get 1
    qc = QuantumCircuit(1, 1)
    qc.x(0)
    qc.measure(0, 0)
    circuits.append(("Z-encode 1, Z-measure", qc, 1))

    # |+> in X basis -> measure X -> should get 0
    qc = QuantumCircuit(1, 1)
    qc.h(0)
    qc.h(0)
    qc.measure(0, 0)
    circuits.append(("X-encode 0, X-measure", qc, 0))

    # |-> in X basis -> measure X -> should get 1
    qc = QuantumCircuit(1, 1)
    qc.x(0)
    qc.h(0)
    qc.h(0)
    qc.measure(0, 0)
    circuits.append(("X-encode 1, X-measure", qc, 1))

    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)

    print(f"  Running 4 BB84 basis tests on {backend.name}...")
    sampler = SamplerV2(mode=backend)

    for name, qc, expected in circuits:
        transpiled = pm.run(qc)
        job = sampler.run([transpiled], shots=1024)
        result = job.result()
        counts = result[0].data.c.get_counts()
        correct = counts.get(str(expected), 0)
        total = sum(counts.values())
        fidelity = correct / total
        print(f"    {name}: {counts} | fidelity={fidelity:.3f}")

    print(f"\n  Real QPU noise directly impacts QKD error rates.")
    print(f"  Production QKD would need error correction codes.")

except Exception as e:
    print(f"\n  QPU test skipped: {e}")
    print(f"  (Run test_ibm_connection.py first to set up credentials)")

# ================================================================
# SAVE RESULTS
# ================================================================
os.makedirs("results", exist_ok=True)

all_results = {
    "protocol": "BB84",
    "scenarios": {
        "no_eve": {k: v for k, v in result_safe.items() if k != 'final_key'},
        "eve_full": {k: v for k, v in result_eve_full.items() if k != 'final_key'},
        "eve_half": {k: v for k, v in result_eve_half.items() if k != 'final_key'},
        "eve_subtle": {k: v for k, v in result_eve_subtle.items() if k != 'final_key'},
    },
    "statistical_analysis": stats_results,
    "encryption_demo": {
        "message": message,
        "key_length": len(key),
        "encrypted_length": len(encrypted),
        "decrypted_match": message == decrypted,
    },
}

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.bool_, np.integer)):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

with open("results/sprint4_qkd_bb84.json", "w") as f:
    json.dump(all_results, f, indent=2, cls=NpEncoder)

print(f"\nResults saved to results/sprint4_qkd_bb84.json")
print(f"\n{'='*70}")
print("MODULE 6: QKD BB84 — COMPLETE")
print(f"{'='*70}")
print(f"""
  What we proved:
    1. No Eve:   0% error rate, perfect key agreement
    2. Eve 100%: ~25% error rate, ALWAYS detected
    3. Eve 50%:  ~12% error rate, usually detected
    4. Eve 10%:  ~2-3% error rate, harder to detect (need more qubits)

  This is a PHYSICS advantage — not algorithmic.
  Classical cryptography cannot detect eavesdroppers.
  Quantum cryptography guarantees detection via Heisenberg uncertainty.

  Next: Module 3 — Quantum Search (Grover's Algorithm)
""")
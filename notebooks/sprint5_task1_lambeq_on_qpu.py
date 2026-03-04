#!/usr/bin/env python3
"""
Sprint 5, Task 5.1: Quantum NLU on Real IBM QPU
==================================================
Trains an IQP variational classifier on simulator,
then runs the same trained circuits on real quantum hardware.
Compares simulator vs QPU accuracy.
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import json
import os
import time

from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from scipy.optimize import minimize

np.random.seed(42)
sim = AerSimulator()

# ================================================================
# PART 1: CONNECT TO IBM QPU
# ================================================================
print("=" * 70)
print("SPRINT 5: NLU CLASSIFIER ON REAL QUANTUM HARDWARE")
print("=" * 70)

print("\nConnecting to IBM Quantum...")
service = QiskitRuntimeService(channel="ibm_cloud")
backend = service.least_busy(operational=True, simulator=False)
print(f"  QPU: {backend.name} ({backend.num_qubits} qubits)")
print(f"  Pending jobs: {backend.status().pending_jobs}")

# ================================================================
# PART 2: DATA
# ================================================================
print("\n" + "-" * 70)
print("PART 2: Training & Test Data")
print("-" * 70)

train_data = [
    ("search for pizza places", 0),
    ("look up the news", 0),
    ("find information about python", 0),
    ("what is machine learning", 0),
    ("where is the nearest station", 0),
    ("how tall is mount everest", 0),
    ("show me the forecast", 0),
    ("who invented the telephone", 0),
    ("turn off the heating", 1),
    ("set a timer for five minutes", 1),
    ("play my favourite playlist", 1),
    ("send an email to john", 1),
    ("lock the front door", 1),
    ("call the restaurant", 1),
    ("turn on the lights now", 1),
    ("remind me at seven pm", 1),
]

test_data = [
    ("search for restaurants nearby", 0),
    ("what is the weather today", 0),
    ("find me a good hotel", 0),
    ("who won the game last night", 0),
    ("turn on the lights", 1),
    ("set an alarm for seven", 1),
    ("play some jazz music", 1),
    ("send a message to mum", 1),
]

train_sents = [s for s, l in train_data]
train_labels = np.array([l for s, l in train_data])
test_sents = [s for s, l in test_data]
test_labels = np.array([l for s, l in test_data])

print(f"  Train: {len(train_sents)} | Test: {len(test_sents)}")
print(f"  Classes: SEARCH (0) vs ACTION (1)")
for s, l in test_data:
    label = "SEARCH" if l == 0 else "ACTION"
    print(f"    [{label}] {s}")

# ================================================================
# PART 3: BUILD IQP CLASSIFIER
# ================================================================
print("\n" + "-" * 70)
print("PART 3: Building IQP Variational Classifier")
print("-" * 70)

N_QUBITS = 4
N_LAYERS = 2
n_params = N_QUBITS * N_LAYERS * 3

params = ParameterVector('theta', n_params)
qc_template = QuantumCircuit(N_QUBITS, 1)

# Hadamard layer
qc_template.h(range(N_QUBITS))

p_idx = 0
for layer in range(N_LAYERS):
    for q in range(N_QUBITS):
        qc_template.rx(params[p_idx], q); p_idx += 1
        qc_template.ry(params[p_idx], q); p_idx += 1
        qc_template.rz(params[p_idx], q); p_idx += 1
    for q in range(N_QUBITS - 1):
        qc_template.cz(q, q + 1)

qc_template.measure(0, 0)

print(f"  IQP classifier: {N_QUBITS} qubits, {N_LAYERS} layers, {n_params} parameters")
print(f"  Circuit depth: {qc_template.depth()}")


def sentence_to_features(sentence, n_features):
    """Hash-based sentence encoding to circuit parameters."""
    words = sentence.lower().split()
    features = np.zeros(n_features)
    for j, w in enumerate(words):
        idx = hash(w) % n_features
        features[idx] += 1.0
    if features.max() > 0:
        features = (features / features.max()) * 2 * np.pi
    return features


def evaluate_circuit_sim(param_values, sentence_features, shots=512):
    """Evaluate circuit on simulator."""
    full_params = param_values.copy()
    n_input = min(len(sentence_features), len(full_params))
    for j in range(n_input):
        full_params[j] += sentence_features[j]

    bound_qc = qc_template.assign_parameters(
        {params[j]: full_params[j] for j in range(n_params)}
    )

    result = sim.run(bound_qc, shots=shots).result()
    counts = result.get_counts()
    p1 = counts.get('1', 0) / shots
    return p1


# ================================================================
# PART 4: TRAIN ON SIMULATOR
# ================================================================
print("\n" + "-" * 70)
print("PART 4: Training on Simulator")
print("-" * 70)


def cost_function(param_values):
    total_loss = 0
    for sent, label in zip(train_sents, train_labels):
        features = sentence_to_features(sent, n_params)
        p1 = evaluate_circuit_sim(param_values, features)
        total_loss += (p1 - label) ** 2
    return total_loss / len(train_sents)


print("  Training with COBYLA optimizer (max 300 iterations)...")
t_start = time.time()

initial_params = np.random.uniform(0, np.pi, n_params)
result = minimize(cost_function, initial_params, method='COBYLA',
                  options={'maxiter': 300, 'disp': False})

trained_params = result.x
train_time = time.time() - t_start
print(f"  Training complete in {train_time:.1f}s | Final cost: {result.fun:.4f}")

# ================================================================
# PART 5: EVALUATE ON SIMULATOR
# ================================================================
print("\n" + "-" * 70)
print("PART 5: Simulator Evaluation")
print("-" * 70)

sim_predictions = []
for sent, label in zip(test_sents, test_labels):
    features = sentence_to_features(sent, n_params)
    p1 = evaluate_circuit_sim(trained_params, features, shots=1024)
    pred = 1 if p1 > 0.5 else 0

    true_str = "SEARCH" if label == 0 else "ACTION"
    pred_str = "SEARCH" if pred == 0 else "ACTION"
    correct = pred == label

    sim_predictions.append({
        "sentence": sent,
        "true_label": int(label),
        "predicted": pred,
        "p_action": round(p1, 4),
        "correct": bool(correct),
    })

    status = "OK" if correct else "WRONG"
    print(f"  [{status}] \"{sent}\" true={true_str} pred={pred_str} p(ACTION)={p1:.3f}")

sim_acc = sum(1 for p in sim_predictions if p['correct']) / len(sim_predictions)
print(f"\n  Simulator accuracy: {sim_acc:.0%} ({sum(1 for p in sim_predictions if p['correct'])}/{len(sim_predictions)})")

# ================================================================
# PART 6: RUN ON REAL QPU
# ================================================================
print("\n" + "-" * 70)
print(f"PART 6: Running on {backend.name} ({backend.num_qubits} qubits)")
print("-" * 70)

pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
sampler = SamplerV2(mode=backend)

qpu_predictions = []
total_qpu_time = 0

for idx, (sent, label) in enumerate(zip(test_sents, test_labels)):
    features = sentence_to_features(sent, n_params)
    full_params = trained_params.copy()
    n_input = min(len(features), len(full_params))
    for j in range(n_input):
        full_params[j] += features[j]

    bound_qc = qc_template.assign_parameters(
        {params[j]: full_params[j] for j in range(n_params)}
    )

    transpiled = pm.run(bound_qc)

    print(f"  [{idx+1}/{len(test_sents)}] \"{sent}\" depth={transpiled.depth()}", end="", flush=True)

    t_start = time.time()
    job = sampler.run([transpiled], shots=512)
    qpu_result = job.result()
    elapsed = time.time() - t_start
    total_qpu_time += elapsed

    counts = qpu_result[0].data.c.get_counts()
    total_shots = sum(counts.values())
    p1 = counts.get('1', 0) / total_shots
    pred = 1 if p1 > 0.5 else 0

    true_str = "SEARCH" if label == 0 else "ACTION"
    pred_str = "SEARCH" if pred == 0 else "ACTION"
    correct = pred == label

    print(f" | {counts} | p(ACTION)={p1:.3f} | {'OK' if correct else 'WRONG'} ({elapsed:.1f}s)")

    qpu_predictions.append({
        "sentence": sent,
        "true_label": int(label),
        "predicted": pred,
        "p_action": round(p1, 4),
        "correct": bool(correct),
        "counts": counts,
        "qpu_time": round(elapsed, 1),
        "transpiled_depth": transpiled.depth(),
    })

qpu_acc = sum(1 for p in qpu_predictions if p['correct']) / len(qpu_predictions)

# ================================================================
# COMPARISON
# ================================================================
print("\n\n" + "=" * 70)
print("SIMULATOR vs QPU COMPARISON")
print("=" * 70)

print(f"\n  {'Sentence':<35} {'True':<8} {'Sim':<8} {'QPU':<8} {'Match'}")
print("  " + "-" * 67)

matches = 0
for sp, qp in zip(sim_predictions, qpu_predictions):
    s_label = "SEARCH" if sp['predicted'] == 0 else "ACTION"
    q_label = "SEARCH" if qp['predicted'] == 0 else "ACTION"
    t_label = "SEARCH" if sp['true_label'] == 0 else "ACTION"
    match = sp['predicted'] == qp['predicted']
    if match:
        matches += 1
    print(f"  {sp['sentence'][:35]:<35} {t_label:<8} {s_label:<8} {q_label:<8} {'YES' if match else 'NO'}")

agreement = matches / len(sim_predictions)

print(f"\n  Simulator accuracy:     {sim_acc:.0%}")
print(f"  QPU accuracy:           {qpu_acc:.0%}")
print(f"  Sim-QPU agreement:      {agreement:.0%}")
print(f"  Total QPU time:         {total_qpu_time:.1f}s")
print(f"  Avg QPU time per sent:  {total_qpu_time/len(test_sents):.1f}s")
print(f"  QPU used:               {backend.name}")

noise_impact = sim_acc - qpu_acc
print(f"\n  Noise impact: {noise_impact*100:+.1f} percentage points")
if abs(noise_impact) <= 0.05:
    print("  EXCELLENT: Hardware noise has minimal impact")
elif abs(noise_impact) <= 0.15:
    print("  GOOD: Some noise degradation but still usable")
elif abs(noise_impact) <= 0.30:
    print("  MODERATE: Significant noise — error mitigation needed")
else:
    print("  HIGH: Hardware noise severely impacts predictions")

# ================================================================
# QPU BUDGET TRACKER
# ================================================================
print("\n" + "=" * 70)
print("QPU BUDGET TRACKER")
print("=" * 70)

# Estimate QPU usage
# Bell state test: ~10s
# Grover test: ~15s
# QKD basis tests: ~60s (4 circuits)
# Reasoning AND gates: ~60s (4 circuits)
# Emotion superposition: ~15s
# This NLU run: total_qpu_time

previous_usage_s = 10 + 15 + 60 + 60 + 15  # Rough estimates
current_usage_s = total_qpu_time
total_usage_s = previous_usage_s + current_usage_s
budget_s = 10 * 60  # 10 minutes

print(f"\n  Previous QPU usage (est): {previous_usage_s:.0f}s ({previous_usage_s/60:.1f} min)")
print(f"  This run:                 {current_usage_s:.0f}s ({current_usage_s/60:.1f} min)")
print(f"  Total estimated:          {total_usage_s:.0f}s ({total_usage_s/60:.1f} min)")
print(f"  Monthly budget:           {budget_s}s ({budget_s/60:.0f} min)")
print(f"  Remaining (est):          {budget_s - total_usage_s:.0f}s ({(budget_s - total_usage_s)/60:.1f} min)")

# ================================================================
# SAVE
# ================================================================
os.makedirs("results", exist_ok=True)

all_results = {
    "task": "Sprint 5.1 - NLU on QPU",
    "backend": backend.name,
    "n_qubits": N_QUBITS,
    "n_layers": N_LAYERS,
    "n_params": n_params,
    "train_sentences": len(train_sents),
    "test_sentences": len(test_sents),
    "simulator_accuracy": round(sim_acc, 4),
    "qpu_accuracy": round(qpu_acc, 4),
    "sim_qpu_agreement": round(agreement, 4),
    "noise_impact": round(noise_impact, 4),
    "total_qpu_time_s": round(total_qpu_time, 1),
    "sim_predictions": sim_predictions,
    "qpu_predictions": [{k: v for k, v in p.items() if k != 'counts'} for p in qpu_predictions],
    "qpu_budget": {
        "previous_usage_s": previous_usage_s,
        "this_run_s": round(current_usage_s, 1),
        "total_estimated_s": round(total_usage_s, 1),
        "monthly_budget_s": budget_s,
        "remaining_s": round(budget_s - total_usage_s, 1),
    },
}

with open("results/sprint5_lambeq_qpu.json", "w") as f:
    json.dump(all_results, f, indent=2)

print(f"\nResults saved to results/sprint5_lambeq_qpu.json")
print(f"\n{'='*70}")
print("TASK 5.1 COMPLETE — NLU on Real Quantum Hardware")
print(f"{'='*70}")
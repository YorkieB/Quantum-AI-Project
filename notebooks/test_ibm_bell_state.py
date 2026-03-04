#!/usr/bin/env python3
"""
First real QPU run: Bell state on IBM Heron processor
======================================================
Sends a 2-qubit entanglement circuit to ibm_marrakesh (156 qubits).
Compares real QPU results vs local simulator.
"""

from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
import time

# Connect
print("Connecting to IBM Quantum...")
service = QiskitRuntimeService(channel="ibm_cloud")
backend = service.least_busy(operational=True, simulator=False)
print(f"Using: {backend.name} ({backend.num_qubits} qubits)")
print(f"Pending jobs: {backend.status().pending_jobs}")

# Build Bell state circuit
qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()

print(f"\nCircuit:")
print(qc.draw())

# Transpile for the real hardware
print(f"\nTranspiling for {backend.name}...")
pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
transpiled = pm.run(qc)
print(f"  Transpiled depth: {transpiled.depth()}")
print(f"  Transpiled gates: {transpiled.count_ops()}")

# Run on real QPU
print(f"\nSubmitting to {backend.name}...")
sampler = SamplerV2(mode=backend)
t_start = time.time()
job = sampler.run([transpiled], shots=1024)

print(f"  Job ID: {job.job_id()}")
print(f"  Waiting for results...")

result = job.result()
elapsed = time.time() - t_start

# Extract counts
counts = result[0].data.meas.get_counts()

print(f"\n{'='*50}")
print(f"REAL QPU RESULTS — {backend.name}")
print(f"{'='*50}")
print(f"  Counts: {counts}")

total = sum(counts.values())
for state, count in sorted(counts.items()):
    pct = count / total * 100
    bar = '#' * int(pct / 2)
    print(f"  |{state}>: {count:>4} ({pct:>5.1f}%) {bar}")

# Expected: ~50% |00> and ~50% |11> for perfect Bell state
# Any |01> or |10> counts indicate hardware noise
correlated = counts.get('00', 0) + counts.get('11', 0)
noise = counts.get('01', 0) + counts.get('10', 0)
fidelity = correlated / total

print(f"\n  Correlated (00+11): {correlated} ({correlated/total:.1%})")
print(f"  Noise (01+10):      {noise} ({noise/total:.1%})")
print(f"  Bell state fidelity: {fidelity:.3f}")
print(f"  Time: {elapsed:.1f}s")

print(f"\n  Perfect simulator would give: 50/50 split, 0 noise")
print(f"  Fidelity > 0.95 = excellent hardware")
print(f"  Fidelity > 0.90 = good hardware")
print(f"  Fidelity < 0.80 = noisy hardware")

# Compare with local simulator
print(f"\n{'='*50}")
print("LOCAL SIMULATOR COMPARISON")
print(f"{'='*50}")

from qiskit_aer import AerSimulator
sim = AerSimulator()
pm_sim = generate_preset_pass_manager(backend=sim, optimization_level=1)
transpiled_sim = pm_sim.run(qc)
sim_sampler = SamplerV2(mode=sim)
sim_result = sim_sampler.run([transpiled_sim], shots=1024).result()
sim_counts = sim_result[0].data.meas.get_counts()

print(f"  Simulator: {sim_counts}")
sim_correlated = sim_counts.get('00', 0) + sim_counts.get('11', 0)
sim_fidelity = sim_correlated / sum(sim_counts.values())
print(f"  Simulator fidelity: {sim_fidelity:.3f}")
print(f"  QPU fidelity:       {fidelity:.3f}")
print(f"  Noise gap:          {sim_fidelity - fidelity:.3f}")

print(f"\nFirst real QPU run complete!")
print(f"You just ran a quantum circuit on a {backend.num_qubits}-qubit Heron processor.")
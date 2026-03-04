#!/usr/bin/env python3
"""Test IBM Quantum connection."""

# Step 1: Install
# pip install qiskit-ibm-runtime

# Step 2: Replace YOUR_TOKEN_HERE with your actual token
TOKEN = "YOUR_TOKEN_HERE"

from qiskit_ibm_runtime import QiskitRuntimeService

# Save account (first time only)
QiskitRuntimeService.save_account(
    channel="ibm_quantum",
    token=TOKEN,
    overwrite=True
)

# Connect
service = QiskitRuntimeService(channel="ibm_quantum")

print("IBM Quantum Connected!")
print("\nAvailable backends:")
for backend in service.backends():
    status = backend.status()
    print(f"  {backend.name}: {backend.num_qubits} qubits | "
          f"operational={status.operational} | "
          f"pending_jobs={status.pending_jobs}")

print("\nLeast busy backend:")
best = service.least_busy(operational=True, simulator=False)
print(f"  {best.name} ({best.num_qubits} qubits)")
print("\nIBM Quantum setup complete!")

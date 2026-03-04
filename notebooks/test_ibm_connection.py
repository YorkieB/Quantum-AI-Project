#!/usr/bin/env python3
"""Quick test: Connect to IBM Quantum and list backends."""

from qiskit_ibm_runtime import QiskitRuntimeService

# Replace with your NEW API key (regenerated)
TOKEN ="fiwu1PAEXy95dGgrJPOqYVhtWZEaXS25oLFlUOmVTFF6"
INSTANCE = "crn:v1:bluemix:public:quantum-computing:us-east:a/385ae41856b047f3b8d3daa50829a071:a4c87d72-b6b7-40ff-8441-9ad2e72667bd::"

# Save credentials (first time only)
QiskitRuntimeService.save_account(
    channel="ibm_cloud",
    token=TOKEN,
    instance=INSTANCE,
    overwrite=True,
)

# Connect
print("Connecting to IBM Quantum...")
service = QiskitRuntimeService(channel="ibm_cloud")

print("\nAvailable backends:")
for backend in service.backends():
    status = backend.status()
    print(f"  {backend.name}: {backend.num_qubits} qubits | "
          f"operational={status.operational} | "
          f"pending_jobs={status.pending_jobs}")

# Find least busy
best = service.least_busy(operational=True, simulator=False)
print(f"\nLeast busy: {best.name} ({best.num_qubits} qubits)")
print("\nIBM Quantum connected! Ready for Sprint 5.")
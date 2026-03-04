#!/usr/bin/env python3
"""
Jarvis Quantum — Backend Router
=================================
Tier-aware quantum device selector.

Tiers:
  local      — Local CPU simulator (PennyLane lightning.qubit + Qiskit AerSimulator)
  cloud-sim  — Cloud GPU simulator (PennyLane lightning.gpu + Qiskit AerSimulator)
  cloud-qpu  — Real IBM quantum hardware (Qiskit IBM Runtime)

Usage:
  from jarvis_backend_router import JarvisBackendRouter
  router = JarvisBackendRouter()
  dev = router.get_pennylane_device(n_wires=4)
  backend = router.get_qiskit_backend()
"""

import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger("jarvis-quantum.router")
logging.basicConfig(level=logging.INFO)

# Load environment from config file if COMPUTE_TIER is not already set
_tier = os.environ.get("COMPUTE_TIER", "local")
_config_file = os.path.join(os.path.dirname(__file__), "config", f"{_tier}.env")
if os.path.exists(_config_file):
    load_dotenv(_config_file, override=False)

COMPUTE_TIER = os.environ.get("COMPUTE_TIER", "local")

TIER_CONFIG = {
    "local":     {"max_qubits": 30,  "pennylane_device": "lightning.qubit"},
    "cloud-sim": {"max_qubits": 30,  "pennylane_device": "lightning.gpu"},
    "cloud-qpu": {"max_qubits": 156, "pennylane_device": "default.qubit"},
}


class JarvisBackendRouter:
    """Selects the appropriate quantum backend based on the compute tier."""

    def __init__(self, tier: str | None = None):
        self.tier = tier or COMPUTE_TIER
        if self.tier not in TIER_CONFIG:
            raise ValueError(
                f"Unknown compute tier '{self.tier}'. "
                f"Choose from: {list(TIER_CONFIG.keys())}"
            )
        self.config = TIER_CONFIG[self.tier]
        logger.info(f"Backend router initialised on tier: {self.tier}")

    @property
    def max_qubits(self) -> int:
        return self.config["max_qubits"]

    def get_pennylane_device(self, n_wires: int):
        """Return a PennyLane device for the current tier."""
        import pennylane as qml

        device_name = self.config["pennylane_device"]
        if self.tier == "cloud-qpu":
            device_name = "default.qubit"

        logger.info(
            f"[{self.tier}] Creating {device_name} device with {n_wires} wires"
        )
        return qml.device(device_name, wires=n_wires)

    def get_qiskit_backend(self):
        """Return a Qiskit backend for the current tier."""
        if self.tier in ("local", "cloud-sim"):
            from qiskit_aer import AerSimulator
            backend = AerSimulator(method="statevector")
            logger.info(f"[{self.tier}] Using Qiskit AerSimulator (statevector)")
            return backend

        # cloud-qpu: connect to IBM Runtime
        from qiskit_ibm_runtime import QiskitRuntimeService

        token = os.environ.get("IBM_QUANTUM_TOKEN")
        if not token or token == "YOUR_IBM_QUANTUM_TOKEN_HERE":
            raise EnvironmentError(
                "IBM_QUANTUM_TOKEN is not set. "
                "Copy config/cloud-qpu.env and add your token."
            )

        channel = os.environ.get("IBM_QUANTUM_CHANNEL", "ibm_quantum")
        instance = os.environ.get("IBM_QUANTUM_INSTANCE", "ibm-q/open/main")
        preferred = os.environ.get("PREFERRED_BACKEND", "ibm_fez")

        service = QiskitRuntimeService(
            channel=channel, token=token, instance=instance
        )
        backend = service.backend(preferred)
        logger.info(f"[cloud-qpu] Connected to IBM QPU: {backend.name}")
        return backend


def _self_test():
    """Run a quick Bell-state test on the local simulator."""
    import pennylane as qml
    import numpy as np

    print("=" * 50)
    print("Jarvis Quantum — Backend Router Self-Test")
    print("=" * 50)

    router = JarvisBackendRouter(tier="local")
    print(f"Compute Tier: {router.tier}")
    print(f"Max Recommended Qubits: {router.max_qubits}")

    # PennyLane test
    print("\n--- PennyLane Device Test ---")
    dev = router.get_pennylane_device(n_wires=4)
    print(f"Device: {dev.name}")

    @qml.qnode(dev)
    def bell_circuit():
        qml.Hadamard(wires=0)
        qml.CNOT(wires=[0, 1])
        return qml.expval(qml.PauliZ(0))

    # Qiskit test
    print("\n--- Qiskit Backend Test ---")
    backend = router.get_qiskit_backend()
    print(f"Backend: {backend}")

    # Bell state expectation value
    print("\n--- Quick Circuit Test ---")
    result = bell_circuit()
    print(f"Bell state <Z₀> expectation: {result:.4f} (expected: ~0.0)")

    if abs(result) < 0.1:
        print(f"✅ Backend router working correctly on tier: {router.tier}")
    else:
        print("⚠️  Unexpected result — check your installation.")


if __name__ == "__main__":
    _self_test()

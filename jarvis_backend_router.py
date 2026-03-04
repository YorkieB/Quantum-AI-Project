"""
Jarvis Quantum — Backend Router
================================
Tier-aware device selection for quantum circuit execution.

Tiers:
  - local:     PennyLane lightning.qubit (CPU, up to ~30 qubits)
  - cloud-gpu: PennyLane lightning.gpu on AWS (GPU-accelerated)
  - cloud-qpu: Real quantum hardware via Amazon Braket

Switch tiers by setting JARVIS_COMPUTE_TIER in environment config.
No code changes required — only the env file changes.

Usage:
    from jarvis_backend_router import get_quantum_device, get_qiskit_backend
    
    # PennyLane device
    dev = get_quantum_device(n_wires=4)
    
    # Qiskit backend
    backend = get_qiskit_backend()
"""

import os
import logging

logger = logging.getLogger("jarvis-quantum.router")


def get_compute_tier() -> str:
    """Get the current compute tier from environment."""
    tier = os.environ.get("JARVIS_COMPUTE_TIER", "local")
    if tier not in ("local", "cloud-gpu", "cloud-qpu"):
        raise ValueError(
            f"Unknown compute tier: '{tier}'. "
            f"Valid options: local, cloud-gpu, cloud-qpu"
        )
    return tier


def get_quantum_device(n_wires: int, shots: int | None = None):
    """
    Get a PennyLane quantum device for the current compute tier.
    
    Args:
        n_wires: Number of qubits the circuit requires.
        shots: Number of measurement shots. None = analytic (exact).
    
    Returns:
        A PennyLane device configured for the current tier.
    """
    import pennylane as qml
    
    tier = get_compute_tier()
    
    if tier == "local":
        # Tier 1: CPU simulator — handles up to ~30 qubits efficiently
        logger.info(f"[Local CPU] Creating lightning.qubit device with {n_wires} wires")
        return qml.device("lightning.qubit", wires=n_wires, shots=shots)
    
    elif tier == "cloud-gpu":
        # Tier 2: Cloud GPU simulator via PennyLane lightning.gpu
        logger.info(f"[Cloud GPU] Creating lightning.gpu device with {n_wires} wires")
        return qml.device("lightning.gpu", wires=n_wires, shots=shots)
    
    elif tier == "cloud-qpu":
        # Tier 3: Real quantum hardware via Amazon Braket
        device_arn = os.environ.get("QPU_DEVICE_ARN")
        s3_bucket = os.environ.get("BRAKET_S3_BUCKET", "jarvis-quantum-results")
        
        if not device_arn:
            raise EnvironmentError(
                "QPU_DEVICE_ARN must be set for cloud-qpu tier. "
                "Example: arn:aws:braket:us-east-1::device/qpu/ionq/Harmony"
            )
        
        qpu_shots = shots if shots is not None else 1000
        logger.info(
            f"[Cloud QPU] Creating Braket device: {device_arn} "
            f"with {n_wires} wires, {qpu_shots} shots"
        )
        return qml.device(
            "braket.aws.qubit",
            device_arn=device_arn,
            wires=n_wires,
            s3_destination_folder=(s3_bucket,),
            shots=qpu_shots,
        )

    raise ValueError(f"Unknown compute tier: {tier}")


def get_qiskit_backend(n_qubits: int | None = None):
    """
    Get a Qiskit backend for the current compute tier.
    
    Args:
        n_qubits: Optional qubit count for validation.
    
    Returns:
        A Qiskit backend (Aer simulator or cloud service).
    """
    from qiskit_aer import AerSimulator
    
    tier = get_compute_tier()
    
    if tier == "local":
        # Tier 1: Local Aer statevector simulator
        logger.info("[Local CPU] Using Qiskit AerSimulator (statevector)")
        return AerSimulator(method="statevector")
    
    elif tier == "cloud-gpu":
        # Tier 2: Aer with GPU acceleration
        logger.info("[Cloud GPU] Using Qiskit AerSimulator (statevector_gpu)")
        return AerSimulator(method="statevector_gpu")
    
    elif tier == "cloud-qpu":
        # Tier 3: IBM Quantum or Braket via Qiskit provider
        # Requires: pip install qiskit-ibm-runtime  OR  qiskit-braket-provider
        ibm_token = os.environ.get("IBM_QUANTUM_TOKEN")
        if ibm_token:
            try:
                from qiskit_ibm_runtime import QiskitRuntimeService
                service = QiskitRuntimeService(channel="ibm_quantum", token=ibm_token)
                backend = service.least_busy(
                    min_num_qubits=n_qubits or 5,
                    simulator=False,
                )
                logger.info(f"[Cloud QPU] Using IBM Quantum backend: {backend.name}")
                return backend
            except ImportError:
                raise ImportError(
                    "Install qiskit-ibm-runtime for IBM Quantum access: "
                    "pip install qiskit-ibm-runtime"
                )
        
        # Fallback: Amazon Braket Qiskit provider
        try:
            from qiskit_braket_provider import BraketProvider
            provider = BraketProvider()
            device_arn = os.environ.get("QPU_DEVICE_ARN")
            if device_arn:
                backend = provider.get_backend(device_arn)
                logger.info(f"[Cloud QPU] Using Braket backend: {device_arn}")
                return backend
            raise EnvironmentError("Set IBM_QUANTUM_TOKEN or QPU_DEVICE_ARN for QPU access")
        except ImportError:
            raise ImportError(
                "Install a QPU provider: "
                "pip install qiskit-ibm-runtime  OR  pip install qiskit-braket-provider"
            )
    
    raise ValueError(f"Unknown compute tier: {tier}")


def get_tier_info() -> dict:
    """Return information about the current compute configuration."""
    tier = get_compute_tier()
    
    info = {
        "tier": tier,
        "tier_name": {
            "local": "Local CPU Simulator",
            "cloud-gpu": "Cloud GPU Simulator",
            "cloud-qpu": "Quantum Processing Unit",
        }[tier],
        "max_qubits_recommended": {
            "local": 30,
            "cloud-gpu": 32,
            "cloud-qpu": 127,  # IBM Eagle+
        }[tier],
    }
    
    if tier == "cloud-qpu":
        info["qpu_device"] = os.environ.get("QPU_DEVICE_ARN", "not set")
        info["ibm_token_set"] = bool(os.environ.get("IBM_QUANTUM_TOKEN"))
    
    return info


# Quick self-test when run directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 50)
    print("Jarvis Quantum — Backend Router Self-Test")
    print("=" * 50)
    
    info = get_tier_info()
    print(f"\nCompute Tier: {info['tier_name']} ({info['tier']})")
    print(f"Max Recommended Qubits: {info['max_qubits_recommended']}")
    
    # Test PennyLane device
    print("\n--- PennyLane Device Test ---")
    dev = get_quantum_device(n_wires=4)
    print(f"Device: {dev.name}")
    print(f"Wires: {len(dev.wires)}")
    
    # Test Qiskit backend
    print("\n--- Qiskit Backend Test ---")
    backend = get_qiskit_backend()
    print(f"Backend: {backend}")
    
    # Quick circuit test
    print("\n--- Quick Circuit Test ---")
    import pennylane as qml
    import numpy as np
    
    @qml.qnode(dev)
    def test_circuit():
        qml.Hadamard(wires=0)
        qml.CNOT(wires=[0, 1])
        return qml.expval(qml.PauliZ(0))
    
    result = test_circuit()
    print(f"Bell state <Z₀> expectation: {result:.4f} (expected: ~0.0)")
    print(f"\n✅ Backend router working correctly on tier: {info['tier']}")

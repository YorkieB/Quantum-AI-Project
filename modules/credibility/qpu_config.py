#!/usr/bin/env python3
"""
Shared QPU configuration for all Jarvis quantum modules.
Import this in any service to get QPU access.
"""

import os
from qiskit_aer import AerSimulator

_qpu_service = None
_qpu_backend = None
_sim = AerSimulator()


def get_simulator():
    return _sim


def get_qpu_service():
    global _qpu_service
    if _qpu_service is None:
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
            _qpu_service = QiskitRuntimeService(channel="ibm_cloud")
            print("  QPU: IBM Quantum connected")
        except Exception as e:
            print(f"  QPU: Connection failed ({e})")
            _qpu_service = None
    return _qpu_service


def get_qpu_backend(preferred=None):
    global _qpu_backend
    service = get_qpu_service()
    if service is None:
        return None

    if _qpu_backend is None or (preferred and _qpu_backend.name != preferred):
        try:
            if preferred:
                _qpu_backend = service.backend(preferred)
            else:
                _qpu_backend = service.least_busy(operational=True, simulator=False)
            print(f"  QPU backend: {_qpu_backend.name} ({_qpu_backend.num_qubits} qubits)")
        except Exception as e:
            print(f"  QPU backend failed: {e}")
            return None
    return _qpu_backend


def get_usage():
    """Rough QPU usage tracking."""
    tracker_path = os.path.join(os.path.dirname(__file__), '..', 'qpu_usage.json')
    try:
        import json
        with open(tracker_path) as f:
            return json.load(f)
    except Exception:
        return {"total_jobs": 0, "total_shots": 0}


def log_usage(shots, circuit_name="unknown"):
    """Log QPU usage."""
    tracker_path = os.path.join(os.path.dirname(__file__), '..', 'qpu_usage.json')
    import json
    try:
        with open(tracker_path) as f:
            data = json.load(f)
    except Exception:
        data = {"total_jobs": 0, "total_shots": 0, "history": []}

    data["total_jobs"] += 1
    data["total_shots"] += shots
    data["history"].append({
        "circuit": circuit_name,
        "shots": shots,
    })

    with open(tracker_path, "w") as f:
        json.dump(data, f, indent=2)
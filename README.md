# Jarvis Quantum

Quantum-enhanced modules for the Jarvis AI ecosystem. Six quantum subsystems running on PennyLane, Qiskit, and lambeq — starting on local CPU simulators, scaling to cloud GPU, and eventually deploying on real quantum hardware.

## Modules

| Module | Framework | Purpose | Port |
|--------|-----------|---------|------|
| NLU Engine | lambeq + PennyLane | Intent classification via DisCoCat quantum circuits | 8001 |
| Reasoning Core | PennyLane QAOA | Task scheduling and combinatorial optimisation | 8002 |
| Knowledge Retrieval | Qiskit Grover's | O(√N) document search | 8003 |
| Credibility Verifier | Qiskit VQC | Fake news / source credibility classification | 8004 |
| Voice Processor | PennyLane + PyTorch | Hybrid quantum-classical speech features | 8005 |
| Secure Comms | QKD | Quantum key distribution for secure transport | 8006 |

## Compute Tiers

All modules use the backend router (`jarvis_backend_router.py`) which selects the quantum device based on `JARVIS_COMPUTE_TIER`:

- **local** — CPU simulators (PennyLane lightning.qubit, Qiskit Aer). Up to ~30 qubits.
- **cloud-gpu** — GPU-accelerated simulators on AWS. Up to ~32 qubits.
- **cloud-qpu** — Real quantum hardware (IBM Quantum, Amazon Braket).

Switch tiers by changing the env file — no code changes needed.

## Quick Start

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate.ps1  # Windows

# Install dependencies
pip install -r requirements.txt

# Test the backend router
python jarvis_backend_router.py

# Run a notebook
jupyter notebook notebooks/
```

## Project Structure

```
jarvis-quantum/
├── Dockerfile.base              # Base image with all frameworks
├── docker-compose.yml           # Orchestrates all modules
├── jarvis_backend_router.py     # Tier-aware device selection
├── requirements.txt             # Python dependencies
├── config/
│   ├── local.env                # Tier 1: CPU simulator
│   ├── cloud-sim.env            # Tier 2: Cloud GPU
│   └── cloud-qpu.env            # Tier 3: Real QPU
├── modules/
│   ├── nlu/                     # Module 1: lambeq NLU
│   ├── reasoning/               # Module 2: QAOA
│   ├── retrieval/               # Module 3: Grover's
│   ├── credibility/             # Module 4: VQC
│   ├── voice/                   # Module 5: Hybrid QNN
│   └── secure_comms/            # Module 6: QKD
├── notebooks/                   # Jupyter tutorials and experiments
├── tests/                       # Test suite
└── docs/                        # Architecture and benchmarks
```

## Roadmap

- **Phase 1** (Mar–Apr 2026): Environment setup, classical baselines, data pipelines
- **Phase 2** (Apr–Jul 2026): Quantum module prototyping on simulators
- **Phase 3** (Jul–Oct 2026): Integration, testing, noise resilience
- **Phase 4** (Oct 2026–Jan 2027): Cloud migration, real QPU deployment
- **Phase 5** (Jan–Apr 2027): Advanced features, quantum internet prep

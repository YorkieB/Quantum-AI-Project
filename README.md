# Jarvis Quantum

## Overview
Jarvis Quantum is an extension to the Jarvis AI system, integrating quantum computing capabilities using frameworks like Qiskit, PennyLane, and lambeq. This project provides quantum-enhanced modules for tasks such as natural language understanding (NLU), reasoning, knowledge retrieval, credibility verification, emotion processing, and secure communications via Quantum Key Distribution (QKD).

The system is structured as microservices accessible through a unified gateway, with support for local simulators, cloud GPUs, and real quantum hardware (e.g., IBM Heron processors).

## Key Features
- **Quantum Modules**:
  - **NLU (Module 1)**: Uses lambeq's DisCoCat for quantum natural language processing.
  - **Reasoning (Module 2)**: Quantum logic and inference with QAOA.
  - **Search (Module 3)**: Grover's algorithm for O(sqrt(N)) database search.
  - **Credibility (Module 4)**: Variational Quantum Classifier (VQC) for fake news detection.
  - **Emotion (Module 5)**: Superposition-based processing for TTS vectors.
  - **QKD (Module 6)**: BB84 protocol for quantum-secure encryption.

- **Architecture**:
  - Unified gateway at port 3030 routing to 5 microservices (ports 3031–3035).
  - Tiered compute: Local CPU simulator, cloud GPU, IBM QPU.
  - QPU-enabled for select modules (toggle via `use_qpu` in API requests).

- **Achievements** (from Sprints 4-5):
  - Connected to 3 IBM Heron QPUs (133–156 qubits).
  - Bell state fidelity: 0.974.
  - Grover's success: 72.9% on QPU.
  - QKD BB84: 96.8–100% fidelity.
  - Error mitigation: Improved Bell from 94.1% to 99.3%.
  - Noise analysis shows depth-fidelity correlation r = -0.833.

## Project Structure
```
jarvis-quantum/
├── config/
│   ├── cloud-qpu.env
│   ├── cloud-sim.env
│   └── local.env
├── modules/
│   ├── credibility/     # Port 3031: Fake news detection
│   ├── emotion/         # Port 3035: TTS vectors
│   ├── gateway/         # Port 3030: Unified routing
│   ├── qkd/             # Port 3032: Quantum encryption
│   ├── reasoning/       # Port 3034: Logic & inference
│   └── search/          # Port 3033: Grover's search
├── notebooks/           # Experiments and tutorials
├── results/             # JSON outputs from runs
├── tests/               # Unit tests
├── data/                # Datasets
├── models/              # Trained models
├── docs/                # Additional documentation
├── .gitignore
├── Dockerfile.base
├── docker-compose.yml
├── jarvis_backend_router.py
├── README.md            # This file
├── requirements.txt
└── venv/                # Virtual environment
```

## Setup Instructions
1. **Clone the Repo**:
   ```
   git clone https://github.com/yorkie9733/jarvis-quantum.git
   cd jarvis-quantum
   ```

2. **Install Dependencies** (Python 3.11+):
   ```
   python -m venv venv
   source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   - Copy `config/local.env` and set IBM Quantum API keys for QPU access.

4. **Run Services**:
   - Start each microservice in separate terminals:
     ```
     cd modules/gateway && python service.py
     cd modules/credibility && python service.py
     # Repeat for qkd, search, reasoning, emotion
     ```
   - Access via gateway: `http://localhost:3030/docs`

5. **Run Notebooks**:
   - Use Jupyter: `jupyter notebook notebooks/`
   - Key notebooks: sprint4_hybrid_credibility.ipynb, sprint5_noise_analysis.ipynb, etc.

## Quantum Hardware Integration
- Free IBM Quantum tier: 10 minutes/month.
- Usage tracked: ~36 seconds for validation runs.
- Toggle QPU in API requests for real hardware execution.

## Next Steps
- Integrate with main Jarvis orchestrator (proxy `/api/quantum` to port 3030).
- Enable QPU for all modules.
- Production hardening: Docker deployment, monitoring.
- Monitor Quantinuum BobcatParser for advanced NLU.

## License
MIT License. See LICENSE file for details.

## Contact
- Author: Yorkie Brown (@yorkie9733 on X)
- Date: March 2026


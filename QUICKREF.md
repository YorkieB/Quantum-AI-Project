# Jarvis Quantum — Quick Reference

## One-Command Setup (Pick One)

### Linux/macOS
```bash
bash bootstrap.sh
```

### Windows / All Platforms
```bash
python bootstrap.py
```

---

## Project Status

| Component | Status | Details |
|-----------|--------|---------|
| **Frameworks** | ✅ Ready | Qiskit 2.3, PennyLane 0.44, lambeq 0.5, PyTorch 2.10 |
| **Datasets** | ✅ Ready | LIAR (politics), CLINC150 (intent), jarvis_v1 (synthetic) |
| **Models** | ✅ Trained | Classical + Quantum credibility (train_all.py seeds them) |
| **Backend Router** | ✅ Working | local → cloud-gpu → cloud-qpu (env var switches) |
| **Microservices** | ✅ Runnable | 6 FastAPI services + gateway router (ports 3030-3035) |
| **Benchmarks** | ✅ Complete | Sprints 1–3 results in `results/` |

---

## Six Quantum Modules

```
┌─────────────────────────────┐
│ Gateway (3030) - Router     │
├────┬────┬────┬────┬────┬────┤
│ M1 │ M2 │ M3 │ M4 │ M5 │ M6 │
├────┼────┼────┼────┼────┼────┤
│NLU │Rea │Sea │Cre │Emo │QKD │
│301│302│303│304│305│306│
│    │    │    │    │    │    │
│ disc│QAOA│Gro│VQC │QNN │BB84│
└────┴────┴────┴────┴────┴────┘
```

| # | Module | Port | Framework | Algorithm | Status |
|---|--------|------|-----------|-----------|--------|
| 1 | NLU | 3031 | lambeq | DisCoCat | Pre-trained |
| 2 | Reasoning | 3032 | PennyLane | QAOA | Ready |
| 3 | Search | 3033 | Qiskit | Grover's | Ready |
| 4 | Credibility | 3034 | Hybrid | VQC+Classical | Pre-trained |
| 5 | Emotion | 3035 | PennyLane | QNN | Ready |
| 6 | QKD | 3036 | Qiskit | BB84 | Ready |

---

## Startup Sequence

### 1. Terminal 1: Start Gateway
```bash
python modules/gateway/service.py
# Listens on http://localhost:3030
```

### 2. Terminal 2+: Start Services
```bash
# Credibility (requires models/classical_credibility.pkl + quantum_credibility.pt)
cd modules/credibility && python service.py

# Search
cd modules/Search && python service.py

# Reasoning
cd modules/reasoning && python service.py

# QKD
cd modules/qkd && python service.py

# Emotion
cd modules/emotion && python service.py
```

### 3. Test
```bash
# Check all modules are online
curl http://localhost:3030/api/quantum/status

# Try credibility verification
curl -X POST http://localhost:3030/api/credibility/verify \
  -H "Content-Type: application/json" \
  -d '{"claim": "The Earth is a sphere"}'
```

---

## API Endpoints (via Gateway 3030)

### Credibility Verifier
```
POST /api/credibility/verify
  Input: { "claim": str, "source"?: str }
  Output: { "credibility_score": 0-1, "label": "CREDIBLE"|"NOT_CREDIBLE", ... }

POST /api/credibility/batch
  Input: { "claims": [str, ...] }
  Output: { "results": [...] }

GET /api/credibility/config
GET /api/credibility/health
```

### Quantum Search
```
POST /api/search/add_entry
  Input: { "topic": str, "content": str }

POST /api/search/search
  Input: { "query": str, "top_k": int }
  Output: { "results": [{topic, score, content}, ...] }

GET /api/search/list
GET /api/search/clear
```

### QKD (Secure Comms)
```
POST /api/qkd/generate_key
  Input: { "n_bits": int }
  Output: { "key": [0,1,...], "sift_rate": float }

POST /api/qkd/encrypt
  Input: { "message": str, "key": [0,1,...] }
  Output: { "ciphertext": bytes }

POST /api/qkd/decrypt
  Input: { "ciphertext": bytes, "key": [0,1,...] }
  Output: { "plaintext": str }
```

### Reasoning
```
POST /api/reasoning/entailment
  Input: { "premise": str, "hypothesis": str }
  Output: { "label": "ENTAILMENT"|"CONTRADICTION"|"NEUTRAL", "confidence": 0-1 }

POST /api/reasoning/infer
  Input: { "facts": {}, "rules": [], "query": str }
  Output: { "result": bool, "chain": [...], "confidence": 0-1 }

POST /api/reasoning/consistency
  Input: { "claims": [str, ...] }
  Output: { "consistent": bool, "conflicts": [...] }
```

### Emotion Detection
```
POST /api/emotion/detect
  Input: { "text": str }
  Output: { "emotions": {joy, trust, fear, ...}, "dominant": str }

POST /api/emotion/blend
  Input: { "emotions_weights": {joy: 0.5, ...} }
  Output: { "blended": float }
```

### System Health
```
GET /api/quantum/status
  Output: { "modules_online": "5/6", "modules": {...} }

GET /api/quantum/info
  Output: { "modules": {...}, "ports": {...}, "docs_urls": {...} }
```

---

## Key Files

### Entry Points
| File | Purpose |
|------|---------|
| `bootstrap.py` | One-command setup |
| `jarvis_backend_router.py` | Device selector + self-test |
| `modules/{M}/service.py` | Start FastAPI service |
| `modules/gateway/service.py` | Start unified gateway |

### Data
| File | Purpose |
|------|---------|
| `data/liar_train.tsv` | Political statements (credibility) |
| `data/clinc150_full.json` | Intent classification |
| `data/jarvis_intents_v1.json` | Synthetic NLU data |

### Trained Models
| File | Purpose |
|------|---------|
| `modules/credibility/models/classical_credibility.pkl` | TF-IDF + LogReg |
| `modules/credibility/models/quantum_credibility.pt` | DisCoCat + QNN |

### Results (Benchmarks)
| File | Source |
|------|--------|
| `results/sprint3_liar.json` | Credibility benchmark |
| `results/sprint3_clinc150.json` | Intent benchmark |
| `results/sprint4_hybrid_credibility.json` | Hybrid results |

---

## Compute Tiers (No Code Changes — Just Env Vars)

### Tier 1: Local CPU (Default)
```bash
export JARVIS_COMPUTE_TIER=local
python any_module/service.py
# Uses: PennyLane lightning.qubit + Qiskit AerSimulator
# Max: ~30 qubits
# Speed: Fast for development
```

### Tier 2: Cloud GPU
```bash
export JARVIS_COMPUTE_TIER=cloud-gpu
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export BRAKET_S3_BUCKET=jarvis-quantum-results

python any_module/service.py
# Uses: PennyLane lightning.gpu on AWS
# Max: ~32 qubits
# Speed: Faster for large circuits
```

### Tier 3: Real Quantum Hardware
```bash
export JARVIS_COMPUTE_TIER=cloud-qpu

# Option A: IBM Quantum
export IBM_QUANTUM_TOKEN=...

# Option B: Amazon Braket (IonQ/Rigetti)
export QPU_DEVICE_ARN=arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1

python any_module/service.py
# Uses: Real IBM Eagle (127q) or IonQ Aria (25q)
# Max: Depends on hardware
# Speed: Slow + expensive (10min/month IBM, $0.03/task IonQ)
```

---

## Key Benchmarks

### LIAR Credibility (Real Political Statements)
| Method | Train Data | Test Accuracy |
|--------|-----------|---------------|
| Classical (TF-IDF + SVM) | 4,500+ | **66%** |
| **Quantum (DisCoCat)** | **80** | **62%** |
| **Gap → Data Efficiency** | — | **56× less data** |

**Insight:** Quantum achieves competitive results with dramatically less training data. 
On harder problems, the gap shrinks.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ImportError: No module named 'qiskit'` | `pip install -r requirements.txt` |
| `Models not found` | `cd modules/credibility && python train_all.py` |
| `Connection refused on 3030` | Make sure gateway is running: `python modules/gateway/service.py` |
| `Port already in use` | `lsof -i :3030` then `kill -9 <PID>` (or use different port) |
| `LIAR dataset missing` | `python notebooks/sprint3_task2_liar.py` |

---

## Documentation

- **Full Setup:** [STARTUP.md](STARTUP.md)
- **Sprint Results:** [docs/sprint_1_3_summary.md](docs/sprint_1_3_summary.md)
- **QPU Setup:** [docs/qpu_setup_guide.md](docs/qpu_setup_guide.md)
- **README:** [README.md](README.md)

---

## Quick Commands

```bash
# Setup
python bootstrap.py

# Test backend
python jarvis_backend_router.py

# Start gateway
python modules/gateway/service.py

# Train models
cd modules/credibility && python train_all.py

# Test credibility
curl -X POST http://localhost:3030/api/credibility/verify \
  -H "Content-Type: application/json" \
  -d '{"claim": "test claim"}'

# Check status
curl http://localhost:3030/api/quantum/status

# View service docs
# http://localhost:3031/docs  (Credibility Swagger)
# http://localhost:3033/docs  (Search Swagger)
```

---

## Architecture Overview

```
Developer Machine
├── Virtual Environment (Python 3.11)
│   ├── Qiskit 2.3.0
│   ├── PennyLane 0.44.0
│   ├── lambeq 0.5.0
│   ├── PyTorch 2.10.0
│   └── FastAPI
│
├── Jarvis Backend Router (Tier Selector)
│   ├── Local: PennyLane lightning.qubit (CPU)
│   ├── Cloud GPU: PennyLane lightning.gpu (AWS)
│   └── Cloud QPU: IBM Quantum / IonQ (Real Hardware)
│
├── Six Quantum Microservices
│   ├── Gateway (3030) → Proxy to all modules
│   ├── Credibility (3031) → Hybrid VQC
│   ├── QKD (3032) → BB84 Protocol
│   ├── Search (3033) → Grover's Algorithm
│   ├── Reasoning (3034) → QAOA
│   └── Emotion (3035) → Quantum QNN
│
└── Data & Benchmarks
    ├── LIAR dataset (political statements)
    ├── CLINC150 (intent classification)
    └── results/ (benchmark outputs)
```

---

## What's Next (Sprint 4 Roadmap)

- [ ] Hybrid NLU (spaCy entity extraction + quantum intent)
- [ ] Full-length sentence parsing (currently 10-word truncation)
- [ ] IBM Quantum Eagle integration
- [ ] Error mitigation strategies
- [ ] Production deployment on cloud

See [docs/sprint_1_3_summary.md](docs/sprint_1_3_summary.md) for full roadmap.


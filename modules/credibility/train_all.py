#!/usr/bin/env python3
"""
Module 4: Train All Models
============================
Run this once to train and save both classical and quantum models.
After this, the service can start and serve predictions.

Usage:
  cd C:/Users/conta/jarvis-quantum/modules/credibility
  python train_all.py
"""

import os
import sys
import time

print("=" * 60)
print("JARVIS MODULE 4 — CREDIBILITY VERIFIER")
print("Training all models...")
print("=" * 60)

# Check data exists
data_dir = "../../data"
required = ["liar_train.tsv", "liar_val.tsv", "liar_test.tsv"]
for f in required:
    path = os.path.join(data_dir, f)
    if not os.path.exists(path):
        print(f"ERROR: Missing {path}")
        print("Run sprint3_task2_liar.py first to download the LIAR dataset.")
        sys.exit(1)

t_start = time.time()

# Train classical
print("\n" + "-" * 60)
print("STEP 1: Classical Model (TF-IDF + LogReg)")
print("-" * 60)
from classical_model import train_and_save as train_classical
train_classical()

# Train quantum
print("\n" + "-" * 60)
print("STEP 2: Quantum Model (DisCoCat + PytorchQuantumModel)")
print("-" * 60)
from quantum_model import train_and_save as train_quantum
train_quantum(max_words=10, max_train=80, epochs=100)

elapsed = time.time() - t_start

# Verify
print("\n" + "-" * 60)
print("STEP 3: Verify Models")
print("-" * 60)

from classical_model import ClassicalCredibilityModel
classical = ClassicalCredibilityModel()
test = classical.predict("The economy grew by 2.3 percent last year.")
print(f"  Classical test: {test['label']} ({test['confidence']:.3f})")

print(f"\n  Total training time: {elapsed:.0f}s")

print("\n" + "=" * 60)
print("ALL MODELS TRAINED AND SAVED")
print("=" * 60)
print(f"""
Files created:
  models/tfidf_vectorizer.pkl     — TF-IDF feature extractor
  models/classical_clf.pkl        — Logistic regression classifier
  models/quantum_model_weights.pt — Quantum circuit weights
  models/quantum_config.pkl       — Quantum ansatz configuration

To start the service:
  python service.py

To test:
  curl -X POST http://localhost:3031/api/credibility/verify \\
    -H "Content-Type: application/json" \\
    -d '{{"claim": "The unemployment rate dropped 3 percent"}}'
""")
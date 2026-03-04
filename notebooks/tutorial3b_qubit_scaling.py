#!/usr/bin/env python3
"""
Tutorial 3b: Qubit Scaling Test
================================
Jarvis Quantum - Sprint 1 Extension

Tests DisCoCat NLU at increasing qubit counts.
NOUN qubits scale up (richer word representations).
SENTENCE stays at 1 (binary classification output = 2D).
"""

import warnings
warnings.filterwarnings('ignore')

import lambeq
from lambeq import (
    RemoveCupsRewriter,
    IQPAnsatz,
    AtomicType,
    PytorchTrainer,
    PytorchQuantumModel,
    Dataset,
    stairs_reader,
)
import torch
import numpy as np
import json
import os
import time

print(f"lambeq version: {lambeq.__version__}")

# === DATA ===
train_sentences = [
    "search the web for recipes",
    "find information about dogs",
    "look up the weather today",
    "search for nearby restaurants",
    "find a good book to read",
    "look up train times online",
    "search for science news today",
    "find the best coffee shops",
    "set an alarm for tomorrow",
    "turn off the bedroom lights",
    "play my favourite playlist now",
    "send a message to John",
    "turn up the volume please",
    "set a timer for five minutes",
    "lock the front door now",
    "play the latest podcast episode",
]
train_labels = [0,0,0,0,0,0,0,0, 1,1,1,1,1,1,1,1]

test_sentences = [
    "find reviews for new phones",
    "search for holiday deals online",
    "look up football scores today",
    "turn on the kitchen lights",
    "set a reminder for the meeting",
    "play some relaxing music now",
]
test_labels = [0,0,0, 1,1,1]

# === PARSE (once - reuse across configs) ===
print("Parsing sentences...")
reader = stairs_reader
raw_train_diagrams = reader.sentences2diagrams(train_sentences)
raw_test_diagrams = reader.sentences2diagrams(test_sentences)

train_pairs = [(d, l) for d, l in zip(raw_train_diagrams, train_labels) if d is not None]
test_pairs = [(d, l) for d, l in zip(raw_test_diagrams, test_labels) if d is not None]
raw_train_diagrams = [p[0] for p in train_pairs]
train_labels_clean = [p[1] for p in train_pairs]
raw_test_diagrams = [p[0] for p in test_pairs]
test_labels_clean = [p[1] for p in test_pairs]

remove_cups = RemoveCupsRewriter()
train_diagrams = [remove_cups(d) for d in raw_train_diagrams]
test_diagrams = [remove_cups(d) for d in raw_test_diagrams]

train_labels_2d = np.array([[1-l, l] for l in train_labels_clean], dtype=np.float64)
test_labels_2d = np.array([[1-l, l] for l in test_labels_clean], dtype=np.float64)

print(f"  Ready: {len(train_diagrams)} train, {len(test_diagrams)} test\n")

# === SCALING CONFIGS ===
# SENTENCE=1 throughout (keeps output 2D for binary classification)
# NOUN scales up (richer word representations = more qubits per word)
configs = [
    {"name": "A", "noun": 1, "sentence": 1, "layers": 2, "desc": "~5-6 qubits"},
    {"name": "B", "noun": 2, "sentence": 1, "layers": 2, "desc": "~10-11 qubits"},
    {"name": "C", "noun": 3, "sentence": 1, "layers": 2, "desc": "~15-16 qubits"},
    {"name": "D", "noun": 4, "sentence": 1, "layers": 3, "desc": "~20-21 qubits"},
    {"name": "E", "noun": 6, "sentence": 1, "layers": 3, "desc": "~30+ qubits"},
]

def loss_fn(y_pred, y_true):
    return torch.nn.functional.mse_loss(y_pred, y_true.to(y_pred.dtype))

def accuracy_fn(y_pred, y_true):
    return (torch.argmax(y_pred, dim=1) == torch.argmax(y_true.to(y_pred.dtype), dim=1)).sum().item() / len(y_true)

results_all = []

for cfg in configs:
    print("=" * 60)
    print(f"CONFIG {cfg['name']}: NOUN={cfg['noun']}, SENTENCE={cfg['sentence']}, "
          f"layers={cfg['layers']} ({cfg['desc']})")
    print("=" * 60)

    ansatz = IQPAnsatz(
        {AtomicType.NOUN: cfg['noun'], AtomicType.SENTENCE: cfg['sentence']},
        n_layers=cfg['layers'],
        n_single_qubit_params=3,
    )

    t_start = time.time()

    train_circuits = [ansatz(d) for d in train_diagrams]
    test_circuits = [ansatz(d) for d in test_diagrams]

    all_circuits = train_circuits + test_circuits
    model = PytorchQuantumModel.from_diagrams(all_circuits)
    model.initialise_weights()

    n_params = len(model.symbols)
    print(f"  Parameters: {n_params}")

    train_dataset = Dataset(train_circuits, train_labels_2d, batch_size=4)
    test_dataset = Dataset(test_circuits, test_labels_2d, batch_size=4)

    trainer = PytorchTrainer(
        model=model,
        loss_function=loss_fn,
        optimizer=torch.optim.Adam,
        learning_rate=0.1,
        epochs=50,
        evaluate_functions={"accuracy": accuracy_fn},
        evaluate_on_train=True,
        verbose='text',
        seed=42,
    )

    trainer.fit(train_dataset, test_dataset)

    # Evaluate
    train_preds = model(train_circuits)
    test_preds = model(test_circuits)

    train_pred_classes = torch.argmax(train_preds, dim=1)
    test_pred_classes = torch.argmax(test_preds, dim=1)
    train_true_classes = torch.tensor(np.argmax(train_labels_2d, axis=1))
    test_true_classes = torch.tensor(np.argmax(test_labels_2d, axis=1))

    train_acc = (train_pred_classes == train_true_classes).float().mean().item()
    test_acc = (test_pred_classes == test_true_classes).float().mean().item()

    # Measure average confidence (how far from 0.5)
    test_confidence = test_preds.detach().max(dim=1).values.mean().item()

    elapsed = time.time() - t_start

    result = {
        "config": cfg['name'],
        "noun_qubits": cfg['noun'],
        "sentence_qubits": cfg['sentence'],
        "layers": cfg['layers'],
        "n_params": n_params,
        "train_acc": train_acc,
        "test_acc": test_acc,
        "avg_confidence": round(test_confidence, 4),
        "time_seconds": round(elapsed, 1),
    }
    results_all.append(result)

    print(f"\n  Train: {train_acc:.1%} | Test: {test_acc:.1%} | "
          f"Confidence: {test_confidence:.3f} | Params: {n_params} | Time: {elapsed:.1f}s\n")

# === SUMMARY ===
print("\n" + "=" * 70)
print("QUBIT SCALING SUMMARY")
print("=" * 70)
print(f"{'Config':<8} {'Qubits':<14} {'Params':<10} {'Train':<8} {'Test':<8} {'Conf':<8} {'Time':<8}")
print("-" * 70)
for r in results_all:
    q_desc = f"N={r['noun_qubits']},S={r['sentence_qubits']}"
    print(f"{r['config']:<8} {q_desc:<14} {r['n_params']:<10} "
          f"{r['train_acc']:.0%}      {r['test_acc']:.0%}      "
          f"{r['avg_confidence']:.3f}   {r['time_seconds']}s")

# Save
os.makedirs("results", exist_ok=True)
with open("results/qubit_scaling_results.json", "w") as f:
    json.dump(results_all, f, indent=2)

print(f"\nResults saved to results/qubit_scaling_results.json")
print("\nKey insight: NOUN qubits = word representation richness")
print("SENTENCE=1 keeps binary output. Watch confidence + time scaling.")
#!/usr/bin/env python3
"""
Sprint 2: Quantum vs Classical Head-to-Head
=============================================
Runs the quantum DisCoCat model on the SAME hard test set
that classical models struggled with (50-69% accuracy).

Train on original 16 sentences, test on 16 hard unseen sentences.
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

# === ORIGINAL TRAINING DATA (same as all tutorials) ===
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

# === EASY TEST (from tutorials) ===
easy_test_sentences = [
    "find reviews for new phones",
    "search for holiday deals online",
    "look up football scores today",
    "turn on the kitchen lights",
    "set a reminder for the meeting",
    "play some relaxing music now",
]
easy_test_labels = [0,0,0, 1,1,1]

# === HARD TEST (same as classical baseline) ===
hard_test_sentences = [
    "what is the capital of France",
    "how tall is mount Everest",
    "show me pictures of cats",
    "who won the world cup",
    "tell me about quantum computing",
    "what time does the shop close",
    "where is the nearest hospital",
    "how do you make pancakes",
    "remind me to call mum at six",
    "switch off all the lights",
    "pause the music for a moment",
    "read my latest email out loud",
    "start the coffee machine now",
    "cancel my morning alarm please",
    "dim the living room lights",
    "skip to the next song",
]
hard_test_labels = [0,0,0,0,0,0,0,0, 1,1,1,1,1,1,1,1]

intent_names = {0: "SEARCH", 1: "ACTION"}

# === PARSE ALL SENTENCES ===
print("Parsing all sentences with StairsReader...")
reader = stairs_reader
remove_cups = RemoveCupsRewriter()

raw_train = reader.sentences2diagrams(train_sentences)
raw_easy = reader.sentences2diagrams(easy_test_sentences)
raw_hard = reader.sentences2diagrams(hard_test_sentences)

# Remove failed parses
def clean(diagrams, labels, sentences):
    triples = [(d, l, s) for d, l, s in zip(diagrams, labels, sentences) if d is not None]
    if len(triples) < len(diagrams):
        print(f"  Warning: {len(diagrams) - len(triples)} sentences failed to parse")
    return [t[0] for t in triples], [t[1] for t in triples], [t[2] for t in triples]

raw_train, train_labels, train_sentences = clean(raw_train, train_labels, train_sentences)
raw_easy, easy_test_labels, easy_test_sentences = clean(raw_easy, easy_test_labels, easy_test_sentences)
raw_hard, hard_test_labels, hard_test_sentences = clean(raw_hard, hard_test_labels, hard_test_sentences)

train_diagrams = [remove_cups(d) for d in raw_train]
easy_diagrams = [remove_cups(d) for d in raw_easy]
hard_diagrams = [remove_cups(d) for d in raw_hard]

print(f"  Train: {len(train_diagrams)} | Easy test: {len(easy_diagrams)} | Hard test: {len(hard_diagrams)}")

# === RUN ALL THREE CONFIGS ===
configs = [
    {"name": "Quantum N=1", "noun": 1, "layers": 2},
    {"name": "Quantum N=2", "noun": 2, "layers": 2},
    {"name": "Quantum N=3", "noun": 3, "layers": 2},
]

def loss_fn(y_pred, y_true):
    return torch.nn.functional.mse_loss(y_pred, y_true.to(y_pred.dtype))

def accuracy_fn(y_pred, y_true):
    return (torch.argmax(y_pred, dim=1) == torch.argmax(y_true.to(y_pred.dtype), dim=1)).sum().item() / len(y_true)

train_labels_2d = np.array([[1-l, l] for l in train_labels], dtype=np.float64)
easy_labels_2d = np.array([[1-l, l] for l in easy_test_labels], dtype=np.float64)
hard_labels_2d = np.array([[1-l, l] for l in hard_test_labels], dtype=np.float64)

all_results = []

for cfg in configs:
    print("\n" + "=" * 60)
    print(f"{cfg['name']} (NOUN={cfg['noun']}, SENTENCE=1, layers={cfg['layers']})")
    print("=" * 60)

    ansatz = IQPAnsatz(
        {AtomicType.NOUN: cfg['noun'], AtomicType.SENTENCE: 1},
        n_layers=cfg['layers'],
        n_single_qubit_params=3,
    )

    t_start = time.time()

    train_circuits = [ansatz(d) for d in train_diagrams]
    easy_circuits = [ansatz(d) for d in easy_diagrams]
    hard_circuits = [ansatz(d) for d in hard_diagrams]

    # Model needs ALL circuits it will ever see
    all_circuits = train_circuits + easy_circuits + hard_circuits
    model = PytorchQuantumModel.from_diagrams(all_circuits)
    model.initialise_weights()
    print(f"  Parameters: {len(model.symbols)}")

    train_dataset = Dataset(train_circuits, train_labels_2d, batch_size=4)
    easy_dataset = Dataset(easy_circuits, easy_labels_2d, batch_size=4)

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

    print("\n  Training...")
    trainer.fit(train_dataset, easy_dataset)

    elapsed = time.time() - t_start

    # === EVALUATE ALL THREE SETS ===
    train_preds = model(train_circuits)
    easy_preds = model(easy_circuits)
    hard_preds = model(hard_circuits)

    def calc_acc(preds, labels_2d):
        pred_classes = torch.argmax(preds, dim=1)
        true_classes = torch.tensor(np.argmax(labels_2d, axis=1))
        return (pred_classes == true_classes).float().mean().item()

    def calc_conf(preds):
        return preds.detach().max(dim=1).values.mean().item()

    train_acc = calc_acc(train_preds, train_labels_2d)
    easy_acc = calc_acc(easy_preds, easy_labels_2d)
    hard_acc = calc_acc(hard_preds, hard_labels_2d)
    hard_conf = calc_conf(hard_preds)

    result = {
        "method": cfg['name'],
        "noun_qubits": cfg['noun'],
        "n_params": len(model.symbols),
        "train_acc": round(train_acc, 4),
        "easy_test_acc": round(easy_acc, 4),
        "hard_test_acc": round(hard_acc, 4),
        "hard_confidence": round(hard_conf, 4),
        "time_seconds": round(elapsed, 1),
    }
    all_results.append(result)

    print(f"\n  Train: {train_acc:.1%} | Easy: {easy_acc:.1%} | HARD: {hard_acc:.1%}")
    print(f"  Hard confidence: {hard_conf:.3f} | Time: {elapsed:.1f}s")

    # Detailed hard test predictions
    if cfg['noun'] == 3:  # Show details for best config
        print(f"\n  HARD TEST DETAILED ({cfg['name']}):")
        print("  " + "-" * 56)
        hard_pred_classes = torch.argmax(hard_preds, dim=1)
        hard_true_classes = torch.tensor(np.argmax(hard_labels_2d, axis=1))
        for i, (sent, pred, true_l) in enumerate(zip(hard_test_sentences, hard_pred_classes, hard_true_classes)):
            p = pred.item()
            t = true_l.item()
            status = "CORRECT" if p == t else "WRONG"
            probs = hard_preds[i].detach().numpy()
            print(f"    [{status}] \"{sent}\"")
            print(f"       Pred: {intent_names[p]} | True: {intent_names[t]} | Probs: [{probs[0]:.3f}, {probs[1]:.3f}]")

# === FINAL COMPARISON ===
print("\n\n" + "=" * 80)
print("FINAL HEAD-TO-HEAD: QUANTUM vs CLASSICAL on HARD TEST SET")
print("=" * 80)

# Add classical results
classical_results = [
    {"method": "TF-IDF + LogReg", "hard_test_acc": 0.50, "hard_confidence": 0.580},
    {"method": "TF-IDF + SVM-linear", "hard_test_acc": 0.50, "hard_confidence": 0.654},
    {"method": "TF-IDF + SVM-rbf", "hard_test_acc": 0.50, "hard_confidence": 0.715},
    {"method": "spaCy + LogReg", "hard_test_acc": 0.69, "hard_confidence": 0.798},
    {"method": "spaCy + SVM-rbf", "hard_test_acc": 0.63, "hard_confidence": 0.697},
]

print(f"\n  {'Method':<28} {'Hard Test Acc':<16} {'Confidence':<12}")
print("  " + "-" * 56)
for r in classical_results:
    print(f"  {r['method']:<28} {r['hard_test_acc']:.0%}              {r['hard_confidence']:.3f}")
print("  " + "-" * 56)
for r in all_results:
    print(f"  {r['method']:<28} {r['hard_test_acc']:.0%}              {r['hard_confidence']:.3f}")

# Save
os.makedirs("results", exist_ok=True)
with open("results/quantum_vs_classical_hard.json", "w") as f:
    json.dump({"quantum": all_results, "classical": classical_results}, f, indent=2)

print(f"\nResults saved to results/quantum_vs_classical_hard.json")
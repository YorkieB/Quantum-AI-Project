#!/usr/bin/env python3
"""
Sprint 3, Task 3.1: CLINC150 Real-World Intent Classification
===============================================================
Jarvis Quantum - Real benchmark data

CLINC150: 150 intent classes, 10 domains, plus out-of-scope detection.
We'll start with a manageable subset for quantum comparison.

Strategy:
  1. Download CLINC150
  2. Pick a challenging domain subset (5-10 intents)
  3. Run classical baselines
  4. Run quantum model
  5. Compare on REAL human-written data
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import json
import os
import time
import random
from collections import Counter

random.seed(42)
np.random.seed(42)

# ================================================================
# PART 1: DOWNLOAD CLINC150
# ================================================================
print("Downloading CLINC150 dataset...")

import urllib.request

url = "https://raw.githubusercontent.com/clinc/oos-eval/master/data/data_full.json"
os.makedirs("data", exist_ok=True)
data_path = "data/clinc150_full.json"

if not os.path.exists(data_path):
    urllib.request.urlretrieve(url, data_path)
    print("  Downloaded.")
else:
    print("  Already cached.")

with open(data_path) as f:
    clinc = json.load(f)

# Structure: clinc['train'], clinc['val'], clinc['test'] — each is list of [sentence, intent]
# Also clinc['oos_train'], clinc['oos_val'], clinc['oos_test'] for out-of-scope

train_all = clinc['train']
val_all = clinc['val']
test_all = clinc['test']

all_intents = sorted(set(intent for _, intent in train_all))
print(f"  Total: {len(train_all)} train, {len(val_all)} val, {len(test_all)} test")
print(f"  Intents: {len(all_intents)}")

# Group by domain (CLINC150 has 10 domains, 15 intents each)
# Let's see the distribution
intent_counts = Counter(intent for _, intent in train_all)
print(f"  Samples per intent: {intent_counts.most_common(1)[0][1]}")

# ================================================================
# PART 2: SELECT CHALLENGING SUBSET
# ================================================================
# Pick intents that are semantically CLOSE (hard to distinguish)
# Banking/finance domain — these overlap in meaning

# First, let's see what intents exist
print("\n  All intents (first 30):")
for i, intent in enumerate(all_intents[:30]):
    print(f"    {intent}")

# Select confusable intent groups
# Group 1: Information seeking (easily confused)
info_intents = [
    'balance', 'bill_balance', 'bill_due', 'pay_bill',
    'transfer', 'transactions', 'spending_history',
]

# Group 2: Travel (semantically close)
travel_intents = [
    'book_flight', 'book_hotel', 'car_rental',
    'travel_suggestion', 'travel_alert', 'flight_status',
    'international_visa',
]

# Group 3: Utility (action vs info ambiguity)
utility_intents = [
    'alarm', 'reminder', 'timer', 'todo_list',
    'calendar', 'calendar_update', 'meeting_schedule',
]

# Let's check which of these exist in the dataset
available = set(all_intents)

def filter_available(intents):
    return [i for i in intents if i in available]

info_intents = filter_available(info_intents)
travel_intents = filter_available(travel_intents)
utility_intents = filter_available(utility_intents)

print(f"\n  Available intent groups:")
print(f"    Finance: {info_intents}")
print(f"    Travel:  {travel_intents}")
print(f"    Utility: {utility_intents}")

# Use all three groups combined — ~20 intents, very challenging
selected_intents = info_intents + travel_intents + utility_intents

# If we don't have enough, fall back to first N intents
if len(selected_intents) < 6:
    print("  Not enough matched intents, using first 10 alphabetically")
    selected_intents = all_intents[:10]

print(f"\n  Selected {len(selected_intents)} intents for benchmark:")
for intent in selected_intents:
    count = sum(1 for _, i in train_all if i == intent)
    print(f"    {intent}: {count} train samples")

# Filter data
def filter_data(data, intents):
    intent_set = set(intents)
    intent_to_idx = {intent: idx for idx, intent in enumerate(sorted(intents))}
    filtered = [(sent, intent_to_idx[intent]) for sent, intent in data if intent in intent_set]
    return filtered, intent_to_idx

train_filtered, intent_map = filter_data(train_all, selected_intents)
val_filtered, _ = filter_data(val_all, selected_intents)
test_filtered, _ = filter_data(test_all, selected_intents)

idx_to_intent = {v: k for k, v in intent_map.items()}

train_sents = [s for s, l in train_filtered]
train_labels = np.array([l for s, l in train_filtered])
val_sents = [s for s, l in val_filtered]
val_labels = np.array([l for s, l in val_filtered])
test_sents = [s for s, l in test_filtered]
test_labels = np.array([l for s, l in test_filtered])

n_classes = len(selected_intents)
print(f"\n  Final dataset:")
print(f"    Train: {len(train_sents)} | Val: {len(val_sents)} | Test: {len(test_sents)}")
print(f"    Classes: {n_classes}")

# Show sample sentences
print("\n  Sample sentences:")
for intent_name, idx in sorted(intent_map.items())[:5]:
    examples = [s for s, l in train_filtered if l == idx][:2]
    for ex in examples:
        print(f"    [{intent_name}] {ex}")

# ================================================================
# PART 3: CLASSICAL BASELINES
# ================================================================
print("\n" + "=" * 70)
print(f"CLASSICAL BASELINES ({n_classes}-class classification)")
print("=" * 70)

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, classification_report
import spacy

nlp = spacy.load("en_core_web_sm")

# TF-IDF
tfidf = TfidfVectorizer(ngram_range=(1, 2), max_features=3000)
X_train_tfidf = tfidf.fit_transform(train_sents)
X_val_tfidf = tfidf.transform(val_sents)
X_test_tfidf = tfidf.transform(test_sents)

# spaCy vectors
X_train_spacy = np.array([nlp(s).vector for s in train_sents])
X_val_spacy = np.array([nlp(s).vector for s in val_sents])
X_test_spacy = np.array([nlp(s).vector for s in test_sents])

classical_models = {
    "TF-IDF + LogReg": (LogisticRegression(max_iter=2000, random_state=42, C=1.0),
                        X_train_tfidf, X_val_tfidf, X_test_tfidf),
    "TF-IDF + SVM-linear": (SVC(kernel='linear', probability=True, random_state=42),
                            X_train_tfidf, X_val_tfidf, X_test_tfidf),
    "spaCy + LogReg": (LogisticRegression(max_iter=2000, random_state=42),
                       X_train_spacy, X_val_spacy, X_test_spacy),
    "spaCy + SVM-rbf": (SVC(kernel='rbf', probability=True, random_state=42),
                        X_train_spacy, X_val_spacy, X_test_spacy),
}

classical_results = []

for name, (clf, X_tr, X_va, X_te) in classical_models.items():
    t_start = time.time()
    clf.fit(X_tr, train_labels)
    elapsed = time.time() - t_start

    train_acc = accuracy_score(train_labels, clf.predict(X_tr))
    val_acc = accuracy_score(val_labels, clf.predict(X_va))
    test_acc = accuracy_score(test_labels, clf.predict(X_te))
    test_f1 = f1_score(test_labels, clf.predict(X_te), average='weighted')

    result = {
        "method": name,
        "train_acc": round(train_acc, 4),
        "val_acc": round(val_acc, 4),
        "test_acc": round(test_acc, 4),
        "test_f1": round(test_f1, 4),
        "time": round(elapsed, 3),
    }
    classical_results.append(result)

    print(f"\n  {name}")
    print(f"    Train: {train_acc:.1%}  Val: {val_acc:.1%}  Test: {test_acc:.1%}  F1: {test_f1:.3f}  ({elapsed:.1f}s)")

# Best classical — show confusion areas
best_clf_name = max(classical_results, key=lambda r: r['test_acc'])['method']
print(f"\n  Best classical: {best_clf_name}")

# Show per-class accuracy for best model
best_clf = [clf for name, (clf, _, _, _) in classical_models.items() if name == best_clf_name][0]
X_te_best = X_test_tfidf if "TF-IDF" in best_clf_name else X_test_spacy
test_preds_classical = best_clf.predict(X_te_best)

print(f"\n  Per-class test accuracy ({best_clf_name}):")
for idx in range(n_classes):
    mask = test_labels == idx
    if mask.sum() > 0:
        class_acc = accuracy_score(test_labels[mask], test_preds_classical[mask])
        intent_name = idx_to_intent[idx]
        n_samples = mask.sum()
        print(f"    {intent_name:<25} {class_acc:.0%} ({n_samples} samples)")

# ================================================================
# PART 4: QUANTUM MODEL (Binary subset — most confusable pair)
# ================================================================
print("\n" + "=" * 70)
print("QUANTUM MODEL — Most Confusable Intent Pair")
print("=" * 70)

# Find the most confused pair from classical predictions
from sklearn.metrics import confusion_matrix

cm = confusion_matrix(test_labels, test_preds_classical)
# Zero out diagonal
cm_off = cm.copy()
np.fill_diagonal(cm_off, 0)

# Find most confused pair
max_idx = np.unravel_index(cm_off.argmax(), cm_off.shape)
intent_a = idx_to_intent[max_idx[0]]
intent_b = idx_to_intent[max_idx[1]]
confusion_count = cm_off[max_idx]

print(f"\n  Most confused pair: '{intent_a}' vs '{intent_b}' ({confusion_count} misclassifications)")

# If no confusions, pick two semantically close intents
if confusion_count == 0:
    # Pick first two intents as fallback
    intent_a = idx_to_intent[0]
    intent_b = idx_to_intent[1]
    print(f"  No confusions found! Using first two: '{intent_a}' vs '{intent_b}'")

# Extract binary subset
label_a = intent_map[intent_a]
label_b = intent_map[intent_b]

def make_binary(sents, labels, la, lb):
    pairs = [(s, 0 if l == la else 1) for s, l in zip(sents, labels) if l in (la, lb)]
    return [s for s, l in pairs], np.array([l for s, l in pairs])

q_train_sents, q_train_labels = make_binary(train_sents, train_labels, label_a, label_b)
q_val_sents, q_val_labels = make_binary(val_sents, val_labels, label_a, label_b)
q_test_sents, q_test_labels = make_binary(test_sents, test_labels, label_a, label_b)

print(f"  Binary dataset: {len(q_train_sents)} train, {len(q_val_sents)} val, {len(q_test_sents)} test")
print(f"    Class 0 ({intent_a}): {sum(q_train_labels==0)} train")
print(f"    Class 1 ({intent_b}): {sum(q_train_labels==1)} train")

# Show examples
print(f"\n  Examples:")
for s, l in zip(q_train_sents[:3], q_train_labels[:3]):
    name = intent_a if l == 0 else intent_b
    print(f"    [{name}] {s}")

# Classical baseline on this binary task
print(f"\n  Classical on binary pair:")
tfidf_bin = TfidfVectorizer(ngram_range=(1, 2), max_features=1000)
X_tr_bin = tfidf_bin.fit_transform(q_train_sents)
X_va_bin = tfidf_bin.transform(q_val_sents)
X_te_bin = tfidf_bin.transform(q_test_sents)

for name, clf in [("LogReg", LogisticRegression(max_iter=1000, random_state=42)),
                  ("SVM", SVC(kernel='linear', probability=True, random_state=42))]:
    clf.fit(X_tr_bin, q_train_labels)
    val_acc = accuracy_score(q_val_labels, clf.predict(X_va_bin))
    test_acc = accuracy_score(q_test_labels, clf.predict(X_te_bin))
    print(f"    TF-IDF + {name}: Val: {val_acc:.1%}  Test: {test_acc:.1%}")

# Quantum
import torch
from lambeq import (
    RemoveCupsRewriter,
    IQPAnsatz,
    AtomicType,
    PytorchTrainer,
    PytorchQuantumModel,
    Dataset,
    stairs_reader,
)

# Truncate to 10 words max
MAX_WORDS = 10
q_train_short = [" ".join(s.split()[:MAX_WORDS]) for s in q_train_sents]
q_val_short = [" ".join(s.split()[:MAX_WORDS]) for s in q_val_sents]
q_test_short = [" ".join(s.split()[:MAX_WORDS]) for s in q_test_sents]

# Subsample training if too large
MAX_Q_TRAIN = 80
if len(q_train_short) > MAX_Q_TRAIN:
    idx_0 = [i for i, l in enumerate(q_train_labels) if l == 0]
    idx_1 = [i for i, l in enumerate(q_train_labels) if l == 1]
    per_class = MAX_Q_TRAIN // 2
    selected = sorted(
        list(np.random.choice(idx_0, min(per_class, len(idx_0)), replace=False)) +
        list(np.random.choice(idx_1, min(per_class, len(idx_1)), replace=False))
    )
    q_train_short = [q_train_short[i] for i in selected]
    q_train_labels_q = np.array([q_train_labels[i] for i in selected])
else:
    q_train_labels_q = q_train_labels

print(f"\n  Quantum training: {len(q_train_short)} sentences (max {MAX_WORDS} words)")

reader = stairs_reader
remove_cups = RemoveCupsRewriter()

def parse_clean(sentences, labels):
    raw = reader.sentences2diagrams(sentences)
    pairs = [(d, l) for d, l in zip(raw, labels) if d is not None]
    if len(pairs) < len(sentences):
        print(f"    {len(sentences)-len(pairs)} failed parses")
    return [remove_cups(p[0]) for p in pairs], np.array([p[1] for p in pairs])

print("  Parsing...")
q_tr_diag, q_tr_lab = parse_clean(q_train_short, q_train_labels_q)
q_va_diag, q_va_lab = parse_clean(q_val_short, q_val_labels)
q_te_diag, q_te_lab = parse_clean(q_test_short, q_test_labels)

print(f"  Parsed: {len(q_tr_diag)} train, {len(q_va_diag)} val, {len(q_te_diag)} test")

q_tr_lab_2d = np.array([[1-l, l] for l in q_tr_lab], dtype=np.float64)
q_va_lab_2d = np.array([[1-l, l] for l in q_va_lab], dtype=np.float64)
q_te_lab_2d = np.array([[1-l, l] for l in q_te_lab], dtype=np.float64)

def loss_fn(y_pred, y_true):
    return torch.nn.functional.mse_loss(y_pred, y_true.to(y_pred.dtype))

def accuracy_fn(y_pred, y_true):
    return (torch.argmax(y_pred, dim=1) == torch.argmax(y_true.to(y_pred.dtype), dim=1)).sum().item() / len(y_true)

ansatz = IQPAnsatz(
    {AtomicType.NOUN: 1, AtomicType.SENTENCE: 1},
    n_layers=2,
    n_single_qubit_params=3,
)

print("  Building circuits...")
t_start = time.time()

tr_circuits = [ansatz(d) for d in q_tr_diag]
va_circuits = [ansatz(d) for d in q_va_diag]
te_circuits = [ansatz(d) for d in q_te_diag]

all_circuits = tr_circuits + va_circuits + te_circuits
model = PytorchQuantumModel.from_diagrams(all_circuits)
model.initialise_weights()
print(f"  Parameters: {len(model.symbols)}")

tr_dataset = Dataset(tr_circuits, q_tr_lab_2d, batch_size=8)
va_dataset = Dataset(va_circuits, q_va_lab_2d, batch_size=8)

trainer = PytorchTrainer(
    model=model,
    loss_function=loss_fn,
    optimizer=torch.optim.Adam,
    learning_rate=0.05,
    epochs=100,
    evaluate_functions={"accuracy": accuracy_fn},
    evaluate_on_train=True,
    verbose='text',
    seed=42,
)

print("  Training (100 epochs)...")
trainer.fit(tr_dataset, va_dataset)
elapsed = time.time() - t_start

# Evaluate
tr_preds = model(tr_circuits)
va_preds = model(va_circuits)
te_preds = model(te_circuits)

def calc_acc(preds, lab_2d):
    return (torch.argmax(preds, dim=1) == torch.tensor(np.argmax(lab_2d, axis=1))).float().mean().item()

q_train_acc = calc_acc(tr_preds, q_tr_lab_2d)
q_val_acc = calc_acc(va_preds, q_va_lab_2d)
q_test_acc = calc_acc(te_preds, q_te_lab_2d)
q_conf = te_preds.detach().max(dim=1).values.mean().item()

print(f"\n  Quantum N=1: Train: {q_train_acc:.1%}  Val: {q_val_acc:.1%}  Test: {q_test_acc:.1%}  Conf: {q_conf:.3f}  Time: {elapsed:.0f}s")

# Detailed test predictions
print(f"\n  Detailed quantum predictions:")
print("  " + "-" * 56)
te_pred_classes = torch.argmax(te_preds, dim=1)
te_true_classes = torch.tensor(np.argmax(q_te_lab_2d, axis=1))
q_test_sents_used = q_test_short[:len(te_pred_classes)]  # match parsed count

correct = 0
total = len(te_pred_classes)
for i in range(min(total, 20)):  # show first 20
    p = te_pred_classes[i].item()
    t = te_true_classes[i].item()
    name_p = intent_a if p == 0 else intent_b
    name_t = intent_a if t == 0 else intent_b
    status = "CORRECT" if p == t else "WRONG"
    probs = te_preds[i].detach().numpy()
    if i < len(q_test_sents_used):
        print(f"    [{status}] \"{q_test_sents_used[i]}\"")
        print(f"       Pred: {name_p} | True: {name_t} | [{probs[0]:.3f}, {probs[1]:.3f}]")

# ================================================================
# FINAL SUMMARY
# ================================================================
print("\n\n" + "=" * 80)
print(f"CLINC150 RESULTS SUMMARY")
print("=" * 80)

print(f"\n  MULTI-CLASS ({n_classes} intents):")
print(f"  {'Method':<24} {'Test Acc':<10} {'F1':<8}")
print("  " + "-" * 42)
for r in classical_results:
    print(f"  {r['method']:<24} {r['test_acc']:.1%}      {r['test_f1']:.3f}")

print(f"\n  BINARY ('{intent_a}' vs '{intent_b}'):")
print(f"  {'Method':<24} {'Test Acc':<10}")
print("  " + "-" * 34)

# Re-run classical binary for summary
for name, clf in [("TF-IDF + LogReg", LogisticRegression(max_iter=1000, random_state=42)),
                  ("TF-IDF + SVM", SVC(kernel='linear', probability=True, random_state=42))]:
    clf.fit(X_tr_bin, q_train_labels)
    test_acc = accuracy_score(q_test_labels, clf.predict(X_te_bin))
    print(f"  {name:<24} {test_acc:.1%}")

print(f"  {'Quantum N=1':<24} {q_test_acc:.1%}")

# Save all results
os.makedirs("results", exist_ok=True)
all_results = {
    "dataset": "CLINC150",
    "n_classes_multi": n_classes,
    "selected_intents": selected_intents,
    "binary_pair": [intent_a, intent_b],
    "classical_multi": classical_results,
    "quantum_binary": {
        "method": "Quantum N=1",
        "train_acc": round(q_train_acc, 4),
        "val_acc": round(q_val_acc, 4),
        "test_acc": round(q_test_acc, 4),
        "confidence": round(q_conf, 4),
        "time_seconds": round(elapsed, 1),
        "n_params": len(model.symbols),
        "train_size": len(tr_circuits),
    },
    "intent_map": intent_map,
}
with open("results/sprint3_clinc150.json", "w") as f:
    json.dump(all_results, f, indent=2)

print(f"\nResults saved to results/sprint3_clinc150.json")
print(f"Dataset cached at data/clinc150_full.json")
print("\nTask 3.1 Complete - CLINC150 Benchmark")
print("Next: Task 3.2 - Real credibility dataset (LIAR)")
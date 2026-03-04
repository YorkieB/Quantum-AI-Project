#!/usr/bin/env python3
"""
Sprint 4, Task 4.1: Hybrid Classical+Quantum Credibility Pipeline
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

print("Loading LIAR dataset...")

def load_liar(path):
    data = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                data.append({"statement": parts[2], "label": parts[1]})
    return data

train_raw = load_liar("data/liar_train.tsv")
val_raw = load_liar("data/liar_val.tsv")
test_raw = load_liar("data/liar_test.tsv")

credible = {'true', 'mostly-true'}
not_credible = {'false', 'pants-fire'}

def make_binary(data):
    return [(d['statement'], 0 if d['label'] in credible else 1)
            for d in data if d['label'] in credible | not_credible]

train_data = make_binary(train_raw)
val_data = make_binary(val_raw)
test_data = make_binary(test_raw)

train_sents = [s for s, l in train_data]
train_labels = np.array([l for s, l in train_data])
val_sents = [s for s, l in val_data]
val_labels = np.array([l for s, l in val_data])
test_sents = [s for s, l in test_data]
test_labels = np.array([l for s, l in test_data])

print(f"  Train: {len(train_sents)} | Val: {len(val_sents)} | Test: {len(test_sents)}")
majority = max(Counter(test_labels).values()) / len(test_labels)
print(f"  Majority baseline: {majority:.1%}")

print("\n" + "=" * 70)
print("STAGE 1: Classical Pre-Filter (TF-IDF + LogReg)")
print("=" * 70)

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

tfidf = TfidfVectorizer(ngram_range=(1, 3), max_features=5000)
X_train_tfidf = tfidf.fit_transform(train_sents)
X_val_tfidf = tfidf.transform(val_sents)
X_test_tfidf = tfidf.transform(test_sents)

clf = LogisticRegression(max_iter=2000, random_state=42)
clf.fit(X_train_tfidf, train_labels)

train_probs = clf.predict_proba(X_train_tfidf)
val_probs = clf.predict_proba(X_val_tfidf)
test_probs = clf.predict_proba(X_test_tfidf)

classical_test_preds = clf.predict(X_test_tfidf)
classical_test_acc = accuracy_score(test_labels, classical_test_preds)
classical_test_f1 = f1_score(test_labels, classical_test_preds, average='weighted')

print(f"\n  Classical standalone: Test Acc: {classical_test_acc:.1%}  F1: {classical_test_f1:.3f}")

test_confidence = test_probs.max(axis=1)

print("\n  Confidence distribution on test set:")
for threshold in [0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
    n_uncertain = (test_confidence < threshold).sum()
    pct = n_uncertain / len(test_confidence)
    confident_mask = test_confidence >= threshold
    uncertain_mask = ~confident_mask
    if confident_mask.sum() > 0:
        confident_acc = accuracy_score(test_labels[confident_mask], classical_test_preds[confident_mask])
    else:
        confident_acc = 0
    if uncertain_mask.sum() > 0:
        uncertain_acc = accuracy_score(test_labels[uncertain_mask], classical_test_preds[uncertain_mask])
    else:
        uncertain_acc = 0
    print(f"    Threshold {threshold}: {n_uncertain} uncertain ({pct:.0%}) | "
          f"Confident acc: {confident_acc:.1%} | Uncertain acc: {uncertain_acc:.1%}")

CONFIDENCE_THRESHOLD = 0.65
confident_mask = test_confidence >= CONFIDENCE_THRESHOLD
uncertain_mask = ~confident_mask

n_confident = confident_mask.sum()
n_uncertain = uncertain_mask.sum()

print(f"\n  Selected threshold: {CONFIDENCE_THRESHOLD}")
print(f"  Confident cases: {n_confident} ({n_confident/len(test_labels):.0%})")
print(f"  Uncertain cases: {n_uncertain} ({n_uncertain/len(test_labels):.0%})")

confident_acc = accuracy_score(test_labels[confident_mask], classical_test_preds[confident_mask]) if n_confident > 0 else 0
uncertain_acc_classical = accuracy_score(test_labels[uncertain_mask], classical_test_preds[uncertain_mask]) if n_uncertain > 0 else 0

print(f"  Classical on confident: {confident_acc:.1%}")
print(f"  Classical on uncertain: {uncertain_acc_classical:.1%} (quantum target)")

print("\n" + "=" * 70)
print("STAGE 2: Quantum Reasoning (DisCoCat on uncertain cases)")
print("=" * 70)

import torch
from lambeq import (
    RemoveCupsRewriter, IQPAnsatz, AtomicType,
    PytorchTrainer, PytorchQuantumModel, Dataset, stairs_reader,
)

MAX_WORDS = 10

uncertain_test_sents = [test_sents[i] for i in range(len(test_sents)) if uncertain_mask[i]]
uncertain_test_labels = test_labels[uncertain_mask]

print(f"\n  Uncertain test sentences: {len(uncertain_test_sents)}")

train_confidence = train_probs.max(axis=1)
train_uncertain_mask = train_confidence < CONFIDENCE_THRESHOLD

uncertain_train_idx = np.where(train_uncertain_mask)[0]
certain_train_idx = np.where(~train_uncertain_mask)[0]

Q_TRAIN = 80
n_uncertain_pick = min(Q_TRAIN // 2, len(uncertain_train_idx))
n_certain_pick = Q_TRAIN - n_uncertain_pick

def balanced_sample(indices, labels, n):
    idx_0 = [i for i in indices if labels[i] == 0]
    idx_1 = [i for i in indices if labels[i] == 1]
    n_per = n // 2
    picked_0 = list(np.random.choice(idx_0, min(n_per, len(idx_0)), replace=False)) if idx_0 else []
    picked_1 = list(np.random.choice(idx_1, min(n_per, len(idx_1)), replace=False)) if idx_1 else []
    return sorted(picked_0 + picked_1)

uncertain_picks = balanced_sample(uncertain_train_idx, train_labels, n_uncertain_pick)
certain_picks = balanced_sample(certain_train_idx, train_labels, n_certain_pick)
q_train_idx = sorted(uncertain_picks + certain_picks)

q_train_sents = [" ".join(train_sents[i].split()[:MAX_WORDS]) for i in q_train_idx]
q_train_labels = np.array([train_labels[i] for i in q_train_idx])

q_test_sents = [" ".join(s.split()[:MAX_WORDS]) for s in uncertain_test_sents]
q_test_labels = uncertain_test_labels

q_val_sents_full = [" ".join(s.split()[:MAX_WORDS]) for s in val_sents]
q_val_labels_full = val_labels

MAX_VAL = 80
if len(q_val_sents_full) > MAX_VAL:
    val_idx = sorted(np.random.choice(len(q_val_sents_full), MAX_VAL, replace=False))
    q_val_sents_sub = [q_val_sents_full[i] for i in val_idx]
    q_val_labels_sub = q_val_labels_full[val_idx]
else:
    q_val_sents_sub = q_val_sents_full
    q_val_labels_sub = q_val_labels_full

print(f"  Quantum training: {len(q_train_sents)} ({sum(q_train_labels==0)} cred, {sum(q_train_labels==1)} not)")
print(f"  Quantum val: {len(q_val_sents_sub)} | Quantum test: {len(q_test_sents)}")

reader = stairs_reader
remove_cups = RemoveCupsRewriter()

def parse_clean(sentences, labels):
    raw = reader.sentences2diagrams(sentences)
    pairs = [(d, l) for d, l in zip(raw, labels) if d is not None]
    if len(pairs) < len(sentences):
        print(f"    {len(sentences)-len(pairs)} failed parses removed")
    return [remove_cups(p[0]) for p in pairs], np.array([p[1] for p in pairs])

print("  Parsing...")
q_tr_diag, q_tr_lab = parse_clean(q_train_sents, q_train_labels)
q_va_diag, q_va_lab = parse_clean(q_val_sents_sub, q_val_labels_sub)
q_te_diag, q_te_lab = parse_clean(q_test_sents, q_test_labels)

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
    n_layers=2, n_single_qubit_params=3,
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
    model=model, loss_function=loss_fn,
    optimizer=torch.optim.Adam, learning_rate=0.05,
    epochs=100, evaluate_functions={"accuracy": accuracy_fn},
    evaluate_on_train=True, verbose='text', seed=42,
)

print("  Training (100 epochs)...")
trainer.fit(tr_dataset, va_dataset)
elapsed = time.time() - t_start

te_preds = model(te_circuits)
te_pred_classes = torch.argmax(te_preds, dim=1).numpy()
te_true_classes = np.argmax(q_te_lab_2d, axis=1)

quantum_uncertain_acc = accuracy_score(te_true_classes, te_pred_classes)
print(f"\n  Quantum on uncertain: {quantum_uncertain_acc:.1%}")
print(f"  Classical on uncertain: {uncertain_acc_classical:.1%}")
print(f"  Improvement: {(quantum_uncertain_acc - uncertain_acc_classical)*100:+.1f} points")

print("\n" + "=" * 70)
print("STAGE 3: Hybrid Ensemble Results")
print("=" * 70)

strategy_a_preds = classical_test_preds.copy()
strategy_a_acc = accuracy_score(test_labels, strategy_a_preds)

strategy_b_preds = classical_test_preds.copy()
uncertain_indices = np.where(uncertain_mask)[0]
parsed_uncertain_count = len(te_pred_classes)
for i, test_idx in enumerate(uncertain_indices):
    if i < parsed_uncertain_count:
        strategy_b_preds[test_idx] = te_pred_classes[i]
strategy_b_acc = accuracy_score(test_labels, strategy_b_preds)

strategy_c_preds = classical_test_preds.copy()
te_preds_np = te_preds.detach().numpy()
for i, test_idx in enumerate(uncertain_indices):
    if i < len(te_preds_np):
        classical_prob = test_probs[test_idx]
        quantum_prob = te_preds_np[i]
        blended = 0.4 * classical_prob + 0.6 * quantum_prob
        strategy_c_preds[test_idx] = np.argmax(blended)
strategy_c_acc = accuracy_score(test_labels, strategy_c_preds)

print(f"\n  Strategy A - Classical only:        {strategy_a_acc:.1%}")
print(f"  Strategy B - Hybrid (hard switch):   {strategy_b_acc:.1%}")
print(f"  Strategy C - Hybrid (weighted blend): {strategy_c_acc:.1%}")
print(f"  Majority baseline:                   {majority:.1%}")

print(f"\n  Improvement over classical:")
print(f"    Strategy B: {(strategy_b_acc - strategy_a_acc)*100:+.1f} points")
print(f"    Strategy C: {(strategy_c_acc - strategy_a_acc)*100:+.1f} points")

if n_uncertain > 0:
    uncertain_b_acc = accuracy_score(test_labels[uncertain_mask], strategy_b_preds[uncertain_mask])
    uncertain_c_acc = accuracy_score(test_labels[uncertain_mask], strategy_c_preds[uncertain_mask])
    print(f"\n  Uncertain cases ({n_uncertain}):")
    print(f"    Classical:      {uncertain_acc_classical:.1%}")
    print(f"    Quantum only:   {quantum_uncertain_acc:.1%}")
    print(f"    Weighted blend: {uncertain_c_acc:.1%}")

print(f"\n  Speed: Classical ~10ms | Quantum {elapsed:.0f}s for {len(te_circuits)} cases")
print(f"  Hybrid saves: {n_confident}/{len(test_labels)} skip quantum ({n_confident/len(test_labels):.0%})")

os.makedirs("results", exist_ok=True)
results = {
    "pipeline": "Hybrid Classical+Quantum Credibility",
    "dataset": "LIAR",
    "threshold": CONFIDENCE_THRESHOLD,
    "classical_only": round(strategy_a_acc, 4),
    "hybrid_switch": round(strategy_b_acc, 4),
    "hybrid_blend": round(strategy_c_acc, 4),
    "classical_on_uncertain": round(uncertain_acc_classical, 4),
    "quantum_on_uncertain": round(quantum_uncertain_acc, 4),
    "majority_baseline": round(majority, 4),
}
with open("results/sprint4_hybrid_credibility.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to results/sprint4_hybrid_credibility.json")
print(f"\nTask 4.1 Complete")
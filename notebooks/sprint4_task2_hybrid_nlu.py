#!/usr/bin/env python3
"""
Sprint 4, Task 4.2: Hybrid Classical+Quantum NLU on CLINC150
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

print("Loading CLINC150...")

with open("data/clinc150_full.json") as f:
    clinc = json.load(f)

train_all = clinc['train']
val_all = clinc['val']
test_all = clinc['test']

info_intents = ['balance', 'bill_balance', 'bill_due', 'pay_bill',
                'transfer', 'transactions', 'spending_history']
travel_intents = ['book_flight', 'book_hotel', 'car_rental',
                  'travel_suggestion', 'travel_alert', 'flight_status',
                  'international_visa']
utility_intents = ['alarm', 'reminder', 'timer', 'todo_list',
                   'calendar', 'calendar_update', 'meeting_schedule']

available = set(intent for _, intent in train_all)
selected_intents = [i for i in info_intents + travel_intents + utility_intents if i in available]

intent_to_idx = {intent: idx for idx, intent in enumerate(sorted(selected_intents))}
idx_to_intent = {v: k for k, v in intent_to_idx.items()}
n_classes = len(selected_intents)

def filter_data(data):
    return [(sent, intent_to_idx[intent]) for sent, intent in data if intent in intent_to_idx]

train_filtered = filter_data(train_all)
val_filtered = filter_data(val_all)
test_filtered = filter_data(test_all)

train_sents = [s for s, l in train_filtered]
train_labels = np.array([l for s, l in train_filtered])
val_sents = [s for s, l in val_filtered]
val_labels = np.array([l for s, l in val_filtered])
test_sents = [s for s, l in test_filtered]
test_labels = np.array([l for s, l in test_filtered])

print(f"  {n_classes} intents | Train: {len(train_sents)} | Val: {len(val_sents)} | Test: {len(test_sents)}")

print("\n" + "=" * 70)
print("STAGE 1: Classical Multi-Class Classifier")
print("=" * 70)

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix

tfidf = TfidfVectorizer(ngram_range=(1, 2), max_features=3000)
X_train = tfidf.fit_transform(train_sents)
X_val = tfidf.transform(val_sents)
X_test = tfidf.transform(test_sents)

clf = LogisticRegression(max_iter=2000, random_state=42)
clf.fit(X_train, train_labels)

test_preds = clf.predict(X_test)
test_probs = clf.predict_proba(X_test)
test_acc = accuracy_score(test_labels, test_preds)

print(f"\n  Classical multi-class: {test_acc:.1%}")

cm = confusion_matrix(test_labels, test_preds)
cm_off = cm.copy()
np.fill_diagonal(cm_off, 0)

confused_pairs = []
cm_temp = cm_off.copy()
for _ in range(3):
    idx = np.unravel_index(cm_temp.argmax(), cm_temp.shape)
    count = cm_temp[idx]
    if count == 0:
        break
    confused_pairs.append({
        "intent_a": idx_to_intent[idx[0]],
        "intent_b": idx_to_intent[idx[1]],
        "label_a": idx[0],
        "label_b": idx[1],
        "confusions": int(count),
    })
    cm_temp[idx] = 0
    cm_temp[idx[1], idx[0]] = 0

print(f"\n  Top confused pairs:")
for pair in confused_pairs:
    print(f"    '{pair['intent_a']}' <-> '{pair['intent_b']}': {pair['confusions']} misclassifications")

test_confidence = test_probs.max(axis=1)
THRESHOLD = 0.60
uncertain_mask = test_confidence < THRESHOLD
n_uncertain = uncertain_mask.sum()

print(f"\n  Confidence threshold: {THRESHOLD}")
print(f"  Uncertain: {n_uncertain}/{len(test_labels)} ({n_uncertain/len(test_labels):.0%})")

if uncertain_mask.sum() > 0:
    uncertain_acc = accuracy_score(test_labels[uncertain_mask], test_preds[uncertain_mask])
    confident_acc = accuracy_score(test_labels[~uncertain_mask], test_preds[~uncertain_mask])
    print(f"  Confident accuracy: {confident_acc:.1%}")
    print(f"  Uncertain accuracy: {uncertain_acc:.1%}")

print("\n" + "=" * 70)
print("STAGE 2: Quantum Binary on Most Confused Pair")
print("=" * 70)

import torch
from lambeq import (
    RemoveCupsRewriter, IQPAnsatz, AtomicType,
    PytorchTrainer, PytorchQuantumModel, Dataset, stairs_reader,
)

if len(confused_pairs) == 0:
    pair = {"intent_a": idx_to_intent[0], "intent_b": idx_to_intent[1],
            "label_a": 0, "label_b": 1}
else:
    pair = confused_pairs[0]

intent_a = pair['intent_a']
intent_b = pair['intent_b']
label_a = pair['label_a']
label_b = pair['label_b']

print(f"\n  Target pair: '{intent_a}' vs '{intent_b}'")

def make_binary(sents, labels, la, lb):
    pairs = [(s, 0 if l == la else 1) for s, l in zip(sents, labels) if l in (la, lb)]
    return [s for s, l in pairs], np.array([l for s, l in pairs])

bin_train_sents, bin_train_labels = make_binary(train_sents, train_labels, label_a, label_b)
bin_val_sents, bin_val_labels = make_binary(val_sents, val_labels, label_a, label_b)
bin_test_sents, bin_test_labels = make_binary(test_sents, test_labels, label_a, label_b)

print(f"  Binary: {len(bin_train_sents)} train, {len(bin_val_sents)} val, {len(bin_test_sents)} test")

tfidf_bin = TfidfVectorizer(ngram_range=(1, 2), max_features=1000)
X_tr_bin = tfidf_bin.fit_transform(bin_train_sents)
X_va_bin = tfidf_bin.transform(bin_val_sents)
X_te_bin = tfidf_bin.transform(bin_test_sents)

clf_bin = LogisticRegression(max_iter=1000, random_state=42)
clf_bin.fit(X_tr_bin, bin_train_labels)
classical_bin_acc = accuracy_score(bin_test_labels, clf_bin.predict(X_te_bin))
print(f"  Classical binary: {classical_bin_acc:.1%}")

MAX_WORDS = 10
Q_TRAIN = 80

q_tr_sents = [" ".join(s.split()[:MAX_WORDS]) for s in bin_train_sents]
q_tr_labels = bin_train_labels

if len(q_tr_sents) > Q_TRAIN:
    idx_0 = [i for i, l in enumerate(q_tr_labels) if l == 0]
    idx_1 = [i for i, l in enumerate(q_tr_labels) if l == 1]
    per_class = Q_TRAIN // 2
    sel = sorted(
        list(np.random.choice(idx_0, min(per_class, len(idx_0)), replace=False)) +
        list(np.random.choice(idx_1, min(per_class, len(idx_1)), replace=False))
    )
    q_tr_sents = [q_tr_sents[i] for i in sel]
    q_tr_labels = q_tr_labels[sel]

q_va_sents = [" ".join(s.split()[:MAX_WORDS]) for s in bin_val_sents]
q_te_sents = [" ".join(s.split()[:MAX_WORDS]) for s in bin_test_sents]

reader = stairs_reader
remove_cups = RemoveCupsRewriter()

def parse_clean(sentences, labels):
    raw = reader.sentences2diagrams(sentences)
    pairs = [(d, l) for d, l in zip(raw, labels) if d is not None]
    if len(pairs) < len(sentences):
        print(f"    {len(sentences)-len(pairs)} failed parses")
    return [remove_cups(p[0]) for p in pairs], np.array([p[1] for p in pairs])

print("  Parsing...")
q_tr_diag, q_tr_lab = parse_clean(q_tr_sents, q_tr_labels)
q_va_diag, q_va_lab = parse_clean(q_va_sents, bin_val_labels)
q_te_diag, q_te_lab = parse_clean(q_te_sents, bin_test_labels)

MAX_EVAL = 60
if len(q_va_diag) > MAX_EVAL:
    va_idx = sorted(np.random.choice(len(q_va_diag), MAX_EVAL, replace=False))
    q_va_diag = [q_va_diag[i] for i in va_idx]
    q_va_lab = q_va_lab[va_idx]

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

tr_circ = [ansatz(d) for d in q_tr_diag]
va_circ = [ansatz(d) for d in q_va_diag]
te_circ = [ansatz(d) for d in q_te_diag]

all_circ = tr_circ + va_circ + te_circ
model = PytorchQuantumModel.from_diagrams(all_circ)
model.initialise_weights()
print(f"  Parameters: {len(model.symbols)}")

tr_ds = Dataset(tr_circ, q_tr_lab_2d, batch_size=8)
va_ds = Dataset(va_circ, q_va_lab_2d, batch_size=8)

trainer = PytorchTrainer(
    model=model, loss_function=loss_fn,
    optimizer=torch.optim.Adam, learning_rate=0.05,
    epochs=100, evaluate_functions={"accuracy": accuracy_fn},
    evaluate_on_train=True, verbose='text', seed=42,
)

print("  Training (100 epochs)...")
trainer.fit(tr_ds, va_ds)
elapsed = time.time() - t_start

te_preds = model(te_circ)
te_pred_classes = torch.argmax(te_preds, dim=1).numpy()
te_true_classes = np.argmax(q_te_lab_2d, axis=1)
quantum_bin_acc = accuracy_score(te_true_classes, te_pred_classes)

print(f"\n  Quantum binary: {quantum_bin_acc:.1%}")
print(f"  Classical binary: {classical_bin_acc:.1%}")

print("\n" + "=" * 70)
print("STAGE 3: Hybrid Multi-Class")
print("=" * 70)

hybrid_preds = test_preds.copy()
ab_mask = np.isin(test_preds, [label_a, label_b])
ab_uncertain = ab_mask & uncertain_mask
n_deferred = ab_uncertain.sum()
print(f"\n  Deferred to quantum: {n_deferred}")

deferred_idx = np.where(ab_uncertain)[0]
for i, test_idx in enumerate(deferred_idx):
    sent = test_sents[test_idx]
    sent_short = " ".join(sent.split()[:MAX_WORDS])
    if sent_short in q_te_sents:
        q_idx = q_te_sents.index(sent_short)
        if q_idx < len(te_pred_classes):
            q_pred = te_pred_classes[q_idx]
            hybrid_preds[test_idx] = label_a if q_pred == 0 else label_b

classical_multi_acc = accuracy_score(test_labels, test_preds)
hybrid_multi_acc = accuracy_score(test_labels, hybrid_preds)

print(f"\n  Classical multi-class: {classical_multi_acc:.1%}")
print(f"  Hybrid multi-class:   {hybrid_multi_acc:.1%}")
print(f"  Change: {(hybrid_multi_acc - classical_multi_acc)*100:+.1f} points")

print("\n" + "=" * 80)
print("SPRINT 4 TASK 4.2 SUMMARY")
print("=" * 80)
print(f"\n  Dataset: CLINC150 ({n_classes} intents)")
print(f"  Confused pair: '{intent_a}' vs '{intent_b}'")
print(f"  Multi-class: Classical {classical_multi_acc:.1%} | Hybrid {hybrid_multi_acc:.1%}")
print(f"  Binary: Classical {classical_bin_acc:.1%} | Quantum {quantum_bin_acc:.1%}")

results = {
    "dataset": "CLINC150",
    "n_classes": n_classes,
    "confused_pair": [intent_a, intent_b],
    "classical_multi": round(classical_multi_acc, 4),
    "hybrid_multi": round(hybrid_multi_acc, 4),
    "classical_binary": round(classical_bin_acc, 4),
    "quantum_binary": round(quantum_bin_acc, 4),
    "quantum_time": round(elapsed, 1),
}
os.makedirs("results", exist_ok=True)
with open("results/sprint4_hybrid_nlu.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to results/sprint4_hybrid_nlu.json")
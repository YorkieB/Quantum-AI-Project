#!/usr/bin/env python3
"""
Sprint 3, Task 3.2: LIAR Dataset — Real Credibility Detection
================================================================
Jarvis Quantum - Module 4 (Credibility Verifier) on real data

LIAR: 12,836 human-rated political statements from PolitiFact.
6 credibility levels: pants-fire, false, barely-true, half-true, mostly-true, true

We simplify to binary: CREDIBLE (true + mostly-true) vs NOT CREDIBLE (rest)
Then test quantum on the hardest pairs.
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
# PART 1: DOWNLOAD LIAR DATASET
# ================================================================
print("Downloading LIAR dataset...")
import urllib.request

os.makedirs("data", exist_ok=True)

base_url = "https://raw.githubusercontent.com/thiagorainmaker77/liar_dataset/master/"
files = {
    "train": "train.tsv",
    "val": "valid.tsv",
    "test": "test.tsv",
}

for split, fname in files.items():
    path = f"data/liar_{split}.tsv"
    if not os.path.exists(path):
        urllib.request.urlretrieve(base_url + fname, path)
        print(f"  Downloaded {split}")
    else:
        print(f"  {split} cached")

# Parse TSV — columns: id, label, statement, subject, speaker, job, state, party,
#   barely_true_count, false_count, half_true_count, mostly_true_count, pants_fire_count, context
def load_liar(path):
    data = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                label = parts[1]
                statement = parts[2]
                # Get speaker and context if available
                speaker = parts[4] if len(parts) > 4 else ""
                context = parts[-1] if len(parts) > 13 else ""
                data.append({
                    "statement": statement,
                    "label": label,
                    "speaker": speaker,
                    "context": context,
                })
    return data

train_raw = load_liar("data/liar_train.tsv")
val_raw = load_liar("data/liar_val.tsv")
test_raw = load_liar("data/liar_test.tsv")

print(f"\n  Raw data: {len(train_raw)} train, {len(val_raw)} val, {len(test_raw)} test")

# Label distribution
all_labels = [d['label'] for d in train_raw]
label_counts = Counter(all_labels)
print(f"\n  Label distribution (train):")
for label, count in sorted(label_counts.items()):
    print(f"    {label:<15} {count:>5} ({count/len(train_raw):.1%})")

# ================================================================
# PART 2: CREATE BINARY TASK
# ================================================================
print("\n  Creating binary classification...")

# Binary: CREDIBLE vs NOT CREDIBLE
credible_labels = {'true', 'mostly-true'}
not_credible_labels = {'false', 'pants-fire'}
# Skip half-true and barely-true (ambiguous middle ground)

def make_binary(data):
    binary = []
    for d in data:
        if d['label'] in credible_labels:
            binary.append((d['statement'], 0, d['speaker']))  # 0 = CREDIBLE
        elif d['label'] in not_credible_labels:
            binary.append((d['statement'], 1, d['speaker']))  # 1 = NOT CREDIBLE
    return binary

train_binary = make_binary(train_raw)
val_binary = make_binary(val_raw)
test_binary = make_binary(test_raw)

print(f"  Binary (excluding ambiguous middle):")
print(f"    Train: {len(train_binary)} ({sum(1 for _,l,_ in train_binary if l==0)} credible, {sum(1 for _,l,_ in train_binary if l==1)} not credible)")
print(f"    Val:   {len(val_binary)}")
print(f"    Test:  {len(test_binary)}")

train_sents = [s for s, l, _ in train_binary]
train_labels = np.array([l for s, l, _ in train_binary])
val_sents = [s for s, l, _ in val_binary]
val_labels = np.array([l for s, l, _ in val_binary])
test_sents = [s for s, l, _ in test_binary]
test_labels = np.array([l for s, l, _ in test_binary])

# Sample statements
print("\n  Sample CREDIBLE statements:")
for s, l, speaker in train_binary[:3]:
    if l == 0:
        print(f"    [{speaker}] \"{s}\"")

print("\n  Sample NOT CREDIBLE statements:")
for s, l, speaker in train_binary:
    if l == 1:
        print(f"    [{speaker}] \"{s}\"")
        break

# ================================================================
# PART 3: CLASSICAL BASELINES
# ================================================================
print("\n" + "=" * 70)
print("CLASSICAL BASELINES — LIAR Binary")
print("=" * 70)

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.preprocessing import StandardScaler
import spacy

nlp = spacy.load("en_core_web_sm")

# TF-IDF
tfidf = TfidfVectorizer(ngram_range=(1, 3), max_features=5000)
X_train_tfidf = tfidf.fit_transform(train_sents)
X_val_tfidf = tfidf.transform(val_sents)
X_test_tfidf = tfidf.transform(test_sents)

# Linguistic features
def extract_features(sentences):
    features = []
    for sent in sentences:
        doc = nlp(sent)
        words = sent.split()
        n_words = len(words)
        n_chars = len(sent)

        # Complexity
        avg_word_len = np.mean([len(w) for w in words]) if words else 0
        n_long_words = sum(1 for w in words if len(w) > 8)

        # Certainty markers
        hedging = ['may', 'might', 'could', 'possibly', 'perhaps',
                    'approximately', 'about', 'around', 'roughly', 'estimated']
        certainty = ['always', 'never', 'every', 'all', 'none', 'definitely',
                     'absolutely', 'certainly', 'guaranteed', 'proven']
        sent_lower = sent.lower()
        n_hedge = sum(1 for w in hedging if w in sent_lower)
        n_certain = sum(1 for w in certainty if w in sent_lower)

        # Numerical claims (specific = more credible?)
        n_numbers = sum(1 for t in doc if t.like_num)
        has_percent = 1 if '%' in sent or 'percent' in sent_lower else 0

        # Named entities
        n_entities = len(doc.ents)
        n_person = sum(1 for e in doc.ents if e.label_ == 'PERSON')
        n_org = sum(1 for e in doc.ents if e.label_ == 'ORG')

        # Superlatives and comparatives
        n_superlative = sum(1 for t in doc if t.tag_ == 'JJS' or t.tag_ == 'RBS')
        n_comparative = sum(1 for t in doc if t.tag_ == 'JJR' or t.tag_ == 'RBR')

        # Quotation marks (citing others)
        n_quotes = sent.count('"') + sent.count("'")

        features.append([
            n_words, n_chars, avg_word_len, n_long_words,
            n_hedge, n_certain, n_numbers, has_percent,
            n_entities, n_person, n_org,
            n_superlative, n_comparative, n_quotes,
        ])
    return np.array(features)

feature_names = [
    'n_words', 'n_chars', 'avg_word_len', 'n_long_words',
    'n_hedge', 'n_certain', 'n_numbers', 'has_percent',
    'n_entities', 'n_person', 'n_org',
    'n_superlative', 'n_comparative', 'n_quotes',
]

print("\n  Extracting linguistic features...")
X_train_feat = extract_features(train_sents)
X_val_feat = extract_features(val_sents)
X_test_feat = extract_features(test_sents)

scaler = StandardScaler()
X_train_feat_s = scaler.fit_transform(X_train_feat)
X_val_feat_s = scaler.transform(X_val_feat)
X_test_feat_s = scaler.transform(X_test_feat)

# spaCy vectors
print("  Extracting spaCy vectors...")
X_train_spacy = np.array([nlp(s).vector for s in train_sents])
X_val_spacy = np.array([nlp(s).vector for s in val_sents])
X_test_spacy = np.array([nlp(s).vector for s in test_sents])

# Combined
from scipy.sparse import hstack
X_train_combo = hstack([X_train_tfidf, X_train_feat_s])
X_val_combo = hstack([X_val_tfidf, X_val_feat_s])
X_test_combo = hstack([X_test_tfidf, X_test_feat_s])

classical_models = {
    "TF-IDF + LogReg": (LogisticRegression(max_iter=2000, random_state=42),
                        X_train_tfidf, X_val_tfidf, X_test_tfidf),
    "TF-IDF + SVM": (SVC(kernel='linear', probability=True, random_state=42),
                     X_train_tfidf, X_val_tfidf, X_test_tfidf),
    "Linguistic + LogReg": (LogisticRegression(max_iter=2000, random_state=42),
                            X_train_feat_s, X_val_feat_s, X_test_feat_s),
    "Linguistic + RF": (RandomForestClassifier(n_estimators=200, random_state=42),
                        X_train_feat_s, X_val_feat_s, X_test_feat_s),
    "Combined + LogReg": (LogisticRegression(max_iter=2000, random_state=42),
                          X_train_combo, X_val_combo, X_test_combo),
    "Combined + GBM": (GradientBoostingClassifier(n_estimators=200, random_state=42),
                       X_train_combo, X_val_combo, X_test_combo),
    "spaCy + LogReg": (LogisticRegression(max_iter=2000, random_state=42),
                       X_train_spacy, X_val_spacy, X_test_spacy),
    "spaCy + SVM": (SVC(kernel='rbf', probability=True, random_state=42),
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
    print(f"    Train: {train_acc:.1%}  Val: {val_acc:.1%}  Test: {test_acc:.1%}  F1: {test_f1:.3f}")

# ================================================================
# PART 4: QUANTUM CREDIBILITY MODEL
# ================================================================
print("\n" + "=" * 70)
print("QUANTUM CREDIBILITY MODEL — LIAR Binary")
print("=" * 70)

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

# Quantum subset — balanced 80 train, truncated
MAX_WORDS = 10
MAX_Q_TRAIN = 80

idx_0 = [i for i, l in enumerate(train_labels) if l == 0]
idx_1 = [i for i, l in enumerate(train_labels) if l == 1]
per_class = MAX_Q_TRAIN // 2
selected = sorted(
    list(np.random.choice(idx_0, min(per_class, len(idx_0)), replace=False)) +
    list(np.random.choice(idx_1, min(per_class, len(idx_1)), replace=False))
)

q_train_sents = [" ".join(train_sents[i].split()[:MAX_WORDS]) for i in selected]
q_train_labels = np.array([train_labels[i] for i in selected])
q_val_sents = [" ".join(s.split()[:MAX_WORDS]) for s in val_sents]
q_val_labels = val_labels
q_test_sents = [" ".join(s.split()[:MAX_WORDS]) for s in test_sents]
q_test_labels = test_labels

print(f"\n  Quantum: {len(q_train_sents)} train (max {MAX_WORDS} words)")
print(f"  Full val: {len(q_val_sents)} | Full test: {len(q_test_sents)}")

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
q_va_diag, q_va_lab = parse_clean(q_val_sents, q_val_labels)
q_te_diag, q_te_lab = parse_clean(q_test_sents, q_test_labels)

# Limit val/test for speed
MAX_EVAL = 100
if len(q_va_diag) > MAX_EVAL:
    va_idx = sorted(np.random.choice(len(q_va_diag), MAX_EVAL, replace=False))
    q_va_diag = [q_va_diag[i] for i in va_idx]
    q_va_lab = q_va_lab[va_idx]

if len(q_te_diag) > MAX_EVAL:
    te_idx = sorted(np.random.choice(len(q_te_diag), MAX_EVAL, replace=False))
    q_te_diag = [q_te_diag[i] for i in te_idx]
    q_te_lab = q_te_lab[te_idx]

print(f"  After parse + subsample: {len(q_tr_diag)} train, {len(q_va_diag)} val, {len(q_te_diag)} test")

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

print(f"\n  Quantum: Train: {q_train_acc:.1%}  Val: {q_val_acc:.1%}  Test: {q_test_acc:.1%}  Conf: {q_conf:.3f}  Time: {elapsed:.0f}s")

# ================================================================
# FINAL SUMMARY
# ================================================================
print("\n\n" + "=" * 80)
print("LIAR CREDIBILITY RESULTS — CREDIBLE vs NOT CREDIBLE")
print("=" * 80)

print(f"\n  {'Method':<24} {'Train':<8} {'Val':<8} {'Test':<8} {'F1':<8}")
print("  " + "-" * 56)
for r in classical_results:
    print(f"  {r['method']:<24} {r['train_acc']:.0%}     {r['val_acc']:.0%}     {r['test_acc']:.0%}     {r['test_f1']:.3f}")
print("  " + "-" * 56)
print(f"  {'Quantum N=1':<24} {q_train_acc:.0%}     {q_val_acc:.0%}     {q_test_acc:.0%}     -")

# Check: what's the majority class baseline?
majority = max(Counter(test_labels).values()) / len(test_labels)
print(f"\n  Majority class baseline: {majority:.1%}")
print(f"  (If a model scores near this, it's just guessing the majority class)")

# Save
os.makedirs("results", exist_ok=True)
all_results = {
    "dataset": "LIAR",
    "task": "Binary: CREDIBLE (true+mostly-true) vs NOT CREDIBLE (false+pants-fire)",
    "classical": classical_results,
    "quantum": {
        "train_acc": round(q_train_acc, 4),
        "val_acc": round(q_val_acc, 4),
        "test_acc": round(q_test_acc, 4),
        "confidence": round(q_conf, 4),
        "time": round(elapsed, 1),
        "n_params": len(model.symbols),
        "train_size": len(tr_circuits),
    },
    "majority_baseline": round(majority, 4),
}
with open("results/sprint3_liar.json", "w") as f:
    json.dump(all_results, f, indent=2)

print(f"\nResults saved to results/sprint3_liar.json")
print("\nTask 3.2 Complete - LIAR Credibility Benchmark")
print("Next: Task 3.3 - Analysis and quantum advantage roadmap")
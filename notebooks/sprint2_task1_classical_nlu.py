#!/usr/bin/env python3
"""
Sprint 2, Task 2.1: Classical NLU Baseline
============================================
Jarvis Quantum - Classical baseline for Module 1 (NLU)

Compares multiple classical approaches against our quantum results:
  1. TF-IDF + Logistic Regression
  2. TF-IDF + SVM (linear kernel)
  3. TF-IDF + SVM (RBF kernel)
  4. spaCy word vectors + Logistic Regression
  5. spaCy word vectors + SVM

Quantum benchmark to beat:
  Tutorial 3 (NOUN=3): 100% train, 100% test, 0.912 confidence
"""

import numpy as np
import json
import os
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import cross_val_score
import spacy

print("Loading spaCy model...")
nlp = spacy.load("en_core_web_sm")
print("Ready.\n")

# === SAME DATA AS QUANTUM TUTORIALS ===
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
train_labels = np.array([0,0,0,0,0,0,0,0, 1,1,1,1,1,1,1,1])

test_sentences = [
    "find reviews for new phones",
    "search for holiday deals online",
    "look up football scores today",
    "turn on the kitchen lights",
    "set a reminder for the meeting",
    "play some relaxing music now",
]
test_labels = np.array([0,0,0, 1,1,1])

# === EXPANDED TEST SET ===
# Extra unseen sentences to stress-test generalisation
hard_test_sentences = [
    # SEARCH - trickier phrasing
    "what is the capital of France",
    "how tall is mount Everest",
    "show me pictures of cats",
    "who won the world cup",
    "tell me about quantum computing",
    "what time does the shop close",
    "where is the nearest hospital",
    "how do you make pancakes",
    # ACTION - trickier phrasing
    "remind me to call mum at six",
    "switch off all the lights",
    "pause the music for a moment",
    "read my latest email out loud",
    "start the coffee machine now",
    "cancel my morning alarm please",
    "dim the living room lights",
    "skip to the next song",
]
hard_test_labels = np.array([0,0,0,0,0,0,0,0, 1,1,1,1,1,1,1,1])

intent_names = {0: "SEARCH", 1: "ACTION"}

# === METHOD 1-3: TF-IDF FEATURES ===
print("=" * 60)
print("TF-IDF FEATURES")
print("=" * 60)

tfidf = TfidfVectorizer(
    ngram_range=(1, 2),
    max_features=500,
    stop_words=None,  # keep all words - small dataset
)

X_train_tfidf = tfidf.fit_transform(train_sentences)
X_test_tfidf = tfidf.transform(test_sentences)
X_hard_tfidf = tfidf.transform(hard_test_sentences)

tfidf_classifiers = {
    "TF-IDF + LogReg": LogisticRegression(max_iter=1000, random_state=42),
    "TF-IDF + SVM-linear": SVC(kernel='linear', probability=True, random_state=42),
    "TF-IDF + SVM-rbf": SVC(kernel='rbf', probability=True, random_state=42),
}

results_all = []

for name, clf in tfidf_classifiers.items():
    t_start = time.time()
    clf.fit(X_train_tfidf, train_labels)
    elapsed = time.time() - t_start

    train_acc = accuracy_score(train_labels, clf.predict(X_train_tfidf))
    test_acc = accuracy_score(test_labels, clf.predict(X_test_tfidf))
    hard_acc = accuracy_score(hard_test_labels, clf.predict(X_hard_tfidf))

    # Confidence = average max probability
    test_probs = clf.predict_proba(X_test_tfidf)
    avg_conf = test_probs.max(axis=1).mean()

    # Cross-validation on training set
    cv_scores = cross_val_score(clf, X_train_tfidf, train_labels, cv=4, scoring='accuracy')

    result = {
        "method": name,
        "train_acc": round(train_acc, 4),
        "test_acc": round(test_acc, 4),
        "hard_test_acc": round(hard_acc, 4),
        "avg_confidence": round(avg_conf, 4),
        "cv_mean": round(cv_scores.mean(), 4),
        "cv_std": round(cv_scores.std(), 4),
        "time_seconds": round(elapsed, 4),
    }
    results_all.append(result)

    print(f"\n  {name}")
    print(f"    Train: {train_acc:.1%} | Test: {test_acc:.1%} | Hard: {hard_acc:.1%}")
    print(f"    Confidence: {avg_conf:.3f} | CV: {cv_scores.mean():.1%} +/- {cv_scores.std():.1%}")
    print(f"    Time: {elapsed*1000:.1f}ms")

# === METHOD 4-5: SPACY WORD VECTORS ===
print("\n" + "=" * 60)
print("SPACY WORD VECTOR FEATURES")
print("=" * 60)

def get_doc_vectors(sentences):
    """Get averaged word vectors from spaCy."""
    vectors = []
    for sent in sentences:
        doc = nlp(sent)
        vectors.append(doc.vector)
    return np.array(vectors)

X_train_spacy = get_doc_vectors(train_sentences)
X_test_spacy = get_doc_vectors(test_sentences)
X_hard_spacy = get_doc_vectors(hard_test_sentences)

print(f"  Vector dimension: {X_train_spacy.shape[1]}")

spacy_classifiers = {
    "spaCy + LogReg": LogisticRegression(max_iter=1000, random_state=42),
    "spaCy + SVM-rbf": SVC(kernel='rbf', probability=True, random_state=42),
}

for name, clf in spacy_classifiers.items():
    t_start = time.time()
    clf.fit(X_train_spacy, train_labels)
    elapsed = time.time() - t_start

    train_acc = accuracy_score(train_labels, clf.predict(X_train_spacy))
    test_acc = accuracy_score(test_labels, clf.predict(X_test_spacy))
    hard_acc = accuracy_score(hard_test_labels, clf.predict(X_hard_spacy))

    test_probs = clf.predict_proba(X_test_spacy)
    avg_conf = test_probs.max(axis=1).mean()

    cv_scores = cross_val_score(clf, X_train_spacy, train_labels, cv=4, scoring='accuracy')

    result = {
        "method": name,
        "train_acc": round(train_acc, 4),
        "test_acc": round(test_acc, 4),
        "hard_test_acc": round(hard_acc, 4),
        "avg_confidence": round(avg_conf, 4),
        "cv_mean": round(cv_scores.mean(), 4),
        "cv_std": round(cv_scores.std(), 4),
        "time_seconds": round(elapsed, 4),
    }
    results_all.append(result)

    print(f"\n  {name}")
    print(f"    Train: {train_acc:.1%} | Test: {test_acc:.1%} | Hard: {hard_acc:.1%}")
    print(f"    Confidence: {avg_conf:.3f} | CV: {cv_scores.mean():.1%} +/- {cv_scores.std():.1%}")
    print(f"    Time: {elapsed*1000:.1f}ms")

# === COMPARISON TABLE ===
print("\n\n" + "=" * 80)
print("CLASSICAL vs QUANTUM COMPARISON")
print("=" * 80)

# Add quantum results from our tutorials
quantum_results = [
    {
        "method": "Quantum N=1 (Tutorial 3)",
        "train_acc": 1.0,
        "test_acc": 1.0,
        "hard_test_acc": "N/A",
        "avg_confidence": 0.887,
        "cv_mean": "N/A",
        "cv_std": "N/A",
        "time_seconds": 12.6,
    },
    {
        "method": "Quantum N=3 (best)",
        "train_acc": 1.0,
        "test_acc": 1.0,
        "hard_test_acc": "N/A",
        "avg_confidence": 0.912,
        "cv_mean": "N/A",
        "cv_std": "N/A",
        "time_seconds": 12.8,
    },
]

all_results = results_all + quantum_results

print(f"\n{'Method':<28} {'Train':<8} {'Test':<8} {'Hard':<8} {'Conf':<8} {'CV':<12} {'Time':<10}")
print("-" * 80)
for r in all_results:
    hard = f"{r['hard_test_acc']:.0%}" if isinstance(r['hard_test_acc'], float) else r['hard_test_acc']
    cv = f"{r['cv_mean']:.0%}+/-{r['cv_std']:.0%}" if isinstance(r['cv_mean'], float) else r['cv_mean']
    t = f"{r['time_seconds']:.1f}s" if r['time_seconds'] > 1 else f"{r['time_seconds']*1000:.0f}ms"
    print(f"  {r['method']:<26} {r['train_acc']:.0%}     {r['test_acc']:.0%}     "
          f"{hard:<8} {r['avg_confidence']:.3f}   {cv:<12} {t}")

# === DETAILED HARD TEST RESULTS ===
print("\n\nHARD TEST SET - Detailed Results (best classical model):")
print("-" * 60)

# Find best classical model on hard test
best_classical = max(results_all, key=lambda r: r['hard_test_acc'])
print(f"Best classical: {best_classical['method']} ({best_classical['hard_test_acc']:.0%})\n")

# Refit and predict with best model for details
if "TF-IDF" in best_classical['method']:
    if "LogReg" in best_classical['method']:
        best_clf = LogisticRegression(max_iter=1000, random_state=42)
    elif "linear" in best_classical['method']:
        best_clf = SVC(kernel='linear', probability=True, random_state=42)
    else:
        best_clf = SVC(kernel='rbf', probability=True, random_state=42)
    best_clf.fit(X_train_tfidf, train_labels)
    hard_preds = best_clf.predict(X_hard_tfidf)
    hard_probs = best_clf.predict_proba(X_hard_tfidf)
else:
    if "LogReg" in best_classical['method']:
        best_clf = LogisticRegression(max_iter=1000, random_state=42)
    else:
        best_clf = SVC(kernel='rbf', probability=True, random_state=42)
    best_clf.fit(X_train_spacy, train_labels)
    hard_preds = best_clf.predict(X_hard_spacy)
    hard_probs = best_clf.predict_proba(X_hard_spacy)

for i, (sent, pred, true_l) in enumerate(zip(hard_test_sentences, hard_preds, hard_test_labels)):
    status = "CORRECT" if pred == true_l else "WRONG"
    conf = hard_probs[i].max()
    print(f"  [{status}] \"{sent}\"")
    print(f"     Pred: {intent_names[pred]} | True: {intent_names[true_l]} | Conf: {conf:.3f}")

# === SAVE ===
os.makedirs("results", exist_ok=True)
with open("results/sprint2_classical_nlu.json", "w") as f:
    json.dump(all_results, f, indent=2, default=str)

print(f"\nResults saved to results/sprint2_classical_nlu.json")
print("\nTask 2.1 Complete - Classical NLU Baselines")
print("Next: Task 2.2 - Classical credibility classifier")
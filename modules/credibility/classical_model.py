#!/usr/bin/env python3
"""
Module 4: Credibility Verifier — Classical Model
==================================================
Trains and saves the TF-IDF + LogReg model for fast pre-filtering.
Run once to generate saved models, then the service loads them.
"""

import pickle
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import spacy

def load_liar(path):
    data = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                data.append({"statement": parts[2], "label": parts[1]})
    return data

def train_and_save():
    print("Training classical credibility model...")

    # Load LIAR
    train_raw = load_liar("../../data/liar_train.tsv")
    val_raw = load_liar("../../data/liar_val.tsv")
    test_raw = load_liar("../../data/liar_test.tsv")

    credible = {'true', 'mostly-true'}
    not_credible = {'false', 'pants-fire'}

    def make_binary(data):
        return [(d['statement'], 0 if d['label'] in credible else 1)
                for d in data if d['label'] in credible | not_credible]

    train = make_binary(train_raw)
    val = make_binary(val_raw)
    test = make_binary(test_raw)

    train_sents = [s for s, l in train]
    train_labels = np.array([l for s, l in train])
    val_sents = [s for s, l in val]
    val_labels = np.array([l for s, l in val])
    test_sents = [s for s, l in test]
    test_labels = np.array([l for s, l in test])

    # TF-IDF
    tfidf = TfidfVectorizer(ngram_range=(1, 3), max_features=5000)
    X_train = tfidf.fit_transform(train_sents)
    X_val = tfidf.transform(val_sents)
    X_test = tfidf.transform(test_sents)

    # LogReg
    clf = LogisticRegression(max_iter=2000, random_state=42)
    clf.fit(X_train, train_labels)

    train_acc = accuracy_score(train_labels, clf.predict(X_train))
    val_acc = accuracy_score(val_labels, clf.predict(X_val))
    test_acc = accuracy_score(test_labels, clf.predict(X_test))

    print(f"  Train: {train_acc:.1%}  Val: {val_acc:.1%}  Test: {test_acc:.1%}")

    # Save
    os.makedirs("models", exist_ok=True)
    with open("models/tfidf_vectorizer.pkl", "wb") as f:
        pickle.dump(tfidf, f)
    with open("models/classical_clf.pkl", "wb") as f:
        pickle.dump(clf, f)

    print("  Saved: models/tfidf_vectorizer.pkl, models/classical_clf.pkl")
    return tfidf, clf


class ClassicalCredibilityModel:
    """Loads and serves the pre-trained classical model."""

    def __init__(self, model_dir="models"):
        with open(os.path.join(model_dir, "tfidf_vectorizer.pkl"), "rb") as f:
            self.tfidf = pickle.load(f)
        with open(os.path.join(model_dir, "classical_clf.pkl"), "rb") as f:
            self.clf = pickle.load(f)

    def predict(self, statement: str) -> dict:
        """Predict credibility of a single statement."""
        X = self.tfidf.transform([statement])
        proba = self.clf.predict_proba(X)[0]
        pred_class = int(np.argmax(proba))
        confidence = float(proba.max())

        return {
            "prediction": pred_class,
            "label": "CREDIBLE" if pred_class == 0 else "NOT_CREDIBLE",
            "confidence": round(confidence, 4),
            "probabilities": {
                "credible": round(float(proba[0]), 4),
                "not_credible": round(float(proba[1]), 4),
            }
        }

    def predict_batch(self, statements: list) -> list:
        """Predict credibility for multiple statements."""
        X = self.tfidf.transform(statements)
        probas = self.clf.predict_proba(X)
        results = []
        for i, proba in enumerate(probas):
            pred_class = int(np.argmax(proba))
            results.append({
                "prediction": pred_class,
                "label": "CREDIBLE" if pred_class == 0 else "NOT_CREDIBLE",
                "confidence": round(float(proba.max()), 4),
                "probabilities": {
                    "credible": round(float(proba[0]), 4),
                    "not_credible": round(float(proba[1]), 4),
                }
            })
        return results


if __name__ == "__main__":
    train_and_save()
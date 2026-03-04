#!/usr/bin/env python3
"""
Module 4: Credibility Verifier — Quantum Model
================================================
Trains and saves the DisCoCat quantum model for hard cases.
Run once to generate saved circuits + weights.
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import os
import pickle
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


def load_liar(path):
    data = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                data.append({"statement": parts[2], "label": parts[1]})
    return data


def train_and_save(max_words=10, max_train=80, epochs=100):
    print("Training quantum credibility model...")

    # Load LIAR
    train_raw = load_liar("../../data/liar_train.tsv")
    val_raw = load_liar("../../data/liar_val.tsv")

    credible = {'true', 'mostly-true'}
    not_credible = {'false', 'pants-fire'}

    def make_binary(data):
        return [(d['statement'], 0 if d['label'] in credible else 1)
                for d in data if d['label'] in credible | not_credible]

    train = make_binary(train_raw)
    val = make_binary(val_raw)

    train_sents = [s for s, l in train]
    train_labels = [l for s, l in train]
    val_sents = [s for s, l in val]
    val_labels = [l for s, l in val]

    # Balanced subsample for quantum
    np.random.seed(42)
    idx_0 = [i for i, l in enumerate(train_labels) if l == 0]
    idx_1 = [i for i, l in enumerate(train_labels) if l == 1]
    per_class = max_train // 2
    selected = sorted(
        list(np.random.choice(idx_0, min(per_class, len(idx_0)), replace=False)) +
        list(np.random.choice(idx_1, min(per_class, len(idx_1)), replace=False))
    )

    q_train_sents = [" ".join(train_sents[i].split()[:max_words]) for i in selected]
    q_train_labels = [train_labels[i] for i in selected]

    # Val subset
    max_val = 60
    val_idx = sorted(np.random.choice(len(val_sents), min(max_val, len(val_sents)), replace=False))
    q_val_sents = [" ".join(val_sents[i].split()[:max_words]) for i in val_idx]
    q_val_labels = [val_labels[i] for i in val_idx]

    print(f"  Train: {len(q_train_sents)} | Val: {len(q_val_sents)}")

    # Parse
    reader = stairs_reader
    remove_cups = RemoveCupsRewriter()

    def parse_clean(sentences, labels):
        raw = reader.sentences2diagrams(sentences)
        pairs = [(d, l) for d, l in zip(raw, labels) if d is not None]
        return [remove_cups(p[0]) for p in pairs], [p[1] for p in pairs]

    tr_diag, tr_lab = parse_clean(q_train_sents, q_train_labels)
    va_diag, va_lab = parse_clean(q_val_sents, q_val_labels)

    print(f"  Parsed: {len(tr_diag)} train, {len(va_diag)} val")

    # Ansatz
    ansatz = IQPAnsatz(
        {AtomicType.NOUN: 1, AtomicType.SENTENCE: 1},
        n_layers=2,
        n_single_qubit_params=3,
    )

    tr_circuits = [ansatz(d) for d in tr_diag]
    va_circuits = [ansatz(d) for d in va_diag]

    all_circuits = tr_circuits + va_circuits
    model = PytorchQuantumModel.from_diagrams(all_circuits)
    model.initialise_weights()

    print(f"  Parameters: {len(model.symbols)}")

    tr_lab_2d = np.array([[1-l, l] for l in tr_lab], dtype=np.float64)
    va_lab_2d = np.array([[1-l, l] for l in va_lab], dtype=np.float64)

    def loss_fn(y_pred, y_true):
        return torch.nn.functional.mse_loss(y_pred, y_true.to(y_pred.dtype))

    def accuracy_fn(y_pred, y_true):
        return (torch.argmax(y_pred, dim=1) == torch.argmax(y_true.to(y_pred.dtype), dim=1)).sum().item() / len(y_true)

    tr_dataset = Dataset(tr_circuits, tr_lab_2d, batch_size=8)
    va_dataset = Dataset(va_circuits, va_lab_2d, batch_size=8)

    trainer = PytorchTrainer(
        model=model,
        loss_function=loss_fn,
        optimizer=torch.optim.Adam,
        learning_rate=0.05,
        epochs=epochs,
        evaluate_functions={"accuracy": accuracy_fn},
        evaluate_on_train=True,
        verbose='text',
        seed=42,
    )

    print(f"  Training ({epochs} epochs)...")
    trainer.fit(tr_dataset, va_dataset)

    # Save model state and ansatz config
    os.makedirs("models", exist_ok=True)

    # Save the trained model weights
    torch.save({
        'model_weights': [w.data for w in model.weights],
        'model_symbols': model.symbols,
    }, "models/quantum_model_weights.pt")

    # Save ansatz config for reconstruction
    config = {
        'noun_qubits': 1,
        'sentence_qubits': 1,
        'n_layers': 2,
        'n_single_qubit_params': 3,
        'max_words': max_words,
    }
    with open("models/quantum_config.pkl", "wb") as f:
        pickle.dump(config, f)

    print("  Saved: models/quantum_model_weights.pt, models/quantum_config.pkl")
    return model, ansatz


class QuantumCredibilityModel:
    """Loads and serves the pre-trained quantum model."""

    def __init__(self, model_dir="models"):
        with open(os.path.join(model_dir, "quantum_config.pkl"), "rb") as f:
            self.config = pickle.load(f)

        self.reader = stairs_reader
        self.remove_cups = RemoveCupsRewriter()
        self.ansatz = IQPAnsatz(
            {AtomicType.NOUN: self.config['noun_qubits'],
             AtomicType.SENTENCE: self.config['sentence_qubits']},
            n_layers=self.config['n_layers'],
            n_single_qubit_params=self.config['n_single_qubit_params'],
        )
        self.max_words = self.config['max_words']

        # We need to rebuild the model from a diagram to load weights
        # This is stored alongside the weights
        self.weights_path = os.path.join(model_dir, "quantum_model_weights.pt")
        self._model = None

    def _ensure_model(self, sentences):
        """Build model from diagrams and load saved weights."""
        truncated = [" ".join(s.split()[:self.max_words]) for s in sentences]
        raw = self.reader.sentences2diagrams(truncated)
        diagrams = []
        valid_idx = []
        for i, d in enumerate(raw):
            if d is not None:
                diagrams.append(self.remove_cups(d))
                valid_idx.append(i)

        circuits = [self.ansatz(d) for d in diagrams]
        model = PytorchQuantumModel.from_diagrams(circuits)
        model.initialise_weights()

        # Load saved weights (match by symbol)
        saved = torch.load(self.weights_path, weights_only=False)
        saved_symbols = saved['model_symbols']
        saved_weights = saved['model_weights']
        symbol_to_weight = dict(zip(saved_symbols, saved_weights))

        for i, sym in enumerate(model.symbols):
            if sym in symbol_to_weight:
                model.weights[i].data = symbol_to_weight[sym]

        return model, circuits, valid_idx

    def predict(self, statement: str) -> dict:
        """Predict credibility of a single statement."""
        return self.predict_batch([statement])[0]

    def predict_batch(self, statements: list) -> list:
        """Predict credibility for multiple statements."""
        model, circuits, valid_idx = self._ensure_model(statements)

        if not circuits:
            return [{"prediction": -1, "label": "PARSE_FAILED",
                     "confidence": 0.0} for _ in statements]

        with torch.no_grad():
            preds = model(circuits)

        results = [None] * len(statements)
        for i, vi in enumerate(valid_idx):
            proba = preds[i].detach().numpy()
            pred_class = int(np.argmax(proba))
            results[vi] = {
                "prediction": pred_class,
                "label": "CREDIBLE" if pred_class == 0 else "NOT_CREDIBLE",
                "confidence": round(float(proba.max()), 4),
                "probabilities": {
                    "credible": round(float(proba[0]), 4),
                    "not_credible": round(float(proba[1]), 4),
                }
            }

        # Fill failed parses
        for i in range(len(results)):
            if results[i] is None:
                results[i] = {
                    "prediction": -1,
                    "label": "PARSE_FAILED",
                    "confidence": 0.0,
                }

        return results


if __name__ == "__main__":
    train_and_save()
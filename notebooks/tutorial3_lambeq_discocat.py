#!/usr/bin/env python3
"""
Tutorial 3: lambeq DisCoCat Quantum NLU
========================================
Jarvis Quantum - Sprint 1, Task 1.5

Pipeline:
  Sentence -> Reader -> String Diagram -> RemoveCups -> IQPAnsatz -> Circuit
  -> PytorchQuantumModel -> PytorchTrainer -> Intent Classification
"""

import warnings
warnings.filterwarnings('ignore')

import lambeq
from lambeq import (
    BobcatParser,
    RemoveCupsRewriter,
    IQPAnsatz,
    AtomicType,
    PytorchTrainer,
    PytorchQuantumModel,
    Dataset,
)
import torch
import numpy as np
import json
import os

print(f"lambeq version: {lambeq.__version__}")
print("All lambeq components imported")

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

print(f"Training: {len(train_sentences)} sentences | Test: {len(test_sentences)} sentences")

# === PARSE ===
print("\nParsing sentences into string diagrams...")
try:
    print("  Attempting BobcatParser...")
    reader = BobcatParser(verbose='suppress')
    test_parse = reader.sentences2diagrams(["test sentence"])
    if test_parse[0] is not None:
        print("  BobcatParser loaded")
        parser_name = "BobcatParser"
    else:
        raise RuntimeError("BobcatParser returned None")
except Exception as e:
    print(f"  BobcatParser unavailable: {type(e).__name__}")
    print("  Falling back to StairsReader...")
    from lambeq import stairs_reader
    reader = stairs_reader
    parser_name = "StairsReader"
    print("  StairsReader loaded")

raw_train_diagrams = reader.sentences2diagrams(train_sentences)
raw_test_diagrams = reader.sentences2diagrams(test_sentences)

# Remove failed parses
train_pairs = [(d, l) for d, l in zip(raw_train_diagrams, train_labels) if d is not None]
test_pairs = [(d, l) for d, l in zip(raw_test_diagrams, test_labels) if d is not None]
raw_train_diagrams = [p[0] for p in train_pairs]
train_labels = [p[1] for p in train_pairs]
raw_test_diagrams = [p[0] for p in test_pairs]
test_labels = [p[1] for p in test_pairs]
print(f"  Parsed: {len(raw_train_diagrams)} train, {len(raw_test_diagrams)} test with {parser_name}")

# === SIMPLIFY ===
print("\nSimplifying diagrams (removing cups)...")
remove_cups = RemoveCupsRewriter()
train_diagrams = [remove_cups(d) for d in raw_train_diagrams]
test_diagrams = [remove_cups(d) for d in raw_test_diagrams]

# === ANSATZ ===
print("\nApplying IQPAnsatz...")
ansatz = IQPAnsatz(
    {AtomicType.NOUN: 1, AtomicType.SENTENCE: 1},
    n_layers=2,
    n_single_qubit_params=3,
)
train_circuits = [ansatz(d) for d in train_diagrams]
test_circuits = [ansatz(d) for d in test_diagrams]
print(f"  Circuits: {len(train_circuits)} train, {len(test_circuits)} test")

# === MODEL ===
# Labels: [1,0] = SEARCH, [0,1] = ACTION
# float64 to match PytorchQuantumModel internal dtype
train_labels_2d = np.array([[1-l, l] for l in train_labels], dtype=np.float64)
test_labels_2d = np.array([[1-l, l] for l in test_labels], dtype=np.float64)

print("\nCreating PytorchQuantumModel...")
all_circuits = train_circuits + test_circuits
model = PytorchQuantumModel.from_diagrams(all_circuits)
model.initialise_weights()
print(f"  Trainable symbols: {len(model.symbols)}")

train_dataset = Dataset(train_circuits, train_labels_2d, batch_size=4)
test_dataset = Dataset(test_circuits, test_labels_2d, batch_size=4)

# Cast y_true to match model output dtype (Double) — lambeq Dataset
# may convert labels back to Float internally, so we force alignment
def loss_fn(y_pred, y_true):
    return torch.nn.functional.mse_loss(y_pred, y_true.to(y_pred.dtype))

def accuracy_fn(y_pred, y_true):
    return (torch.argmax(y_pred, dim=1) == torch.argmax(y_true.to(y_pred.dtype), dim=1)).sum().item() / len(y_true)

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

# === TRAIN ===
print("\nTraining Quantum NLU Model")
print("=" * 50)
print(f"  Sentences: {len(train_circuits)} train, {len(test_circuits)} test")
print(f"  Epochs: 50 | Optimiser: Adam (lr=0.1) | Loss: MSE")
print("=" * 50)
trainer.fit(train_dataset, test_dataset)

# === EVALUATE ===
train_preds = model(train_circuits)
test_preds = model(test_circuits)

train_pred_classes = torch.argmax(train_preds, dim=1)
test_pred_classes = torch.argmax(test_preds, dim=1)
train_true_classes = torch.tensor(np.argmax(train_labels_2d, axis=1))
test_true_classes = torch.tensor(np.argmax(test_labels_2d, axis=1))

train_acc = (train_pred_classes == train_true_classes).float().mean().item()
test_acc = (test_pred_classes == test_true_classes).float().mean().item()

print("\n" + "=" * 50)
print("QUANTUM NLU RESULTS")
print("=" * 50)
print(f"  Train Accuracy: {train_acc:.1%}")
print(f"  Test Accuracy:  {test_acc:.1%}")

# Detailed predictions
print("\nDetailed Test Predictions:")
print("-" * 50)
intent_names = {0: "SEARCH", 1: "ACTION"}
for i, (sent, pred, true_label) in enumerate(zip(test_sentences, test_pred_classes, test_true_classes)):
    pred_l = pred.item()
    true_l = true_label.item()
    status = "CORRECT" if pred_l == true_l else "WRONG"
    probs = test_preds[i].detach().numpy()
    print(f"  [{status}] \"{sent}\"")
    print(f"     Pred: {intent_names[pred_l]} | True: {intent_names[true_l]} | Probs: [{probs[0]:.3f}, {probs[1]:.3f}]")

# Save results
os.makedirs("results", exist_ok=True)
results = {
    "parser": parser_name,
    "ansatz": "IQPAnsatz(n_layers=2, n_single_qubit_params=3)",
    "model": "PytorchQuantumModel",
    "n_symbols": len(model.symbols),
    "train_sentences": len(train_circuits),
    "test_sentences": len(test_circuits),
    "epochs": 50,
    "train_accuracy": train_acc,
    "test_accuracy": test_acc,
}
with open("results/tutorial3_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to results/tutorial3_results.json")
print("\nTutorial 3 Complete - DisCoCat Quantum NLU")
print(f"  Parser: {parser_name} | Model: PytorchQuantumModel ({len(model.symbols)} params)")
print(f"  Train: {train_acc:.1%} | Test: {test_acc:.1%}")
print(f"  Next: Sprint 2 - Classical baselines with spaCy + sklearn")
# %% [markdown]
# # Tutorial 2: Qiskit VQC — Training on a Real Dataset
# 
# **Jarvis Quantum — Sprint 1, Task 1.4**
# 
# This tutorial builds the foundation for Module 4 (Credibility Verifier).
# We train a Variational Quantum Classifier (VQC) using Qiskit on the Iris dataset,
# which is a real-world classification benchmark.
#
# Architecture matches the roadmap:
# - ZZFeatureMap for data encoding (Sprint 6, Task 2.5)
# - RealAmplitudes ansatz for trainable layers (Sprint 6, Task 2.6)
# - COBYLA optimiser (Sprint 6, Task 2.7)
#
# Based on: https://qiskit-community.github.io/qiskit-machine-learning/tutorials/02a_training_a_quantum_model_on_a_real_dataset.html

# %% [markdown]
# ## Part 1: Load and Prepare the Iris Dataset
#
# The Iris dataset has 4 features and 3 classes. We'll use 2 features and 
# 2 classes to keep the quantum circuit small (2 qubits), then scale up.

# %%
import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.svm import SVC
from sklearn.metrics import classification_report, accuracy_score

print("Loading Iris dataset...")
iris = load_iris()
X = iris.data
y = iris.target

# Use only classes 0 and 1 (linearly separable first, then we'll try harder ones)
# Use features 0 and 2 (sepal length and petal length) for visualisation
mask = y < 2
X_binary = X[mask][:, [0, 2]]  # 2 features = 2 qubits
y_binary = y[mask]

# Scale features to [0, 1] range for quantum encoding
scaler = MinMaxScaler(feature_range=(0, np.pi))
X_scaled = scaler.fit_transform(X_binary)

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y_binary, test_size=0.3, random_state=42, stratify=y_binary
)

print(f"✅ Dataset loaded: {len(X_train)} train, {len(X_test)} test samples")
print(f"   Features: {X_binary.shape[1]} (sepal length, petal length)")
print(f"   Classes: {np.unique(y_binary)} (setosa, versicolor)")

# Plot the data
plt.figure(figsize=(8, 6))
for label, name, marker, color in [(0, 'Setosa', 'o', 'blue'), (1, 'Versicolor', 'x', 'red')]:
    mask = y_train == label
    plt.scatter(X_train[mask, 0], X_train[mask, 1], c=color, marker=marker,
                label=name, s=60, alpha=0.7)
plt.xlabel("Sepal Length (scaled)")
plt.ylabel("Petal Length (scaled)")
plt.title("Iris Dataset — 2 Classes, 2 Features")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("results/tutorial2_iris_data.png", dpi=150)
plt.show()

# %% [markdown]
# ## Part 2: Classical Baseline — SVM
#
# Before going quantum, establish a classical baseline. This is exactly
# what the roadmap prescribes in Sprint 2 (Task 1.8): build a classical
# credibility classifier using sklearn SVM as the benchmark to beat.

# %%
print("Training Classical SVM Baseline...")
svm = SVC(kernel='rbf', random_state=42)
svm.fit(X_train, y_train)

svm_train_acc = accuracy_score(y_train, svm.predict(X_train))
svm_test_acc = accuracy_score(y_test, svm.predict(X_test))

print(f"\n📊 Classical SVM Results:")
print(f"   Train Accuracy: {svm_train_acc:.1%}")
print(f"   Test Accuracy:  {svm_test_acc:.1%}")
print(f"\n   This is the benchmark the quantum classifier needs to match or beat.")

# %% [markdown]
# ## Part 3: Build the Quantum Circuit
#
# The VQC architecture from the Jarvis roadmap:
# 1. **ZZFeatureMap** — encodes features using entangling ZZ interactions
# 2. **RealAmplitudes** — trainable variational ansatz
# 
# This is the exact architecture specified for Module 4 (Credibility Verifier).

# %%
from qiskit.circuit.library import zz_feature_map, real_amplitudes
from qiskit.circuit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager

n_qubits = 2  # Matches number of features

# Feature map: encodes classical data into quantum states
# ZZFeatureMap creates entanglement between features — crucial for
# capturing correlations (like between sentiment score and source authority)
feature_map = zz_feature_map(feature_dimension=n_qubits, reps=2, entanglement='linear')

# Ansatz: trainable variational circuit
# RealAmplitudes with full entanglement gives maximum expressibility
ansatz = real_amplitudes(num_qubits=n_qubits, reps=3, entanglement='full')

# Decompose to basic gates so Aer can execute them
feature_map = feature_map.decompose()
ansatz = ansatz.decompose()

print("Quantum Circuit Structure:")
print(f"  Qubits: {n_qubits}")
print(f"  Feature map: ZZFeatureMap (reps=2, linear entanglement)")
print(f"  Ansatz: RealAmplitudes (reps=3, full entanglement)")
print(f"  Total parameters: {ansatz.num_parameters}")
print(f"\nFeature Map Circuit:")
print(feature_map.draw(output='text'))
print(f"\nAnsatz Circuit:")
print(ansatz.draw(output='text'))

# %% [markdown]
# ## Part 4: Train the VQC
#
# Using Qiskit Machine Learning's VQC class with the COBYLA optimiser,
# exactly as specified in Sprint 6, Task 2.7 of the roadmap.

# %%
from qiskit_aer import AerSimulator
from qiskit_machine_learning.algorithms import VQC
from qiskit_aer.primitives import SamplerV2 as AerSampler

print("Setting up VQC training...")
print("  Optimiser: COBYLA (maxiter=100)")
print("  Backend: AerSimulator (local CPU)")
print()

# Create the sampler primitive using Aer
sampler = AerSampler()

# Track training progress
objective_values = []
def callback(weights, obj_value):
    """Called after each optimisation iteration."""
    objective_values.append(obj_value)
    if len(objective_values) % 10 == 0:
        print(f"  Iteration {len(objective_values):3d} | Objective: {obj_value:.4f}")

# Create and train the VQC
from qiskit_algorithms.optimizers import COBYLA

optimizer = COBYLA(maxiter=100)

vqc = VQC(
    feature_map=feature_map,
    ansatz=ansatz,
    optimizer=optimizer,
    sampler=sampler,
    callback=callback,
)

print("🚀 Training started...")
vqc.fit(X_train, y_train)
print("✅ Training complete!")

# %% [markdown]
# ## Part 5: Evaluate the Quantum Classifier

# %%
# Predictions
y_train_pred = vqc.predict(X_train)
y_test_pred = vqc.predict(X_test)

vqc_train_acc = accuracy_score(y_train, y_train_pred)
vqc_test_acc = accuracy_score(y_test, y_test_pred)

print("\n" + "=" * 50)
print("RESULTS COMPARISON")
print("=" * 50)
print(f"\n{'Method':<25} {'Train Acc':>10} {'Test Acc':>10}")
print("-" * 50)
print(f"{'Classical SVM':<25} {svm_train_acc:>10.1%} {svm_test_acc:>10.1%}")
print(f"{'Quantum VQC':<25} {vqc_train_acc:>10.1%} {vqc_test_acc:>10.1%}")
print("-" * 50)

if vqc_test_acc >= svm_test_acc:
    print("🏆 Quantum VQC matches or beats the classical baseline!")
else:
    diff = svm_test_acc - vqc_test_acc
    print(f"⚡ Classical SVM leads by {diff:.1%} — more training or tuning may help")

print("\nDetailed Classification Report (Quantum VQC):")
print(classification_report(y_test, y_test_pred, target_names=['Setosa', 'Versicolor']))

# %% [markdown]
# ## Part 6: Training Convergence Plot

# %%
if len(objective_values) > 0:
    plt.figure(figsize=(10, 5))
    plt.plot(objective_values, 'b-', linewidth=1.5, alpha=0.8)
    plt.xlabel("Iteration")
    plt.ylabel("Objective Value")
    plt.title("VQC Training Convergence (COBYLA)")
    plt.grid(True, alpha=0.3)
    plt.axhline(y=objective_values[-1], color='red', linestyle='--', alpha=0.5,
                label=f'Final: {objective_values[-1]:.4f}')
    plt.legend()
    plt.tight_layout()
    plt.savefig("results/tutorial2_vqc_convergence.png", dpi=150)
    plt.show()
else:
    print("⚠️  No convergence data captured (COBYLA callback format may differ)")

# %% [markdown]
# ## Part 7: Scaling Up — 4 Features (4 Qubits)
#
# Now let's use all 4 Iris features with 4 qubits. This is closer to
# what Module 4 will do with multiple credibility features.

# %%
print("\n" + "=" * 50)
print("SCALING UP: 4 Features → 4 Qubits")
print("=" * 50)

# Use all 4 features, still 2 classes
mask_orig = iris.target < 2
X_4feat = iris.data[mask_orig]  # All 4 features
y_4feat = iris.target[mask_orig]
scaler_4 = MinMaxScaler(feature_range=(0, np.pi))
X_4feat_scaled = scaler_4.fit_transform(X_4feat)

X_train_4, X_test_4, y_train_4, y_test_4 = train_test_split(
    X_4feat_scaled, y_4feat, test_size=0.3, random_state=42, stratify=y_4feat
)

# 4-qubit VQC
feature_map_4 = zz_feature_map(feature_dimension=4, reps=2, entanglement='linear').decompose()
ansatz_4 = real_amplitudes(num_qubits=4, reps=3, entanglement='full').decompose()

optimizer_4 = COBYLA(maxiter=150)

objective_values_4 = []
def callback_4(weights, obj_value):
    objective_values_4.append(obj_value)
    if len(objective_values_4) % 20 == 0:
        print(f"  Iteration {len(objective_values_4):3d} | Objective: {obj_value:.4f}")

vqc_4 = VQC(
    feature_map=feature_map_4,
    ansatz=ansatz_4,
    optimizer=optimizer_4,
    sampler=sampler,
    callback=callback_4,
)

# Classical baseline for 4 features
svm_4 = SVC(kernel='rbf', random_state=42)
svm_4.fit(X_train_4, y_train_4)
svm_4_test_acc = accuracy_score(y_test_4, svm_4.predict(X_test_4))

print(f"\nClassical SVM (4 features): {svm_4_test_acc:.1%}")
print(f"Training 4-qubit VQC ({ansatz_4.num_parameters} parameters)...")

vqc_4.fit(X_train_4, y_train_4)
vqc_4_test_acc = accuracy_score(y_test_4, vqc_4.predict(X_test_4))

print(f"\n{'Method':<30} {'Test Accuracy':>15}")
print("-" * 50)
print(f"{'Classical SVM (4 features)':<30} {svm_4_test_acc:>15.1%}")
print(f"{'Quantum VQC (4 qubits)':<30} {vqc_4_test_acc:>15.1%}")

# %% [markdown]
# ## Summary — What This Means for Jarvis
#
# You've now built and trained two quantum classifiers using the exact
# components specified in the Jarvis Quantum roadmap:
#
# | Component | Tutorial | Jarvis Module 4 |
# |-----------|----------|-----------------|
# | Feature Map | ZZFeatureMap (2 reps, linear) | ZZFeatureMap (2 reps, linear) |
# | Ansatz | RealAmplitudes (3 reps, full) | RealAmplitudes (3 reps, full) |
# | Optimiser | COBYLA (100 iter) | COBYLA (200 iter) |
# | Data | Iris features | BERT embeddings → PCA reduced |
# | Task | Flower classification | Credibility classification |
#
# The only difference for Module 4 is the data pipeline: instead of Iris
# features, you'll feed in BERT-reduced article features (sentiment, 
# source authority, claim specificity, cross-reference score).
#
# **Next:** Tutorial 3 covers lambeq DisCoCat for Module 1 (NLU).

# %%
print("\n✅ Tutorial 2 complete!")
print("\nKey takeaways for Jarvis Quantum Module 4:")
print("  • ZZFeatureMap captures feature correlations via entanglement")
print("  • RealAmplitudes provides a flexible trainable layer")
print("  • COBYLA works well for small-parameter quantum circuits")
print("  • 4-qubit VQC can match classical SVM on real data")
print("  • Scale to Module 4 by swapping Iris features for credibility features")

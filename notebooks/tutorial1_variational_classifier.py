# %% [markdown]
# # Tutorial 1: PennyLane Variational Quantum Classifier
# 
# **Jarvis Quantum — Sprint 1, Task 1.4**
# 
# This tutorial teaches the core skill behind Module 1 (NLU) and Module 4 (Credibility):
# encoding classical data into quantum states and training a variational circuit to classify it.
#
# We'll build a quantum classifier that learns to separate two classes of data points,
# running entirely on your local CPU simulator.
#
# Based on: https://pennylane.ai/qml/demos/tutorial_variational_classifier

# %% [markdown]
# ## Part 1: Quantum Basics — Building Blocks
#
# Before classifying data, let's understand the three building blocks:
# 1. **Data Encoding** — map classical features into qubit rotations
# 2. **Variational Layer** — trainable quantum gates (this is the "neural network")
# 3. **Measurement** — read out the classification result

# %%
import pennylane as qml
from pennylane import numpy as np
import matplotlib.pyplot as plt

# Use the Jarvis backend router for device selection
import sys
sys.path.insert(0, '..')
try:
    from jarvis_backend_router import get_quantum_device
    print("✅ Using Jarvis backend router")
except ImportError:
    print("⚠️  Backend router not found, using direct device creation")
    get_quantum_device = None

# %% [markdown]
# ## Part 2: A Simple Quantum Circuit
#
# Let's start with the absolute basics — a single qubit circuit.

# %%
# Create a 1-qubit device
dev1 = qml.device("lightning.qubit", wires=1)

@qml.qnode(dev1)
def simple_circuit(angle):
    """Rotate a qubit and measure it."""
    qml.RX(angle, wires=0)     # Rotate around X-axis
    return qml.expval(qml.PauliZ(0))  # Measure Z expectation

# Test: sweep the angle from 0 to 2π
angles = np.linspace(0, 2 * np.pi, 50)
results = [simple_circuit(a) for a in angles]

plt.figure(figsize=(8, 4))
plt.plot(angles, results, 'b-', linewidth=2)
plt.xlabel("Rotation Angle (radians)")
plt.ylabel("⟨Z⟩ Expectation Value")
plt.title("Single Qubit: Rotation vs Measurement")
plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("results/tutorial1_single_qubit.png", dpi=150)
plt.show()
print("✅ Single qubit circuit working — this is how we encode data!")

# %% [markdown]
# ## Part 3: Variational Classifier — The Full Pipeline
#
# Now let's build a proper classifier with multiple qubits.
# The architecture:
# 1. **Encoding**: Rotate qubits based on input features (AngleEmbedding)
# 2. **Variational layers**: Trainable rotations + entangling gates (StronglyEntanglingLayers)
# 3. **Measurement**: Read out one qubit to get the class prediction

# %%
# Number of qubits = number of features we can encode
n_qubits = 2
n_layers = 3  # Depth of the variational circuit

dev = qml.device("lightning.qubit", wires=n_qubits)

@qml.qnode(dev)
def variational_classifier(weights, x):
    """
    A variational quantum classifier.
    
    Args:
        weights: Trainable parameters (shape: n_layers × n_qubits × 3)
        x: Input features to classify (length: n_qubits)
    """
    # Step 1: Encode classical data into quantum state
    qml.AngleEmbedding(x, wires=range(n_qubits))
    
    # Step 2: Apply trainable variational layers
    qml.StronglyEntanglingLayers(weights, wires=range(n_qubits))
    
    # Step 3: Measure first qubit
    return qml.expval(qml.PauliZ(0))

# Visualise the circuit
print("Circuit structure:")
weights_shape = qml.StronglyEntanglingLayers.shape(n_layers=n_layers, n_wires=n_qubits)
dummy_weights = np.random.randn(*weights_shape)
dummy_x = np.array([0.5, 0.3])
print(qml.draw(variational_classifier)(dummy_weights, dummy_x))

# %% [markdown]
# ## Part 4: Generate Training Data
#
# We'll create a simple 2D dataset with two classes — think of it as a 
# mini version of what the Credibility Verifier (Module 4) will do with 
# real article features.

# %%
np.random.seed(42)

def generate_data(n_samples=100):
    """
    Generate a 2D dataset with two classes.
    Class 0: points clustered around (-0.5, -0.5)
    Class 1: points clustered around (0.5, 0.5)
    """
    n_per_class = n_samples // 2
    
    # Class 0
    x0 = np.random.randn(n_per_class, 2) * 0.4 + np.array([-0.5, -0.5])
    y0 = np.zeros(n_per_class)
    
    # Class 1
    x1 = np.random.randn(n_per_class, 2) * 0.4 + np.array([0.5, 0.5])
    y1 = np.ones(n_per_class)
    
    # Combine and shuffle
    X = np.vstack([x0, x1])
    y = np.concatenate([y0, y1])
    
    # Convert labels: 0 → +1, 1 → -1 (matching PauliZ eigenvalues)
    y_quantum = 1 - 2 * y  # Maps 0→+1, 1→-1
    
    # Shuffle
    perm = np.random.permutation(n_samples)
    return X[perm], y_quantum[perm]

# Generate train and test sets
X_train, y_train = generate_data(100)
X_test, y_test = generate_data(40)

# Scale features to [0, π] range for angle encoding
def scale_features(X):
    """Scale features to [0, π] for quantum angle encoding."""
    X_min, X_max = X.min(axis=0), X.max(axis=0)
    return np.pi * (X - X_min) / (X_max - X_min + 1e-8)

X_train_scaled = scale_features(X_train)
X_test_scaled = scale_features(X_test)

# Plot the data
plt.figure(figsize=(8, 6))
mask_pos = y_train > 0
mask_neg = y_train < 0
plt.scatter(X_train[mask_pos, 0], X_train[mask_pos, 1], c='blue', marker='o', 
            label='Class 0 (⟨Z⟩ = +1)', alpha=0.7, s=60)
plt.scatter(X_train[mask_neg, 0], X_train[mask_neg, 1], c='red', marker='x', 
            label='Class 1 (⟨Z⟩ = -1)', alpha=0.7, s=60)
plt.xlabel("Feature 1")
plt.ylabel("Feature 2")
plt.title("Training Data — 2 Classes")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("results/tutorial1_training_data.png", dpi=150)
plt.show()
print(f"✅ Training set: {len(X_train)} samples | Test set: {len(X_test)} samples")

# %% [markdown]
# ## Part 5: Training the Quantum Classifier
#
# This is the key step — we use gradient descent to optimise the variational 
# circuit parameters, just like training a classical neural network.
# PennyLane computes gradients automatically via the parameter-shift rule.

# %%
def cost(weights, bias, X, y):
    """
    Cost function: mean squared error between predictions and labels.
    
    This is what we minimise during training. The quantum circuit
    is called once per data point, and gradients flow back through
    the parameter-shift rule.
    """
    predictions = np.array([variational_classifier(weights, x) + bias for x in X])
    return np.mean((predictions - y) ** 2)

def accuracy(weights, bias, X, y):
    """Classification accuracy: what percentage did we get right?"""
    predictions = np.array([variational_classifier(weights, x) + bias for x in X])
    predicted_labels = np.sign(predictions)
    return np.mean(predicted_labels == y)

# Initialise random weights
np.random.seed(42)
weights_shape = qml.StronglyEntanglingLayers.shape(n_layers=n_layers, n_wires=n_qubits)
weights = np.random.randn(*weights_shape, requires_grad=True) * 0.1
bias = np.array(0.0, requires_grad=True)

# Optimiser: gradient descent with momentum (Nesterov)
opt = qml.NesterovMomentumOptimizer(stepsize=0.3)

# Training loop
n_epochs = 30
batch_size = 20
train_costs = []
train_accs = []
test_accs = []

print("Training Variational Quantum Classifier")
print("=" * 50)
print(f"Qubits: {n_qubits} | Layers: {n_layers} | Epochs: {n_epochs}")
print(f"Parameters: {weights.size + 1}")
print("=" * 50)

for epoch in range(n_epochs):
    # Mini-batch: randomly sample from training data
    batch_idx = np.random.randint(0, len(X_train_scaled), batch_size)
    X_batch = X_train_scaled[batch_idx]
    y_batch = y_train[batch_idx]
    
    # Optimisation step
    (weights, bias), _cost = opt.step_and_cost(
        lambda w, b: cost(w, b, X_batch, y_batch),
        weights, bias
    )
    
    # Track metrics every 5 epochs
    if (epoch + 1) % 5 == 0 or epoch == 0:
        c = cost(weights, bias, X_train_scaled, y_train)
        train_acc = accuracy(weights, bias, X_train_scaled, y_train)
        test_acc = accuracy(weights, bias, X_test_scaled, y_test)
        train_costs.append(c)
        train_accs.append(train_acc)
        test_accs.append(test_acc)
        print(f"  Epoch {epoch+1:3d} | Cost: {c:.4f} | Train Acc: {train_acc:.1%} | Test Acc: {test_acc:.1%}")

print("=" * 50)
print(f"Final Train Accuracy: {train_accs[-1]:.1%}")
print(f"Final Test Accuracy:  {test_accs[-1]:.1%}")

# %% [markdown]
# ## Part 6: Visualise Results

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Training cost
epochs_tracked = [1] + list(range(5, n_epochs + 1, 5))
axes[0].plot(epochs_tracked, train_costs, 'b-o', linewidth=2, markersize=6)
axes[0].set_xlabel("Epoch")
axes[0].set_ylabel("Cost (MSE)")
axes[0].set_title("Training Cost")
axes[0].grid(True, alpha=0.3)

# Plot 2: Accuracy
axes[1].plot(epochs_tracked, train_accs, 'b-o', linewidth=2, markersize=6, label='Train')
axes[1].plot(epochs_tracked, test_accs, 'r-s', linewidth=2, markersize=6, label='Test')
axes[1].set_xlabel("Epoch")
axes[1].set_ylabel("Accuracy")
axes[1].set_title("Classification Accuracy")
axes[1].legend()
axes[1].grid(True, alpha=0.3)
axes[1].set_ylim([0, 1.05])

plt.suptitle("Variational Quantum Classifier — Training Results", fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig("results/tutorial1_training_results.png", dpi=150)
plt.show()

# %% [markdown]
# ## Part 7: Decision Boundary Visualisation
#
# Let's see what the quantum classifier actually learned — plotting its
# decision boundary over the feature space.

# %%
# Create a mesh grid over the feature space
x_min, x_max = X_train[:, 0].min() - 0.5, X_train[:, 0].max() + 0.5
y_min, y_max = X_train[:, 1].min() - 0.5, X_train[:, 1].max() + 0.5
xx, yy = np.meshgrid(
    np.linspace(x_min, x_max, 40),
    np.linspace(y_min, y_max, 40)
)

# Predict on every grid point
grid_points = np.c_[xx.ravel(), yy.ravel()]
grid_scaled = scale_features(grid_points)
grid_predictions = np.array([
    variational_classifier(weights, x) + bias for x in grid_scaled
])
grid_labels = grid_predictions.reshape(xx.shape)

# Plot
plt.figure(figsize=(8, 6))
plt.contourf(xx, yy, grid_labels, levels=20, cmap='RdBu', alpha=0.6)
plt.colorbar(label='⟨Z⟩ (Blue = Class 0, Red = Class 1)')
plt.scatter(X_train[mask_pos, 0], X_train[mask_pos, 1], c='blue', marker='o',
            edgecolors='black', s=60, label='Class 0', zorder=5)
plt.scatter(X_train[mask_neg, 0], X_train[mask_neg, 1], c='red', marker='x',
            s=60, linewidths=2, label='Class 1', zorder=5)
plt.contour(xx, yy, grid_labels, levels=[0], colors='black', linewidths=2)
plt.xlabel("Feature 1")
plt.ylabel("Feature 2")
plt.title("Quantum Classifier — Decision Boundary")
plt.legend()
plt.tight_layout()
plt.savefig("results/tutorial1_decision_boundary.png", dpi=150)
plt.show()

print("✅ Tutorial 1 complete!")
print("\nKey takeaways for Jarvis Quantum:")
print("  • AngleEmbedding encodes classical features into qubit rotations")
print("  • StronglyEntanglingLayers provide the trainable 'brain'")
print("  • PennyLane auto-differentiates through quantum circuits")
print("  • This exact pattern scales to Module 1 (NLU) and Module 4 (Credibility)")

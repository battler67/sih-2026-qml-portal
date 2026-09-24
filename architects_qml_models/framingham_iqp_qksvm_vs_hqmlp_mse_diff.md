# Framingham IQP QKSVM vs MSE HQMLP: example-level difference

Both models begin with the same prepared Framingham data and the same four PCA values. Their main difference is what the quantum circuit does with those values.

Suppose one fictional patient becomes:

```text
x = [0.80, -1.10, 0.35, 1.40]
```

These numbers are illustrative PCA values, not a real patient prediction.

## Difference at a glance

```text
IQP QKSVM
Patient → fixed quantum state → similarities to training patients → classical SVM

MSE HQMLP
Patient → learned classical layer → trainable quantum circuit → measurements → score
```

The IQP QKSVM asks:

> How similar is this patient to patterns in the training group?

The MSE HQMLP asks:

> Using the patterns learned during training, what score should this patient receive?

## IQP QKSVM example

### 1. Create a quantum state

Hadamard gates first place all four qubits into superposition. Phase gates then use the individual PCA values and relationships between them.

For the example patient, some feature products are:

```text
x0 × x1 =  0.80 × -1.10 = -0.88
x0 × x2 =  0.80 ×  0.35 =  0.28
x0 × x3 =  0.80 ×  1.40 =  1.12
x1 × x2 = -1.10 ×  0.35 = -0.385
x1 × x3 = -1.10 ×  1.40 = -1.54
x2 × x3 =  0.35 ×  1.40 =  0.49
```

These values control pairwise phase interactions in the IQP feature map. The circuit therefore represents both individual PCA values and combinations of values.

The resulting state is written as:

```text
|φIQP(x)⟩
```

### 2. Compare with training patients

The new patient state is compared with a training-patient state:

```text
K(x, ti) = |⟨φIQP(ti)|φIQP(x)⟩|²
```

Suppose the first few similarities are:

```text
Training patient 1: 0.73
Training patient 2: 0.21
Training patient 3: 0.84
...
Training patient 256: 0.47
```

A value near `1` means the two patients have similar quantum representations. A value near `0` means their representations are different.

### 3. Classical SVM decision

The SVM combines the important similarities:

```text
f(x) = Σ αi yi K(x, ti) + b
```

- `K(x, ti)` is the quantum similarity.
- `yi` is the training label.
- `αi` and `b` are learned by the classical SVM.
- Only support vectors have non-zero `αi` values.

The raw SVM result is subsequently calibrated, and a saved threshold produces the research class.

### What IQP QKSVM learns

```text
Quantum weights:         none
Quantum training epochs: none
Learned component:       classical SVM
Main SVM setting tested: C = 0.1, 1.0, or 10.0
```

The IQP circuit is fixed. It is a similarity calculator rather than a trainable quantum predictor.

## MSE HQMLP example

### 1. Learned classical projection

The same PCA values first pass through a learned classical layer:

```text
z = Wprojection × x + bprojection
```

Suppose it produces:

```text
z = [0.25, -0.60, 0.90, 0.10]
```

The model converts these values into angles:

```text
φ = π × tanh(z)
```

giving approximately:

```text
φ = [0.769, -1.687, 2.250, 0.313]
```

### 2. Trainable quantum circuit

Each angle is encoded with an `RY` gate:

```text
q0: RY( 0.769)
q1: RY(-1.687)
q2: RY( 2.250)
q3: RY( 0.313)
```

Each qubit then receives three learned rotations:

```text
q0: Rot(α0, β0, γ0)
q1: Rot(α1, β1, γ1)
q2: Rot(α2, β2, γ2)
q3: Rot(α3, β3, γ3)
```

The qubits are connected with a linear CNOT chain:

```text
q0 ──■────────────
     │
q1 ──X──■─────────
        │
q2 ─────X──■──────
           │
q3 ────────X──────
```

### 3. Measure and score

Suppose the four Pauli-Z measurements are:

```text
m = [0.42, -0.18, 0.61, 0.09]
```

The final classical layer calculates:

```text
logit = w0m0 + w1m1 + w2m2 + w3m3 + b
```

Suppose the result is:

```text
logit = 0.601
score = sigmoid(0.601) ≈ 0.646
```

### 4. MSE training loss

For a positive training label `y = 1`:

```text
loss = (score - y)²
loss = (0.646 - 1)²
loss ≈ 0.125
```

Adam changes the classical and quantum parameters to reduce this error.

### What MSE HQMLP learns

```text
Classical projection: 20 values
Quantum rotations:    12 values
Classical output:      5 values
Total:                37 values
```

Training can continue for up to 12 epochs with early stopping.

## Direct comparison

| IQP QKSVM | MSE HQMLP |
| --- | --- |
| Quantum similarity model | Direct hybrid scoring model |
| Fixed IQP feature map | Trainable quantum circuit |
| No learned quantum weights | 12 learned quantum weights |
| No quantum training epochs | Up to 12 training epochs |
| Compares a patient with training states | Processes one patient directly |
| Uses fixed feature-pair phase interactions | Learns feature interactions during training |
| Classical SVM makes the decision | Classical output layer makes the decision |
| Tunes the SVM setting `C` | Optimizes all 37 parameters with Adam |
| Trained with an SVM objective | Trained with mean-squared error |

## Practical interpretation

The IQP QKSVM behaves like a similarity-based system: it asks whether the new patient resembles important training examples.

The MSE HQMLP behaves like a small trainable neural network containing a quantum middle layer: it learns how to convert one patient's inputs directly into a score.

Both are evidence-only ideal-simulator experiments using teaching data. Neither is a clinically validated early-detection system or evidence of quantum advantage.

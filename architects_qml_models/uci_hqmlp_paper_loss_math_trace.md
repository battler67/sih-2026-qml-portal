# UCI paper-loss HQMLP: simple mathematical trace

This model combines a small classical neural network with a four-qubit quantum circuit. It uses four patient fields to produce a heart-disease research score.

## Complete flow

```text
4 patient values
      ↓
Classical 4-to-4 layer
      ↓
4 rotation angles
      ↓
One angle encoded on each qubit
      ↓
Learned quantum rotations
      ↓
CNOT connections between qubits
      ↓
4 quantum measurements
      ↓
Classical output and sigmoid
      ↓
Heart-disease research score
```

## 1. Input

The four inputs are:

```text
x = [thal, cp, thalach, ca]
```

- `thal`: thalassemia-related test category
- `cp`: chest-pain type
- `thalach`: maximum recorded heart rate
- `ca`: number of major vessels visible in fluoroscopy

## 2. Classical preparation

The model learns how to mix the four inputs:

```text
z = W × x + b
angles = π × tanh(z)
```

`W` contains learned importance values and `b` contains learned adjustments. The `tanh` step keeps every angle between `-π` and `+π`.

The result is four angles:

```text
[φ0, φ1, φ2, φ3]
```

## 3. Put the values onto four qubits

Each angle rotates one qubit:

```text
q0: RY(φ0)
q1: RY(φ1)
q2: RY(φ2)
q3: RY(φ3)
```

For one qubit:

```text
RY(φ)|0⟩ = cos(φ/2)|0⟩ + sin(φ/2)|1⟩
```

In simple terms, the patient value controls how much of state `0` and state `1` the qubit contains.

## 4. Learned quantum rotations

Every qubit receives three learned rotations:

```text
q0: Rot(α0, β0, γ0)
q1: Rot(α1, β1, γ1)
q2: Rot(α2, β2, γ2)
q3: Rot(α3, β3, γ3)
```

There are `4 × 3 = 12` learned quantum values.

## 5. Connect the qubits

The CNOT gates form a chain:

```text
q0 ──■────────────
     │
q1 ──X──■─────────
        │
q2 ─────X──■──────
           │
q3 ────────X──────
```

This allows information from one patient field to affect the other qubits. The circuit can therefore learn relationships between fields, rather than treating each field separately.

## 6. Measure the qubits

Each qubit produces a Pauli-Z reading:

```text
m0, m1, m2, m3
```

Each reading is between `-1` and `+1`:

```text
mi = probability of 0 − probability of 1
```

These four readings are the output of the quantum circuit.

## 7. Produce the model score

The final classical layer combines the measurements:

```text
logit = w0m0 + w1m1 + w2m2 + w3m3 + b
score = 1 / (1 + e^(-logit))
```

The score is between `0` and `1`. A saved threshold converts it into the model's research class.

## 8. Training loss

This version uses mean-squared error:

```text
loss = (score − correct label)²
```

For example, if the correct label is `1` and the model score is `0.7`:

```text
loss = (0.7 − 1)² = 0.09
```

Training adjusts all 37 learned values to reduce this error.

## Parameter count

```text
Classical input layer:  4×4 weights + 4 biases = 20
Quantum rotations:      4 qubits × 3 angles  = 12
Classical output layer: 4 weights + 1 bias   =  5
                                                --
Total                                         = 37
```

This was a small research experiment trained on 50 patients for three epochs. It is not a validated diagnostic model.

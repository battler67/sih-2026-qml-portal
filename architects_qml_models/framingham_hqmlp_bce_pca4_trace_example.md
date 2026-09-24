# Framingham BCE HQMLP PCA-4: example trace

This walkthrough follows one fictional patient through the model. The numbers below are chosen only to explain the calculation. They are **not** the saved model weights or a real patient prediction.

## What the model is trying to learn

The research target is whether a participant who had no coronary heart disease at baseline experienced a recorded CHD event within ten years.

```text
15 baseline health fields
          ↓
Missing-value preparation and standardization
          ↓
PCA: 15 fields become 4 summary values
          ↓
Learned classical 4-to-4 projection
          ↓
Four-qubit trainable circuit
          ↓
Four Pauli-Z readings
          ↓
Classical output, calibration, and saved threshold
          ↓
10-year CHD research class
```

## Step 1: fictional baseline record

The original input contains 15 fields, including age, sex, smoking, blood-pressure medication, previous stroke, hypertension, diabetes, cholesterol, systolic and diastolic blood pressure, BMI, heart rate, and glucose.

For example:

```text
Age                 58
Current smoker      yes
Cigarettes/day      10
Total cholesterol   238
Systolic BP          146
Diastolic BP          88
BMI                 28.2
Heart rate            76
Glucose              104
...remaining baseline fields...
```

The model does not diagnose this fictional person. These values only demonstrate the data flow.

## Step 2: prepare the 15 fields

The preparation pipeline was fitted using training data only:

1. Missing values are replaced with the training-set median.
2. Each field is standardized using its training-set mean and spread.
3. PCA combines the 15 standardized fields into four summary values.
4. The four PCA values are scaled into the range `-π` to `+π`.

Suppose this produces:

```text
x = [0.80, -1.10, 0.35, 1.40]
```

PCA values are mixtures of the original fields. They should not be read as individual medical measurements or causal importance scores.

## Step 3: learned classical projection

The first trainable layer mixes the four PCA values:

```text
z = Wprojection × x + bprojection
```

Assume the learned layer produces this illustrative result:

```text
z = [0.25, -0.60, 0.90, 0.10]
```

The model converts these values into four bounded angles:

```text
φ = π × tanh(z)
```

Therefore:

```text
φ0 = π × tanh( 0.25) ≈  0.769
φ1 = π × tanh(-0.60) ≈ -1.687
φ2 = π × tanh( 0.90) ≈  2.250
φ3 = π × tanh( 0.10) ≈  0.313
```

The projection has 20 learned values:

```text
4 × 4 weights + 4 biases = 20
```

## Step 4: encode the angles on four qubits

The circuit begins in:

```text
|0000⟩
```

One `RY` gate places each angle on one qubit:

```text
q0: RY( 0.769)
q1: RY(-1.687)
q2: RY( 2.250)
q3: RY( 0.313)
```

For any one qubit:

```text
RY(φ)|0⟩ = cos(φ/2)|0⟩ + sin(φ/2)|1⟩
```

For `q0`:

```text
RY(0.769)|0⟩ ≈ 0.927|0⟩ + 0.375|1⟩
```

This does not mean the patient is partly healthy and partly diseased. It is simply how a numeric input is represented in a quantum state.

## Step 5: learned quantum layer

Every qubit receives one learned `RY` rotation and one learned `RZ` rotation:

```text
q0: RY(θy0) → RZ(θz0)
q1: RY(θy1) → RZ(θz1)
q2: RY(θy2) → RZ(θz2)
q3: RY(θy3) → RZ(θz3)
```

These are eight learned quantum values:

```text
4 qubits × 2 angles = 8
```

The `RY` gates change the balance between the qubit's `0` and `1` components. The `RZ` gates change their relative phase, which matters when the qubits interact.

## Step 6: connect the qubits

The linear CNOT chain is:

```text
q0 ──RY(φ0)──RY(θy0)──RZ(θz0)──■────────────
                                │
q1 ──RY(φ1)──RY(θy1)──RZ(θz1)──X──■─────────
                                   │
q2 ──RY(φ2)──RY(θy2)──RZ(θz2)─────X──■──────
                                      │
q3 ──RY(φ3)──RY(θy3)──RZ(θz3)────────X──────
```

The links allow the final state to represent relationships among the four PCA summaries. They do not establish medical causation.

## Step 7: measure all four qubits

The simulator calculates one Pauli-Z expectation from each qubit:

```text
mi = P(qi = 0) - P(qi = 1)
```

Every reading is between `-1` and `+1`. Suppose the circuit returns:

```text
m = [0.42, -0.18, 0.61, 0.09]
```

These are quantum model signals, not probabilities.

## Step 8: classical output

The final classical layer calculates a raw score called a logit:

```text
logit = w0m0 + w1m1 + w2m2 + w3m3 + b
```

Using illustrative output weights:

```text
w = [0.80, -0.40, 0.60, 0.30]
b = -0.20
```

the calculation is:

```text
logit = (0.80 × 0.42)
      + (-0.40 × -0.18)
      + (0.60 × 0.61)
      + (0.30 × 0.09)
      - 0.20

logit ≈ 0.601
```

The sigmoid converts it to a value between zero and one:

```text
sigmoid(0.601) = 1 / (1 + e^-0.601) ≈ 0.646
```

This is the model's uncalibrated score. The benchmark subsequently fits calibration and selects a decision threshold using a separate calibration partition. The held-out test outcomes are not used to choose that threshold.

## Step 9: BCE training loss

During training, the model compares the raw logit with the correct ten-year label using class-weighted binary cross-entropy.

For a positive label `y = 1`, ignoring the class weight for this simple example:

```text
loss = -log(sigmoid(logit))
loss = -log(0.646)
loss ≈ 0.437
```

If the correct label were `0`:

```text
loss = -log(1 - 0.646)
loss ≈ 1.039
```

Adam adjusts the classical and quantum parameters to reduce this loss across the training rows. Positive examples receive additional weight when the training classes are imbalanced.

## Where the 33 learned values come from

```text
Classical projection: 4×4 weights + 4 biases = 20
Quantum layer:        4 qubits × 2 rotations  =  8
Classical output:     4 weights + 1 bias      =  5
                                                   --
Total                                              33
```

## Training context

- 256 training rows per seed
- 597 held-out test rows
- Three experimental seeds
- Up to 12 epochs
- Early stopping after four epochs without validation improvement
- Adam learning rate: 0.01
- Weight decay: 0.0001

This is an evidence-only teaching-data experiment. It studies ten-year risk prediction, but it is not a clinically validated early-detection or diagnostic system.

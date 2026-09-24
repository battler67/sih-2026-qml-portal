# Framingham Angle QKSVM PCA-4: example trace

This walkthrough follows one fictional patient through the model. All patient values and SVM numbers below are illustrative. They are **not** a real prediction or the saved model coefficients.

## What this model does

This model does not learn adjustable quantum gates. The quantum circuit acts as a similarity calculator. It compares a new patient with the 256 training patients, and a classical support vector machine uses those similarities to produce a ten-year CHD research score.

```text
15 baseline health fields
          ↓
Missing-value preparation and standardization
          ↓
PCA: 15 fields become 4 values
          ↓
One PCA value encoded on each qubit
          ↓
Compare the new quantum state with training states
          ↓
256 similarity values
          ↓
Classical SVM
          ↓
Calibration and saved threshold
          ↓
10-year CHD research class
```

## Step 1: fictional baseline record

The original input contains 15 baseline fields, including age, sex, smoking, medication, previous conditions, cholesterol, blood pressure, BMI, heart rate, and glucose.

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

## Step 2: prepare and reduce the data

The preparation pipeline was fitted using training rows only:

1. Replace missing values with the training-set median.
2. Standardize each field using training-set statistics.
3. Use PCA to combine 15 fields into four summary values.
4. Scale the four PCA values into the angle range `-π` to `+π`.

Suppose the fictional patient becomes:

```text
x = [0.80, -1.10, 0.35, 1.40]
```

These are PCA summaries, not individual medical measurements or causal risk factors.

## Step 3: encode the patient on four qubits

All qubits begin in:

```text
|0000⟩
```

Each PCA value controls one `RY` rotation:

```text
q0: RY( 0.80)
q1: RY(-1.10)
q2: RY( 0.35)
q3: RY( 1.40)
```

The circuit is:

```text
q0: |0⟩ ──RY(x0)──
q1: |0⟩ ──RY(x1)──
q2: |0⟩ ──RY(x2)──
q3: |0⟩ ──RY(x3)──
```

There are no CNOT gates and no learned quantum weights in this feature map.

For one qubit:

```text
RY(xi)|0⟩ = cos(xi/2)|0⟩ + sin(xi/2)|1⟩
```

The four-qubit patient state is:

```text
|φ(x)⟩ = RY(x0)|0⟩ ⊗ RY(x1)|0⟩ ⊗ RY(x2)|0⟩ ⊗ RY(x3)|0⟩
```

## Step 4: encode one training patient

Assume one prepared training patient has:

```text
t = [0.60, -0.90, 0.10, 1.00]
```

Its quantum state is:

```text
|φ(t)⟩ = RY(t0)|0⟩ ⊗ RY(t1)|0⟩ ⊗ RY(t2)|0⟩ ⊗ RY(t3)|0⟩
```

## Step 5: calculate their quantum similarity

The kernel is the squared overlap between the two states:

```text
K(x,t) = |⟨φ(t)|φ(x)⟩|²
```

The compute-uncompute circuit applies the new patient's rotations and then reverses the training patient's rotations:

```text
q0: |0⟩ ──RY(x0)──RY(-t0)── measure
q1: |0⟩ ──RY(x1)──RY(-t1)── measure
q2: |0⟩ ──RY(x2)──RY(-t2)── measure
q3: |0⟩ ──RY(x3)──RY(-t3)── measure
```

The probability of measuring `0000` is the kernel value.

Because this angle circuit contains independent `RY` gates, the same value can be written directly as:

```text
K(x,t) = cos²((x0-t0)/2)
       × cos²((x1-t1)/2)
       × cos²((x2-t2)/2)
       × cos²((x3-t3)/2)
```

For the illustrative patients:

```text
x - t = [0.20, -0.20, 0.25, 0.40]

K(x,t) = cos²( 0.10)
       × cos²(-0.10)
       × cos²( 0.125)
       × cos²( 0.20)

K(x,t) ≈ 0.9900 × 0.9900 × 0.9845 × 0.9605
K(x,t) ≈ 0.927
```

The two example patients are therefore highly similar in this four-dimensional quantum representation.

Useful checks are:

```text
K(x,x) = 1
0 ≤ K(x,t) ≤ 1
K(x,t) = K(t,x)
```

## Step 6: compare with all training patients

The same calculation is performed against the 256 training states:

```text
k(x) = [K(x,t1), K(x,t2), ..., K(x,t256)]
```

This 256-value similarity row is the input to the classical SVM. In the recorded simulator benchmark, states were cached and their fidelities were calculated with classical matrix multiplication. This is mathematically equivalent to the ideal state-overlap circuit, but it is not a QPU execution or evidence of quantum speedup.

## Step 7: classical SVM decision

Only training patients selected as support vectors contribute to the final SVM decision:

```text
f(x) = Σi αi yi K(x,ti) + b
```

- `K(x,ti)` is the quantum similarity.
- `yi` is the training label.
- `αi` and `b` are learned by the classical SVM.
- Most training rows have `αi = 0` and do not contribute.

For a short illustrative example with three support vectors:

```text
signed coefficients = [0.80, -0.50, 0.30]
kernel similarities = [0.927, 0.350, 0.620]
bias                = -0.20

f(x) = (0.80 × 0.927)
     + (-0.50 × 0.350)
     + (0.30 × 0.620)
     - 0.20

f(x) ≈ 0.553
```

A positive raw decision means the example lies on the SVM's positive side of its learned boundary. It is not yet a probability.

## Step 8: calibration and threshold

A separate calibration partition converts the raw SVM decision into a better-scaled research score:

```text
calibrated score = sigmoid(a × f(x) + c)
```

The constants `a` and `c`, and the final decision threshold, are fitted without using the held-out test outcomes.

```text
class = 1 when calibrated score ≥ saved threshold
class = 0 when calibrated score < saved threshold
```

The displayed score should not be interpreted as a clinically validated personal probability.

## What is actually trained

```text
Quantum gate weights     none
Quantum training epochs  none
Classical SVM            trained on the kernel matrix
SVM C values tested      0.1, 1.0, 10.0
Calibration              fitted on a separate calibration partition
Decision threshold       selected on that calibration partition
```

## Training context

- 256 training rows per experimental seed
- 597 held-out test rows
- Three seeds
- Four qubits
- Four PCA values retained
- Ideal statevector simulation with cached states

This is an evidence-only educational experiment. It studies ten-year CHD risk classification but cannot run new predictions in the portal and is not a clinically validated early-detection system.

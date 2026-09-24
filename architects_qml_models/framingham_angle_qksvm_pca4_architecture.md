# Framingham Angle QKSVM PCA-4 architecture

Model ID: **framingham-angle-qksvm-pca4**  
Portal status: evidence only  
Purpose: four-feature educational quantum-kernel comparison

## Training snapshot

Each of three seeds used **256 training rows** and **597 held-out test rows**. PCA reduced the prepared health data to four values. The circuit has no learned gate weights and therefore no epochs; the classical SVM tested C = 0.1, 1.0, 10.0 on tuning data.

## Architecture

```mermaid
flowchart LR
    A["15 baseline health fields"]
    B["Fold-local preparation"]
    C["PCA<br/>15 fields -> 4 values"]
    D["Four-qubit angle map"]
    E["State fidelity against training states"]
    F["Quantum kernel matrix"]
    G["Classical SVM + calibration"]
    H["10-year CHD research class"]
    A --> B --> C --> D --> E --> F --> G --> H
```

## Four-qubit circuit flow

```mermaid
flowchart LR
    X["PCA values<br/>x0, x1, x2, x3"]
    Q0["q0: RY(x0)"]
    Q1["q1: RY(x1)"]
    Q2["q2: RY(x2)"]
    Q3["q3: RY(x3)"]
    S["Four-qubit state"]
    K["Squared state overlap<br/>with each training state"]
    X --> Q0 --> S
    X --> Q1 --> S
    X --> Q2 --> S
    X --> Q3 --> S
    S --> K
```

The four-qubit version keeps twice as many PCA values as the runnable two-qubit model, but otherwise uses the same angle-kernel design.

## Evidence boundary

This registry entry preserves a simulator-only research result and cannot run new portal predictions.

## Implementation sources

- qml-research/src/qml_research/framingham/benchmark.py
- qml-research/src/qml_research/quantum/kernels.py


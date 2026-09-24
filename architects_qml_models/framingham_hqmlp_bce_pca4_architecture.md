# Framingham BCE HQMLP PCA-4 architecture

Model ID: **framingham-hqmlp-bce-pca4**  
Portal status: evidence only  
Purpose: hybrid classical-quantum CHD comparison

## Training snapshot

Each of three seeds used **256 training rows** and **597 held-out test rows**. Training allowed up to **12 epochs**, with early stopping after four stale epochs. Adam used a 0.01 learning rate and 0.0001 weight decay. The model learned **33 values**: 25 classical and 8 quantum.

## Architecture

```mermaid
flowchart LR
    A["Prepared Framingham data"]
    B["PCA<br/>4 values"]
    C["Classical 4-to-4 projection"]
    D["Four-qubit RY encoding"]
    E["Trainable RY + RZ gates"]
    F["Linear CNOT chain"]
    G["Measure all 4 qubits"]
    H["Classical 4-to-1 output"]
    I["Calibrated CHD research class"]
    A --> B --> C --> D --> E --> F --> G --> H --> I
```

## Hybrid circuit flow

```mermaid
flowchart LR
    P["4 PCA values"]
    L["Learned projection<br/>tanh scaling"]
    Q["q0-q3: RY inputs"]
    R["Trainable RY and RZ<br/>on every qubit"]
    C["CNOT links<br/>q0-q1-q2-q3"]
    M["Four Pauli-Z readings"]
    O["Learned output layer"]
    P --> L --> Q --> R --> C --> M --> O
```

The classical layers prepare and combine information; the four-qubit middle layer learns feature interactions. Training used class-weighted binary cross-entropy.

## Evidence boundary

This is an evidence-only teaching-data experiment, not a clinical model or proof of quantum advantage.

## Implementation sources

- qml-research/src/qml_research/ehr_ihd/models.py
- qml-research/src/qml_research/framingham/benchmark.py


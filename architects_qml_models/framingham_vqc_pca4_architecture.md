# Framingham VQC PCA-4 architecture

Model ID: **framingham-vqc-pca4**  
Portal status: evidence only  
Purpose: trainable variational quantum comparison

## Training snapshot

Each of three seeds used **256 training rows** and **597 held-out test rows**. Training ran for **30 optimizer steps** with batches of 16. Adam used a 0.05 learning rate to learn **13 values**: 12 circuit rotation values and one output bias.

## Architecture

```mermaid
flowchart LR
    A["Prepared Framingham data"]
    B["PCA<br/>4 values"]
    C["RY angle encoding<br/>4 qubits"]
    D["Trainable rotation layer"]
    E["Entangling connections"]
    F["Measure Pauli-Z on q0"]
    G["Add learned bias"]
    H["Calibration + threshold"]
    I["10-year CHD research class"]
    A --> B --> C --> D --> E --> F --> G --> H --> I
```

## Four-qubit circuit flow

```mermaid
flowchart LR
    X["x0, x1, x2, x3"]
    Q["q0-q3<br/>RY input rotations"]
    R["One trainable layer<br/>3 rotation values per qubit"]
    C["Entangling links<br/>share information across qubits"]
    M["Read q0<br/>Pauli-Z"]
    B["Learned bias"]
    X --> Q --> R --> C --> M --> B
```

Unlike a quantum-kernel model, this circuit learns its own rotation values during training.

## Evidence boundary

This was a bounded simulator experiment on teaching data. It is not available for new portal predictions and is not clinical evidence.

## Implementation sources

- qml-research/src/qml_research/quantum/vqc.py
- qml-research/src/qml_research/framingham/benchmark.py


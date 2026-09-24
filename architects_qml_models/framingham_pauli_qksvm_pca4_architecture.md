# Framingham Pauli QKSVM PCA-4 architecture

Model ID: **framingham-pauli-qksvm-pca4**  
Portal status: evidence only  
Purpose: Pauli Z/ZZ quantum-kernel comparison

## Training snapshot

Each audited seed used **256 training rows** and **597 held-out test rows**. There are no learned circuit weights or epochs. The Pauli map repeats twice, and the SVM strength was selected from 0.1, 1.0, and 10.0.

## Architecture

```mermaid
flowchart LR
    A["Prepared health data"]
    B["PCA<br/>4 values"]
    C["Pauli Z/ZZ feature map<br/>4 qubits, 2 repeats"]
    D["State fidelity kernel"]
    E["Classical SVM"]
    F["Calibration + threshold"]
    G["10-year CHD research class"]
    A --> B --> C --> D --> E --> F --> G
```

## Pauli circuit flow

```mermaid
flowchart LR
    X["x0, x1, x2, x3"]
    H["H on every qubit"]
    Z["RZ from each feature"]
    E["Linear links<br/>q0-q1, q1-q2, q2-q3"]
    ZZ["CNOT - RZ - CNOT<br/>adds pair information"]
    R["Repeat the block twice"]
    K["Compare quantum states"]
    X --> H --> Z --> E --> ZZ --> R --> K
```

The single-qubit phases hold individual features; the linked gates add relationships between neighboring features.

## Evidence boundary

This is a local exact-statevector experiment. The portal keeps its evidence but does not serve new predictions from it.

## Implementation sources

- qml-research/src/qml_research/framingham/benchmark.py
- qml-research/src/qml_research/ehr_ihd/models.py


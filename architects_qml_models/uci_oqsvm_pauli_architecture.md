# UCI Pauli OQSVM architecture

Model ID: **uci-oqsvm-pauli**  
Portal status: evidence only  
Purpose: Cleveland heart-disease presence classification

## Training snapshot

The quantum kernel used a balanced subset of **50 training patients**, with **45 validation** and **46 test patients**. It has no epochs or learned gate weights. Validation compared SVM C values 0.1 and 1.0 and selected **0.1**. The circuit used four qubits, two Pauli-map repeats, and ideal statevector simulation.

## Architecture

```mermaid
flowchart LR
    A["Cleveland patient record"]
    B["Select 4 fields<br/>thal, cp, thalach, ca"]
    C["Scale to quantum angles"]
    D["Four-qubit Pauli Z/ZZ map"]
    E["Fidelity kernel matrix"]
    F["Classical SVM"]
    G["Validation-only calibration"]
    H["Heart-disease presence class"]
    A --> B --> C --> D --> E --> F --> G --> H
```

## Pauli circuit flow

```mermaid
flowchart LR
    X["4 selected values"]
    H["H on q0-q3"]
    Z["RZ feature phases"]
    L["Linear links<br/>q0-q1, q1-q2, q2-q3"]
    ZZ["CNOT - RZ - CNOT<br/>for linked feature pairs"]
    R["Repeat twice"]
    K["Compare patient states"]
    X --> H --> Z --> L --> ZZ --> R --> K
```

The circuit creates patient-to-patient similarities. The SVM, calibration, and final decision remain classical.

## Evidence boundary

This was one small diagnostic smoke test. It does not predict future disease and is unavailable for new portal predictions.

## Implementation sources

- qml-research/src/qml_research/ehr_ihd/models.py
- qml-research/results/ehr_ihd_qml/uci-smoke-20260829T194302Z-3b55c98a85f0


# UCI paper-loss HQMLP architecture

Model ID: **uci-hqmlp-paper-ablation**  
Portal status: evidence only  
Purpose: alternate hybrid architecture and loss comparison

## Training snapshot

The model used a balanced subset of **50 training patients**, with **45 validation** and **46 test patients**. It trained for **3 epochs** with Adam, a 0.01 learning rate, and 0.0001 weight decay. It learned **37 values**: 25 classical and 12 quantum.

## Architecture

```mermaid
flowchart LR
    A["Cleveland patient record"]
    B["4 selected fields<br/>thal, cp, thalach, ca"]
    C["Classical 4-to-4 projection"]
    D["RY encoding on 4 qubits"]
    E["Trainable U3-style rotations"]
    F["CNOT chain"]
    G["Measure all qubits"]
    H["Classical output"]
    I["MSE training loss"]
    J["Heart-disease presence class"]
    A --> B --> C --> D --> E --> F --> G --> H --> I --> J
```

## Hybrid circuit flow

```mermaid
flowchart LR
    P["4 selected values"]
    L["Learned projection"]
    Q["q0-q3: RY inputs"]
    R["3 learned rotation values<br/>per qubit"]
    C["CNOT<br/>q0-q1-q2-q3"]
    M["4 Pauli-Z readings"]
    O["Learned output"]
    P --> L --> Q --> R --> C --> M --> O
```

This comparison changes the trainable quantum rotations and uses mean-squared error instead of the preferred binary loss.

## Evidence boundary

This is a small research ablation, not a validated medical model.

## Implementation sources

- qml-research/src/qml_research/ehr_ihd/models.py
- qml-research/results/ehr_ihd_qml/uci-smoke-20260829T194302Z-3b55c98a85f0


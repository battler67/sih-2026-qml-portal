# WDBC four-qubit QCNN architecture

Model ID: **imaging-wdbc-qcnn**  
Portal status: evidence only  
Purpose: breast-mass morphology control experiment

## Training snapshot

Two small folds were recorded. Each fold used **16 training records**, **8 validation records**, and **16 test records**, with **1 epoch** and batches of 8. Adam used a 0.01 learning rate, 0.0001 weight decay, and 0.05 starting scale. Each fold learned **38 values**. This WDBC entry uses numeric morphology features, not medical images.

## Architecture

```mermaid
flowchart LR
    A["30 WDBC morphology fields"]
    B["Training-only scaling"]
    C["PCA<br/>30 fields -> 4 values"]
    D["Four RY input angles"]
    E["QCNN stage 1<br/>4 qubits -> 2"]
    F["QCNN stage 2<br/>2 qubits -> 1"]
    G["Pauli-Z reading"]
    H["Scale + bias + sigmoid"]
    I["Benign or malignant research class"]
    A --> B --> C --> D --> E --> F --> G --> H --> I
```

## Circuit-level qubit flow

```mermaid
flowchart LR
    Q["q0, q1, q2, q3<br/>RY from PCA values"]
    C1["Stage 1 convolution<br/>q0-q1, q2-q3, q1-q2, q3-q0"]
    P1["Pooling<br/>q0 -> q1 and q2 -> q3"]
    K["q1 and q3 remain"]
    C2["Stage 2 convolution<br/>q1-q3"]
    P2["Pooling<br/>q1 -> q3"]
    M["Measure q3"]
    Q --> C1 --> P1 --> K --> C2 --> P2 --> M
```

The circuit shape matches the BreastMNIST QCNN. The important difference is the input: four PCA values from WDBC tabular measurements replace four pooled image regions.

## Saved weights

| Weight group | Values | Purpose |
| --- | ---: | --- |
| Convolution weights | 30 | Learn pair patterns across two stages |
| Pooling weights | 6 | Control which information continues |
| Output scale and bias | 2 | Convert the final reading into a score |
| **Total** | **38** | Learned values per fold |

## Evidence boundary

These were two tiny, one-epoch control folds. The entry is evidence only and is not a screening or diagnostic system.

## Implementation sources

- qml-research/src/qml_research/qcnn/quantum.py
- qml-research/results/qcnn_breast_cancer/runs/4209ff4c4f241129
- qml-research/results/qcnn_breast_cancer/runs/b0fccd3f82ab8ce8


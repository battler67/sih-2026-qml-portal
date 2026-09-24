# Synthetic FH Angle QKSVM architecture

Model ID: **fh-angle-qksvm-rule-reproduction**  
Portal status: runnable  
Purpose: reproduce a synthetic familial-hypercholesterolemia referral rule

## Training snapshot

The model used **240 synthetic training records** and **120 synthetic test records**. It has no epochs or trainable circuit weights. Four fixed features were standardized and mapped to four qubits; a classical SVM used fixed C = 1.0. The seed was 26139.

## Architecture

```mermaid
flowchart LR
    A["Synthetic FH record"]
    B["4 features<br/>LDL-C, genomic evidence,<br/>family history, phenotype"]
    C["Standardize and bound values"]
    D["Four-qubit RY angle map"]
    E["Fidelity kernel"]
    F["Classical SVM"]
    G["Synthetic referral-rule class"]
    A --> B --> C --> D --> E --> F --> G
```

## Four-qubit circuit flow

```mermaid
flowchart LR
    F0["LDL-C"] --> Q0["q0: RY(angle 0)"]
    F1["Genomic evidence"] --> Q1["q1: RY(angle 1)"]
    F2["Family history"] --> Q2["q2: RY(angle 2)"]
    F3["Phenotype"] --> Q3["q3: RY(angle 3)"]
    Q0 --> S["Quantum state"]
    Q1 --> S
    Q2 --> S
    Q3 --> S
    S --> K["Squared overlap with<br/>240 saved training states"]
```

The quantum circuit turns the four synthetic inputs into a state. Similarities to the saved training states become inputs to the SVM.

## Evidence boundary

The labels were generated from a synthetic referral rule. The strong saved score measures rule reproduction, not FH detection or clinical performance.

## Implementation sources

- scripts/build_fh_synthetic_models.py
- qml_inference/artifacts/v1/fh/model_evidence.json


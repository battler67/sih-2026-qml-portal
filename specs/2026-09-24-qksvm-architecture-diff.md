# Pauli, IQP, and MSE hybrid architecture comparison

## Goal

Create a plain-language Markdown comparison of the Framingham Pauli QKSVM, IQP QKSVM, and MSE HQMLP architectures using the repository's implementation and recorded benchmark evidence.

## Scope

- Correct the mistaken phrase "MSE QKSVM": the repository contains an MSE HQMLP, not an MSE-trained QKSVM.
- Explain how the data flows through each architecture.
- Explain why all three were included in the matched experiment.
- Describe realistic research uses and limitations.
- Compare recorded results across seeds 11, 42, and 73.

## Sources checked

- `qml-research/src/qml_research/quantum/kernels.py`
- `qml-research/src/qml_research/ehr_ihd/models.py`
- `qml-research/src/qml_research/framingham/benchmark.py`
- Per-seed metrics for the audited Framingham run `framingham-audited-20260909`
- Existing architecture notes under `architects_qml_models/`

## Verification

- Confirmed that both QKSVM implementations use fixed feature maps with zero trainable circuit parameters.
- Confirmed that the MSE model is `hqmlp_mse_pca4`, with 37 trainable values and up to 12 epochs.
- Calculated the displayed means from the recorded seed-11, seed-42, and seed-73 held-out metrics.
- Kept the claims limited to evidence-only exact-simulator research.

## Files changed

- `architects_qml_models/pauli_iqp_qksvm_vs_mse_hqmlp_diff.md`
- `architects_qml_models/README.md`
- `specs/2026-09-24-qksvm-architecture-diff.md`

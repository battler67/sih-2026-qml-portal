# Portal QML model architectures

This directory documents every portal registry entry whose model family is quantum kernel, hybrid QML, or QCNN. Classical and deep-learning comparison models are not included.

| Portal model | Family | Portal availability | Architecture document |
| --- | --- | --- | --- |
| BreastMNIST QCNN | QCNN | Runnable | [BreastMNIST QCNN](breastmnist_qcnn_architecture.md) |
| WDBC four-qubit QCNN | QCNN | Evidence only | [WDBC QCNN](imaging_wdbc_qcnn_architecture.md) |
| Framingham Angle QKSVM, PCA-2 | Quantum kernel | Runnable | [Angle QKSVM PCA-2](framingham_angle_qksvm_pca2_architecture.md) |
| Framingham Angle QKSVM, PCA-4 | Quantum kernel | Evidence only | [Angle QKSVM PCA-4](framingham_angle_qksvm_pca4_architecture.md) |
| Framingham IQP QKSVM, PCA-4 | Quantum kernel | Evidence only | [IQP QKSVM PCA-4](framingham_iqp_qksvm_pca4_architecture.md) |
| Framingham Pauli QKSVM, PCA-4 | Quantum kernel | Evidence only | [Pauli QKSVM PCA-4](framingham_pauli_qksvm_pca4_architecture.md) |
| Framingham VQC, PCA-4 | Variational quantum classifier | Evidence only | [VQC PCA-4](framingham_vqc_pca4_architecture.md) |
| Framingham BCE HQMLP, PCA-4 | Hybrid QML | Evidence only | [BCE HQMLP PCA-4](framingham_hqmlp_bce_pca4_architecture.md) |
| Framingham MSE HQMLP, PCA-4 | Hybrid QML | Evidence only | [MSE HQMLP PCA-4](framingham_hqmlp_mse_pca4_architecture.md) |
| UCI Pauli OQSVM | Quantum kernel | Evidence only | [UCI Pauli OQSVM](uci_oqsvm_pauli_architecture.md) |
| UCI preferred BCE HQMLP | Hybrid QML | Evidence only | [UCI preferred HQMLP](uci_hqmlp_preferred_architecture.md) |
| UCI paper-loss HQMLP | Hybrid QML | Evidence only | [UCI paper-loss HQMLP](uci_hqmlp_paper_ablation_architecture.md) |
| Synthetic FH Angle QKSVM | Quantum kernel | Runnable | [Synthetic FH Angle QKSVM](fh_angle_qksvm_rule_reproduction_architecture.md) |

“Evidence only” means the portal can show the saved research result, but does not expose that model for new predictions.

## Architecture comparisons

- [Pauli QKSVM vs IQP QKSVM vs MSE HQMLP](pauli_iqp_qksvm_vs_mse_hqmlp_diff.md)

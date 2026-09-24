# QML model architecture documentation plan

## Goal

Create compact, editable model-architecture diagrams for the QML models available in the portal. Use box-and-flow diagrams rather than transpiled circuit images, and expose only the stages needed to understand how each model transforms its input into a prediction.

## Current trial scope

- Create `architects_qml_models/` at the portal worktree root.
- Document one model only: the verified BreastMNIST four-qubit QCNN.
- Use Markdown and Mermaid source; do not generate PNG, SVG, circuit, or AI-created image assets.
- Base every architecture label on the serving implementation and versioned artifact metadata.
- Keep research limitations visible without crowding the main flow.

## Worktree safety

- Initial drafting worktree: `qml-portal-qcnn-integration`, detached `HEAD` at `dbfb0ac`
- Final location: `qml-portal-consolidation`, branch `codex/fh-genomic-risk-pathway`
- Both worktrees contained pre-existing unrelated changes that were left untouched.
- This task does not modify application code, generated routes, checkpoints, or research artifacts.

## Verification

- Confirm the document describes the implemented `28 x 28 -> 4 angles -> 4 -> 2 -> 1 qubits -> sigmoid -> threshold` path.
- Confirm the quantum convolution and pooling descriptions match `qml_inference/qcnn.py`.
- Confirm no generated image or transpiled-circuit asset is added.
- Review the rendered Mermaid structure at source level and check Git status for scope.

## Task log

- 2026-09-23: Selected BreastMNIST QCNN as the single trial model because it is the portal's verified runnable quantum-convolutional image model.
- 2026-09-23: Planned a presentation-level architecture that omits individual transpiled gates, hardware-provider plumbing, artifact hashes, and explanation reruns from the main flow.
- 2026-09-23: Added `architects_qml_models/breastmnist_qcnn_architecture.md` with two balanced Mermaid flowcharts and no generated image assets.
- 2026-09-23: Verified the documented `28 x 28 -> 4 angles -> 4 -> 2 -> 1 qubits -> sigmoid -> threshold` flow against the serving code and metadata; `git diff --check` reported no new whitespace errors.
- 2026-09-23: Added an implementation reference for the actual circuit blocks and the checkpoint's four model-state tensors: 30 convolution weights, 6 pooling weights, output scale, and output bias. Raw learned values remain in the versioned checkpoint.
- 2026-09-23: Relocated the architecture directory and this task record to `qml-portal-consolidation` so they live with the active portal changes.
- 2026-09-23: Replaced the generic QCNN-stage sketch with the implemented qubit flow: stage-one ring convolution, `q0 -> q1` and `q2 -> q3` pooling, stage-two `q1 -> q3` pooling, and final `q3` measurement.
- 2026-09-23: Added a short judge-facing training summary from run `e77cc845e586cfdd`, including the 32/16/32 split, two epochs, selected optimizer settings, configured 18-trial tuning scope, and 38 learned values. No completed tuning-study artifact was found, so the text does not claim that all trials ran.
- 2026-09-23: Expanded the approved format to every portal registry entry in the quantum-kernel, hybrid-QML, and QCNN families: 13 pages total, including the original BreastMNIST QCNN.
- 2026-09-23: Added `architects_qml_models/README.md` as the model index. Classical and deep-learning comparison entries remain outside this QML architecture set.
- 2026-09-23: Used recorded run artifacts for data sizes, training budgets, circuit families, parameter counts, tuning settings, availability, and scientific boundaries. No image assets were generated.

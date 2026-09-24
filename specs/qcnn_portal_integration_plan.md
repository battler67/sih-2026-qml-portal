# QCNN portal integration plan

- Branch: `codex/qcnn-portal-integration`
- Worktree: `qml-portal-qcnn-integration`
- Base: clean portal commit `ab5a758`; the separate `qml-portal-consolidation` worktree and its uncommitted FH changes remain untouched.
- Objective: promote and serve the existing BreastMNIST QCNN checkpoint from research run `e77cc845e586cfdd`, then connect a bounded image-upload workflow to the existing QML portal.

## Planned vertical slice

1. Copy the trusted checkpoint and immutable serving metadata into the versioned bundle, record SHA-256 hashes, and add a research-data replay verifier.
2. Add a training-free QCNN loader with exact spatial-pooling preprocessing and a cached PennyLane/Torch model.
3. Add a bounded PNG/JPEG inference endpoint under `/api/qml/v1` while preserving all JSON tabular endpoints.
4. Add a focused `/qml/imaging` route with upload, preview, validation, real API inference, technical flow, reduced features, and research-only warnings.
5. Add inference, preprocessing, bundle, API, and regression tests; run frontend lint/build and a browser-to-service smoke test where the environment permits.
6. Update README, integration specification, user guide, and this task record with measured verification and remaining limitations.

## Safety and claim boundaries

- No retraining, mocked scores, hardcoded predictions, surrogate model, external provider call, storage, or clinical claim.
- Uploaded images are held only for the request/browser session and are not logged.
- The selected model is a 32-train-sample smoke run with weak held-out evidence; integration makes it runnable, not clinically valid.
- Raw BreastMNIST images and participant-level predictions are not added to the portal repository.

## Verification log

- Source checkpoint promoted with original SHA-256 and immutable serving metadata.
- Five official-test images replayed against saved scores; maximum absolute error `2.7346502173841714e-08` at tolerance `1e-7`.
- Focused QCNN plus existing-service regression suite: 12 tests passed.
- Targeted frontend ESLint passed.
- Production frontend build passed and generated `/qml/imaging`.
- Browser-to-service smoke passed with an official BreastMNIST test image: the live page returned the real saved-checkpoint score, threshold, Pauli-Z expectation, four encoded angles and provenance; no Vite error overlay appeared.
- Final QML inference discovery suite passed: 12 tests, including PNG/JPEG, malformed/unsupported/oversized input, corrupt QCNN checkpoint startup, deterministic inference and existing tabular-score regressions.

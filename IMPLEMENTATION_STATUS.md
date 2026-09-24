# SIH139 hybrid QML platform implementation status

Last verified: 2026-09-22  
Active branch: `codex/qml-real-hardware-execution`

This file is the concise, current status for portal-visible disease workflows. The detailed feature
matrix and rationale are in [`specs/sih139_feature_gap_and_implementation.md`](specs/sih139_feature_gap_and_implementation.md).

## Runnable portal workflows

| Workflow | Live model(s) | Input | Explanation | Current status |
| --- | --- | --- | --- | --- |
| BreastMNIST imaging demo | Four-qubit hierarchical QCNN | PNG/JPEG or clearly labelled browser-generated synthetic test pattern, converted to 28x28 grayscale | Four-region mid-gray occlusion sensitivity (local simulator, explicitly labeled when the primary score is hardware-derived) | Runnable on local simulator; IBM and free-qBraid hardware paths integrated but live credentials currently rejected |
| Framingham teaching benchmark | Angle QKSVM PCA-2; matched logistic regression PCA-2 | 15-field form or one-row CSV | Patient-level training-median perturbation (local simulator, explicitly labeled for hardware results) | QKSVM runs locally and has IBM 256-circuit batch integration; qBraid is intentionally unsupported for this model; logistic remains classical |
| Cleveland heart-disease presence | Classical RBF-SVM | 13-field form or one-row CSV | Patient-level training-median perturbation over the four selected fields | Runnable diagnostic smoke demo; not future-risk prediction |
| Acute kidney injury | None | None | None | Unavailable: no verified dataset contract, preprocessor, checkpoint, threshold or held-out evidence exists |

Every enabled Run action above invokes a saved artifact and its fitted preprocessing. No enabled
control returns a hard-coded prediction. The service loads models once at startup, verifies bundle
hashes and performs no retraining or external data transmission.

The portal Model catalogue also displays every audited Framingham, Cleveland, BreastMNIST and WDBC
experiment. Each record has a descriptive `Best observed`, `Moderate` or `Experimental` tier plus an
independent `Runnable` or `Evidence only` state. `Best observed` means the highest saved AUPRC inside
that benchmark—not clinical superiority. Evidence-only entries have no enabled Run action.

## API and artifacts

- Service: `qml_inference.server`, default `http://127.0.0.1:8010`.
- Bundle: `qml_inference/artifacts/v1` with `manifest.json`, schemas, preprocessors, estimators,
  calibrators, cached quantum states and the QCNN checkpoint.
- Tabular prediction: `POST /api/qml/v1/predict`.
- Breast QCNN prediction: `POST /api/qml/v1/qcnn/breastmnist/predict` with PNG/JPEG bytes.
- Tabular report: `POST /api/qml/v1/report`.
- QCNN report: generated and downloaded locally from the real prediction response; nothing is stored.
- Hardware capabilities: `GET /api/qml/v1/hardware/capabilities`.
- Hardware preview: `POST /api/qml/v1/hardware/preview` with `modelId` and `provider`.
- Tabular hardware submission: `POST /api/qml/v1/hardware/jobs`.
- QCNN hardware submission: `POST /api/qml/v1/hardware/qcnn/breastmnist/jobs` with image bytes and query parameters.
- Hardware polling/results: `GET /api/qml/v1/hardware/jobs/{job_id}` and `/results`.

The tabular response includes model identity, class, calibrated research probability, decision value,
saved threshold, execution backend, measured inference-plus-explanation time, preprocessing provenance,
resource data and patient-level perturbation contributions. The QCNN response includes model score,
saved threshold, four encoded angles, circuit resources, measured time and four occlusion results.

## Explainability contract

- Clinical models replace one used input at a time with its fitted training-set median and rerun the
  complete saved preprocessing-plus-model pipeline. Contributions use the original field name/unit.
- The QCNN replaces one 14x14 pooled region at a time with mid-gray and reruns the saved circuit.
- These are local model-behaviour perturbations, not medical causation. QCNN occlusion is not Grad-CAM
  and must not be described as lesion localization.

## Known gaps and next work

1. Reconstruct and replay the UCI Pauli OQSVM serving contract. Its saved SVC uses a precomputed kernel,
   but the current research bundle omits the standalone training representations needed for new input.
2. Only after that replay passes, add the same-input RBF-SVM versus OQSVM comparison. The quantum smoke
   model trained on fewer rows, so its aggregate metrics are not a fair quantum-advantage comparison.
3. Promote a BreastMNIST classical image checkpoint with its exact preprocessing for live comparison.
   The saved pooled-logistic metrics do not include a reloadable estimator.
4. Start AKI as a research/data task, not a portal wiring task. Do not enable an AKI Run button until a
   leakage-safe split, fitted preprocessor, checkpoint, selected threshold, held-out metrics and replay
   test exist.
5. Refresh the backend-only IBM and qBraid credentials, then return one real result through the portal. On 2026-09-22 IBM discovery returned `InvalidAccountError` and qBraid returned HTTP 401, so no external job was submitted. Local simulation remains reliable and no quantum advantage is claimed.

## Verification record

Commands completed on 2026-09-22:

```powershell
.\.venv-qml\Scripts\python.exe -m unittest discover -s qml_inference/tests -v
bunx eslint src/components/QcnnImaging.tsx src/components/QmlPages.tsx src/lib/qml-api.ts
bun run build
```

- Backend/API: 12 tests passed, including valid/invalid tabular and image requests, replay data,
  explanation shape, inference timing, CORS and report behavior.
- Frontend lint: passed for every changed TypeScript/React file.
- Production build: passed for client, SSR and Nitro output. Existing chunk-size and
  `vite-tsconfig-paths` notices remain advisory.
- Browser: `/qml/imaging` accepted the repository dataset example and rendered real QCNN inference,
  timing, JSON download and the four-region explanation. `/qml/analyze` rendered a real matched
  logistic result and 15 patient-level contributions. Both routes had content and no Vite error overlay.

## Use and limitations

These workflows are research demonstrations and clinical decision-support prototypes only. They are
not medical devices, diagnoses, treatment recommendations or substitutes for clinician confirmation.
Use deidentified or synthetic inputs; the portal has no patient-history store, access control or
clinical deployment validation.


## QML real-hardware integration status

Status: **PARTIAL**.

- Circuit compatibility verified locally: QCNN Qiskit expectation matches the saved PennyLane circuit; QKSVM overlap circuits match cached-state fidelity after explicit PennyLane/Qiskit bit-order mapping.
- IBM integrated: QCNN (one circuit) and Framingham QKSVM (256 circuits in one SamplerV2 batch job).
- qBraid integrated: QCNN only, restricted to currently online, direct-access, QASM-compatible, zero-price QPUs.
- qBraid QKSVM remains unavailable because a faithful prediction needs 256 distinct overlap circuits and the qBraid path would create separate hardware jobs rather than one bounded batch.
- Classical logistic and RBF-SVM models are not quantum-hardware candidates.
- Live check on 2026-09-22: IBM `InvalidAccountError`; qBraid HTTP 401. No real job was accepted or returned, so completion is not claimed.
- Local jobs are asynchronous and in memory. Results include provider, device, remote job ID, shots, status, qubits, circuit count, transpiled depth/size and raw-count/no-mitigation declarations.

# SIH139 disease-pipeline feature-gap audit and implementation plan

Date: 2026-09-22  
Branch: `codex/sih139-end-to-end-pipelines`  
Base: verified QCNN portal integration commit `2128adb`

## Short implementation specification

Preserve the existing genomics portal and the four verified QML serving models. Extend only the
versioned, checksummed QML service and its existing React/TanStack Clinical Lab. Every enabled action
must call a fitted artifact with its saved preprocessing and threshold. Missing disease pipelines or
incomplete serving bundles remain explicitly unavailable; no random weights, mock scores, silent
retraining, or invented metrics are permitted.

Implementation order:

1. Add measured inference time and honest patient-level explanations to every model that is already
   runnable. Use single-feature median perturbation for EHR inputs and four-region mid-gray occlusion
   for the four pooled QCNN regions. Label these as model-behaviour evidence, not causation.
2. Add image-report download and surface the QCNN explanation as a 2x2 region overlay.
3. Promote the UCI Pauli OQSVM only after reconstructing/verifying the missing training representation
   required by its precomputed-kernel SVC; then add same-input RBF-SVM versus OQSVM comparison.
4. Evaluate a practical BreastMNIST classical checkpoint separately. Do not call MobileNet matched:
   it uses 224x224 ImageNet preprocessing, whereas the QCNN uses four pooled features. The matched
   pooled-feature logistic model has saved metrics but no reloadable checkpoint.
5. Keep AKI unavailable until a dataset/endpoint contract, leakage-safe split, fitted preprocessor,
   checkpoint, validation-selected threshold, held-out metrics and replay test exist.

## Feature-gap audit

| Pipeline | Feature | Status | Existing implementation | Missing work | Priority |
| --- | --- | --- | --- | --- | --- |
| Breast cancer | Image upload and preview | Complete | `src/components/QcnnImaging.tsx`; `/qml/imaging` | None for PNG/JPEG workflow | Critical complete |
| Breast cancer | Validation and preprocessing | Complete | `qml_inference/qcnn.py`; 5 MB bound, EXIF, grayscale, 28x28, 2x2 spatial pooling | None for current demo | Critical complete |
| Breast cancer | QCNN inference | Complete, demonstration-only | Verified run `e77cc845e586cfdd`; endpoint `/api/qml/v1/qcnn/breastmnist/predict` | Keep weak-evidence warning visible | Critical complete |
| Breast cancer | Classical live comparator | Partial | Same-split aggregate evidence; MobileNet, ResNet and small-CNN checkpoints exist in research results | No matched pooled-logistic checkpoint. Audit/promote practical CNN separately with exact preprocessing | High |
| Breast cancer | Same-input comparison | Partial | Aggregate metrics on the same official test subset | No live classical result for the uploaded image | High |
| Breast cancer | Image explainability | Complete | Four-region mid-gray occlusion sensitivity reruns the saved QCNN and is displayed as a 2x2 map | Preserve honest non-Grad-CAM/non-causation wording | Critical complete |
| Breast cancer | Downloadable report | Complete | Local JSON download uses the genuine prediction response | No server history by design | High complete |
| AKI | Clinical input | Missing | No AKI implementation found; only an old research prompt mentions AKI | Define cohort, endpoint, fields, units and provenance | Critical blocked by research artifacts |
| AKI | Preprocessing/model/baseline | Missing | No checkpoint, fitted preprocessor, schema, metrics or replay artifact | Run a leakage-safe research experiment before portal work | Critical blocked by research artifacts |
| AKI | Risk/explainability/report | Missing | No backend or frontend route | Cannot enable honestly until a verified model bundle exists | High blocked |
| Ischaemic heart disease | Clinical input | Complete for UCI diagnostic task | Existing `/qml/analyze` 13-field form and validator | Rename/describe consistently as diagnostic heart-disease presence, not early prediction | Critical |
| Ischaemic heart disease | Classical inference | Complete, smoke demo | UCI selected-feature pipeline, RBF-SVM, Platt calibrator, timing and patient-level perturbation | Keep diagnostic/limited-evidence wording visible | Critical complete |
| Ischaemic heart disease | Quantum inference | Partial / research-only | OQSVM SVC, calibrator, kernel cache, metrics and global ablation exist under research run `uci-smoke-20260829T194302Z-3b55c98a85f0` | Precomputed SVC bundle lacks standalone training inputs/states; reconstruct and replay before promotion | High |
| Ischaemic heart disease | Quantum-classical comparison | Partial | Aggregate RBF/OQSVM/HQMLP metrics are in evidence | No same-patient paired endpoint/UI; quantum trained on 50 rows versus classical 212, so fairness caveat is mandatory | High |
| Ischaemic heart disease | Explainability | Complete for live RBF-SVM | Patient-level training-median perturbation is returned and displayed using the four selected clinical fields | Add quantum explanation only if OQSVM is promoted | Critical complete for live model |
| Ischaemic heart disease | Downloadable report | Complete for single live model | `/api/qml/v1/report` and JSON download | Extend report with explanation/timing and future paired comparison | Medium |
| Framingham CHD teaching benchmark | Quantum and matched classical inference | Complete, educational | Two-qubit Angle QKSVM and matched PCA-2 logistic bundles | Add same-input paired display and local explanations | High |

## Reachability and control audit

- Enabled analysis controls call real local inference; no enabled QML Run button currently returns a
  hard-coded prediction.
- The QCNN page and endpoint are reachable only when the frontend/backend are launched from this
  worktree. A previously observed `Not Found` came from an older checkout occupying ports 8080/8010.
- OQSVM, HQMLP, MobileNet, ResNet and small-CNN results appear in evidence but are not selectable for
  live prediction. This is correct until their standalone serving contracts are verified.
- No disabled AKI Run button or placeholder page exists. Adding one before artifacts exist would be
  misleading.

## Unsupported presentation claims

- BreastMNIST and Cleveland are diagnostic benchmark tasks, not verified early-detection pipelines.
- No AKI model has been trained or integrated in the inspected repositories.
- No completed pipeline is clinically validated or suitable for diagnosis/treatment decisions.
- QML inference uses local ideal simulation; the portal has no verified QML real-hardware execution.
- Current results do not establish quantum predictive or computational advantage.
- QCNN sigmoid output is uncalibrated and must be called a model score, not confidence or patient
  probability. UCI/Framingham calibration is validation-fitted but remains research calibration.

## Verification record

- Repository instructions, QML portal docs, serving manifests and sibling QML research experiment
  specifications were inspected before implementation.
- Current branch started clean; prior QCNN integration and unrelated worktrees were preserved.
- AKI search found no implementation or artifacts beyond a planning-prompt mention.
- Selected QCNN and UCI research run file inventories were inspected. The UCI run includes fitted
  RBF/OQSVM/HQMLP artifacts and global explanations; the QCNN result tree includes image-network
  checkpoints but no reloadable matched pooled-logistic checkpoint.

Further implementation and test results will be appended here as each slice is verified.

## Implemented slice: explanations, timing and QCNN report

- Added measured inference-plus-explanation time to every live prediction response.
- Added patient-level training-median perturbation for the Framingham and Cleveland live models. The
  complete saved preprocessing and fitted estimator are rerun for each perturbation.
- Added four-region mid-gray occlusion sensitivity for QCNN. The displayed method is explicitly not
  Grad-CAM, lesion localization or medical causation.
- Added a local QCNN JSON report download from the genuine response.
- Kept QML circuit execution accounting explicit: the QKSVM result includes the baseline plus 15
  feature perturbations; the QCNN result includes the baseline plus four regional perturbations.

Verification on 2026-09-22:

- `python -m unittest discover -s qml_inference/tests -v`: 12 passed.
- Targeted ESLint for all changed TypeScript/React files: passed.
- `bun run build`: passed client, SSR and Nitro production builds.
- Browser `/qml/imaging`: repository image uploaded; real checkpoint result, timing, report control and
  2x2 occlusion values rendered; no Vite error overlay.
- Browser `/qml/analyze`: synthetic Framingham record produced a real saved-model result and 15
  patient-level contributions; no Vite error overlay.
- Model visibility follow-up: `/qml` now labels all four serveable models as Runnable and gives each a
  descriptive tier. `/qml/evidence` is a complete Model catalogue: every audited Framingham summary,
  Cleveland model and BreastMNIST/WDBC run is visible with a tier and Runnable/Evidence-only state.
  Production build, targeted ESLint and browser checks passed with no overlay or captured console error.
- QCNN sample-input follow-up: `/qml/imaging` now has a **Load synthetic demo image** control. It
  deterministically generates a 28x28 PNG in the browser, labels it as non-medical, and requires the
  user to press Run. Browser verification completed the genuine checkpoint inference, timing, encoded
  angles and four-region explanation with no overlay or captured console error.

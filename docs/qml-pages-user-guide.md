# QML Clinical Lab user guide

Open **QML Clinical Lab** from the portal landing page or dashboard, or visit `/qml`. The lab is a research-use interface for saved models. It does not diagnose disease, estimate a person's clinical prognosis, or recommend treatment.

## Supported workflows

| Workflow | Live models | What the label means |
| --- | --- | --- |
| Framingham teaching benchmark | Angle quantum-kernel SVM (PCA-2); matched logistic regression (recommended) | Educational 10-year incident CHD benchmark. The audited teaching mirror is not clinically validated. |
| Cleveland heart disease presence | Classical RBF SVM | Diagnostic dataset, single small smoke run. It does not measure future disease onset. |
| BreastMNIST imaging demonstration | Four-qubit hierarchical QCNN | Image-classification smoke run trained on 32 images for two epochs; weak held-out evidence and no clinical validation. |
| Synthetic FH genomics pathway | Rule-reproduction logistic and four-qubit Angle QKSVM | Deterministic synthetic referral-rule exercise, not a validated FH detector or personal genomic analysis. |

Other UCI, WDBC, VQC, HQMLP and Framingham experiments appear in the evidence/catalogue only. No raw DNA sequence is accepted by these tabular models. The portal's genomic analysis remains a separate workflow.

## Run an analysis

1. Choose **Analyze**, then the workflow and model, or use **Run** on a runnable EHR catalogue card to preselect that exact model. Only models with a verified serving bundle can be selected.
2. Click **Load synthetic demo** for a visibly labelled fabricated example, type all field values, or upload a one-row CSV. The CSV needs a header containing exactly the field names shown by the form. Empty Framingham cells use the model's saved median imputer; omitted columns and UCI empty cells are rejected.
3. Check the units and dataset code descriptions beside each field. Enter values within the shown compatibility bounds. These are dataset bounds, **not** healthy or clinical reference ranges.
4. Click **Run analysis**. A loading state appears while the local model runs. A validation or service error states what needs attention; no result is invented on failure.
5. The result page shows the research class, calibrated model probability, saved decision threshold and decision value, measured inference-plus-explanation time, ordered inputs, transformed features, bundle/preprocessing provenance and backend. The patient-level model-behaviour panel reruns the complete saved pipeline after replacing one input at a time with its training-set median. These signed changes are local model sensitivity, not medical causation. **Generate report** creates an ephemeral local JSON report with the same evidence and disclaimer; **Download JSON** saves it on your device. No history is stored by the portal.

The Framingham field names are `SEX, AGE, EDUC, CURSMOKE, CIGPDAY, BPMEDS, PREVSTRK, PREVHYP, DIABETES, TOTCHOL, SYSBP, DIABP, BMI, HEARTRTE, GLUCOSE`. The form displays age in years; cigarettes per day; total cholesterol and glucose in mg/dL; blood pressure in mmHg; BMI in kg/m²; heart rate in beats/min; and numeric dataset codes for the remaining fields. The Cleveland form displays its 13 exact fields and units. Use the labels/codes from the selected research dataset; do not substitute a different coding scheme.

## Run the QCNN image demonstration

The **Breast imaging models** card on `/qml` and the runnable QCNN catalogue
card's **Run QCNN** link both open this workflow. Other imaging experiments
remain in the catalogue with an **Evidence only** tag and no Run control.

Open `/qml/imaging`. For a no-file functional test, click **Load synthetic demo image**, then **Run QCNN prediction**. The generated 28×28 grayscale pattern stays in the browser and is not a BreastMNIST datapoint, patient scan or medically meaningful example. Alternatively, select one PNG or JPEG up to 5 MB, review the local preview, and run the QCNN. The service converts the image to 28×28 grayscale, pools four 14×14 regions, maps them to four angles, executes the saved 4→2→1 circuit and returns its sigmoid malignant score and saved threshold. It then replaces each pooled region with mid-gray and reruns the QCNN to show a four-region occlusion-sensitivity map. This is not Grad-CAM, lesion localization or medical causation. **Download JSON report** saves the real response locally. The displayed score is uncalibrated and must not be interpreted as an individual clinical probability. Uploaded image bytes are not persisted or logged.

## Read the output and comparison

The class is determined by a **model-specific saved threshold**. A calibrated model probability is a transformation of that model's score on research data, not a measured chance of disease for an individual. The decision value is the estimator's raw margin. PCA components are mathematical reductions, not identified biomarkers. An empty uncertainty field means individual uncertainty was not validated. Aggregate seed spread or confidence intervals describe benchmark variation and must not be read as confidence in a particular result.

On **Model catalogue**, every audited experiment remains visible. `Best observed` is the highest saved AUPRC within that benchmark, `Moderate` is within 0.10 AUPRC of it, and `Experimental` covers the remaining smoke results. These descriptive tiers do not imply statistical significance or clinical readiness. A separate `Runnable` badge means the checkpoint, preprocessor, schema and endpoint replay successfully; `Evidence only` models cannot be run from the portal. Compare the saved quantum and matched-feature classical Framingham results first. The full-feature RBF SVM used a larger training set, so its numbers are a separate reference. UCI and QCNN values come from smoke/checkpoint runs and are labelled accordingly. AUROC measures ranking across thresholds; AUPRC summarizes precision and recall for the positive class and is useful when positives are uncommon. Sensitivity is the fraction of positives identified, specificity the fraction of negatives identified. Balanced accuracy averages sensitivity and specificity. These population metrics do not validate an individual result.

The Angle QKSVM defaults to an **ideal two-qubit simulator** and classical calculations against cached training states. When IBM access is configured, the hardware option runs 256 finite-shot overlap circuits as one Sampler job before applying the unchanged SVM and calibrator. The QCNN can select IBM or a currently online free qBraid QPU. Hardware output is noisy raw-count evidence, not the saved benchmark protocol, and it does not establish quantum advantage.

## Common problems

- **Service unavailable:** start the Python 3.12 QML inference service and check `/api/qml/v1/health`. The frontend needs `VITE_QML_API_BASE_URL` pointing to it.
- **Health works but the page says unavailable:** check the browser's exact origin (including port) against `QML_CORS_ORIGINS`. An older QML process can still own port 8010 with a stale origin list; a request from `http://127.0.0.1:8081` then returns HTTP 403 even though a direct health check returns 200. Stop that specific old listener and restart the QML service with the portal origin allowed.
- **Invalid CSV:** provide one data row with exact model-specific column names, no outcome column, numeric codes and values, and a file under the upload size limit.
- **Invalid QCNN image:** provide a readable PNG or JPEG no larger than 5 MB. The portal converts RGB to grayscale and resizes to 28×28; other media types are rejected.
- **Missing or out-of-range value:** fill every required key and use the bounds shown in the form. An explicit blank Framingham cell is handled by its saved imputer; an omitted column is not.
- **Bundle unavailable/corrupt:** an operator must restore the verified versioned bundle. The service refuses startup if its hashes or versions fail.
- **Result disappeared after refresh:** results and reports are deliberately held only in the current page session. Run the synthetic/manual input again; download a report if you need to retain it locally.

Use synthetic examples for demonstrations. Do not enter identifiable patient data into a research prototype. Simulator mode sends no QML input externally. A real-hardware selection requires a device preview and confirmation; only the encoded quantum circuit is submitted to the selected provider, while raw image bytes and clinical field names remain in the local service.


## Run on real quantum hardware

1. Keep **Local ideal simulator** for the reliable default path.
2. For a quantum model, choose IBM Quantum or an enabled qBraid option and select 32–1024 shots.
3. The service previews a live compatible device. Read the device, shot and circuit-count confirmation carefully.
4. Confirm once to submit. The page polls queue/running/completed status and shows the provider, device, remote job ID, shots, circuit count, provider status and transpiled depth when returned.
5. Provider errors are shown without credentials or stack traces. Retry only after checking the provider account; a timed-out local poll does not prove an accepted remote job was canceled.

qBraid is intentionally disabled for the QKSVM because one prediction needs 256 different overlap circuits. Classical logistic and RBF-SVM models have no hardware choice. Hardware explanations are still calculated locally and labeled `local_ideal_simulator`; only the primary score uses QPU counts.

As of 2026-09-22 the stored credential variables are present but rejected by both providers (IBM `InvalidAccountError`, qBraid HTTP 401). The selector and flow are integrated, but no real result has returned, so the integration status is **PARTIAL**.

# QML real-hardware execution

Date: 2026-09-22  
Branch: `codex/qml-real-hardware-execution`  
Base: `86d1354`

## Objective

Add explicit, provider-selectable IBM Quantum and qBraid execution to technically compatible live
QML models while preserving the existing local simulator as the default. Provider credentials stay
backend-only and are never copied into source, frontend variables, API payloads, logs or artifacts.

## Compatibility audit

| Runnable model | Quantum hardware status | Reason |
| --- | --- | --- |
| BreastMNIST four-qubit QCNN | Compatible | The learned circuit can be reproduced gate-for-gate with four measured Qiskit qubits. Finite-shot Pauli-Z expectation feeds the unchanged learned output scale, bias and saved threshold. |
| Framingham two-qubit Angle QKSVM | Feasibility-gated | One prediction requires a fidelity kernel against 256 saved training states. A faithful hardware implementation therefore needs 256 measured overlap circuits before the unchanged SVM/calibrator can run. This is technically possible but expensive; it must stay unavailable when circuit/job bounds or provider access cannot support it. |
| Matched Framingham logistic regression | Not applicable | Classical model; no quantum circuit exists. |
| Cleveland RBF-SVM | Not applicable | Classical model; no quantum circuit exists. |

## Security and execution rules

- The simulator remains the default and must work with no provider SDK or credential.
- Load `QBRAID_API_KEY`, `QISKIT_IBM_TOKEN`, channel, instance and allow-list from backend environment
  only. Never return credential-shaped values or raw provider exceptions.
- Real submission requires an explicit confirmation field and provider choice.
- Bound shots, circuit count, polling time and request size. Do not retry automatically after a remote
  job may have been accepted.
- Discover and revalidate live hardware immediately before submission.
- IBM circuits must be transpiled to the selected backend ISA. qBraid input compatibility must be
  checked from live metadata and conversion/validation remains provider-authoritative.
- Preserve exact model preprocessing, learned parameters, class mapping and threshold. Hardware noise
  changes the measurement estimate, not the model definition.
- Return raw counts plus provider, device, remote job ID, status, shots, logical/transpiled resources,
  elapsed time, score and prediction. No error mitigation or quantum-advantage claim.

## Implemented architecture

1. Add QML-specific circuit builders that reproduce the live QCNN and Angle-QKSVM feature map.
2. Add a small provider-neutral hardware service with injected IBM/qBraid adapters for focused tests.
   Reuse the repository's existing discovery, sanitization, transpilation and result-normalization
   conventions without coupling the Python 3.12 QML service to FastAPI/search request models.
3. Add capability/preview, submission, status and result endpoints under `/api/qml/v1/hardware`.
   Local jobs are in-memory and asynchronous; a restart loses local polling state, while the returned
   remote job ID remains usable provider-side.
4. Add backend selector, shot selector, explicit confirmation and progress/result metadata to the
   existing tabular and QCNN pages. Classical models show hardware as not applicable.
5. Add mocked provider/circuit/API tests, existing regression suites, lint/build and browser checks.
6. Only after local verification, load the existing untracked credentials into the process and attempt
   one bounded job per provider/model where access, compatibility and quota permit. Record exact
   outcomes without exposing credentials.

## Definition of complete

The integration is COMPLETE only if every technically compatible live quantum model has returned at
least one genuine provider result through the portal. If one provider/model is unsupported, blocked by
quota/access, or no remote result returns, status is PARTIAL. Mocked tests or successful submission
without a retrieved result do not count as complete.

## Task log

- Read repository hardware/QML documentation and existing provider/circuit/service architecture.
- Confirmed current feature worktree was clean and created this dedicated branch.
- Located provider credential variable names in an untracked sibling backend environment without
  reading or printing values. Current QML environment lacks Qiskit/provider SDKs; the existing genomic
  backend environment has Qiskit 2.5.2, qiskit-ibm-runtime 0.49.0 and qBraid 0.12.2.


## Verification and outcome

- Added exact Qiskit circuit builders for the saved QCNN and PCA-2 Angle QKSVM.
- Corrected and tested PennyLane wire-order to Qiskit little-endian statevector mapping.
- Added provider-selectable IBM/qBraid adapters, live discovery, free-qBraid filtering, IBM ISA transpilation, bounded shots/timeouts, explicit confirmation, asynchronous local jobs, polling and structured results.
- Added portal selectors and hardware metadata while keeping simulator execution as the default.
- Added focused service, circuit-equivalence and API tests. Complete QML suite: 18 tests passed.
- Frontend: 28 Bun tests passed; production client/SSR/Nitro build passed; targeted changed-file lint passed. Repository-wide lint remains blocked by the existing CRLF/Prettier baseline (15,123 reported issues across many untouched files).
- Live provider check: IBM credential present but rejected with `InvalidAccountError`; qBraid credential present but discovery returned HTTP 401. No external job was submitted or billed.

Final status: **PARTIAL**. Software integration is present and locally verified, but the definition of complete requires a real provider result to return through the platform.

# Real-hardware quantum execution

Date: 2026-07-30

## Goal

Add an explicit **Run on Real Hardware** workflow beside the existing Aer
**Run Search** action. The backend must build the selected algorithm's actual
Qiskit circuit, discover currently accessible hardware, select an efficient
device from live metadata, submit only after explicit user action, and expose
a separate hardware-results page.

## Branch

- `feature/real-hardware-routing`

## Security and quota boundaries

- Never put IBM or qBraid credentials in React, API responses, logs, source
  files, test fixtures, or `VITE_*` environment variables.
- Read rotated credentials only from backend environment variables.
- The credentials pasted into the original prompt are considered compromised
  and are not used by this implementation.
- Automated verification uses mocks only. It must not discover live account
  devices or submit real jobs.
- One button click prepares exactly one representative bounded genomic window.
  It does not fan out `maxWindows` circuits across scarce QPU capacity.
- A confirmed click may make at most one qBraid submission attempt followed by
  at most one IBM submission attempt when qBraid fails. It never retries a
  second device from the same provider.
- Submission requires a request field confirming real-hardware execution.
- Shots are capped separately for hardware execution.

## Official API research

- qBraid device metadata exposes QRN, status, qubit count, queue depth,
  accepted input types, and per-task/per-shot/per-minute pricing.
- qBraid Runtime performs program conversion, device transforms, validation,
  preparation, and submission when `device.run(...)` is called.
- qBraid does not provide managed IBM access; IBM jobs require the user's own
  IBM credentials.
- IBM Runtime exposes operational backend discovery and queue metadata.
  Hardware circuits must be transpiled to the selected backend's ISA before
  `SamplerV2` job-mode submission.
- IBM Open Plan workloads use job or batch mode rather than sessions.

References:

- https://docs.qbraid.com/v2/api-reference/rest/get-device
- https://docs.qbraid.com/sdk/user-guide/runtime/components
- https://docs.qbraid.com/v2/lab/user-guide/quantum-jobs
- https://qiskit.qotlabs.org/docs/guides/hello-world
- https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/runtime-service
- https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/sampler-v2

## Device-selection policy

1. Build the actual circuit first; its `num_qubits` is the required capacity.
2. qBraid candidates must be `ONLINE`, `QPU`, accept QASM/Qiskit input, have
   sufficient qubits, and report zero per-task, per-shot, and per-minute
   pricing.
3. IBM candidates must be accessible to the configured account, operational,
   non-simulators, sufficient in capacity, and optionally restricted by the
   configured backend allow-list.
4. Rank all candidates by:
   - fewest unused qubits (`device_qubits - required_qubits`);
   - lowest queue depth;
   - stable provider/device identifier.
5. Revalidate the chosen device immediately before submission.
6. If the selected qBraid submission fails, try the best eligible IBM device
   once. If IBM is unavailable or also fails, terminate the local job and show
   both sanitized provider failures to the user.

This policy prioritizes fitting a circuit onto the smallest adequate processor
instead of consuming a much larger QPU merely because its queue is marginally
shorter. Queue depth breaks ties between similarly sized devices.

## Planned backend changes

- Add provider-neutral device, submission, job, and result models.
- Add qBraid and IBM adapters with lazy optional imports.
- Add a hardware circuit builder for FRQI, Grover/QGSA, and Hybrid.
- Add representative-window preparation without running Aer.
- Add in-memory asynchronous hardware-job management.
- Add device-preview, submission, status, and result API endpoints.
- Add mocked tests for filtering, ranking, circuit construction, submission,
  qBraid-to-IBM fallback, terminal all-provider failure, result mapping,
  credential absence, and endpoint behavior.
- Add optional runtime dependencies and backend-only environment examples.

## Planned frontend changes

- Add **Run on Real Hardware** beside **Run Search**.
- Show a confirmation dialog explaining provider quotas and one-window scope.
- Add `/quantum-hardware-results` with submission progress, mapped device
  rationale, raw hardware counts, probabilities, circuit metrics, selected
  genomic window, provider/remote job identifiers, and limitations.
- Do not include ideal/noisy/mitigated comparison controls on this page.

## Known limitations and decisions

- Real-hardware mode is a bounded demonstration run, not an entire-database
  quantum execution and not a claim of end-to-end quantum advantage.
- It executes the first accepted representative window after the same
  retrieval/normalization/window-generation rules. It does not use Aer to
  pre-rank windows before QPU submission.
- qBraid's zero-price metadata is treated as the eligibility signal; account
  entitlements and provider-side limits can still reject a submission.
- Automatic fallback is cross-provider only: qBraid to IBM. There is no retry
  across multiple qBraid devices or multiple IBM devices.
- A provider can accept a remote job and then fail while waiting for or
  decoding its result. Because provider SDK exceptions do not always state
  whether quota was consumed, fallback can result in two external jobs for one
  confirmed click. The UI confirmation must disclose this bound.
- IBM access/time entitlement cannot be inferred perfectly from backend
  metadata; the provider remains authoritative at submission time.
- Queue depth is a changing snapshot and does not guarantee start time.
- Logical qubit fit does not guarantee that transpilation will produce a
  shallow or scientifically useful hardware circuit. Depth and connectivity
  can make a nominally fitting circuit impractical.
- No error mitigation is applied. Returned counts are raw device measurements.
- Jobs are tracked in process memory, consistent with the existing search-job
  service. A backend restart loses local tracking, though provider job IDs are
  returned for external recovery.
- Provider SDK availability and credentials are optional. The existing Aer
  workflow continues working when hardware dependencies are absent.
- Provider result waiting is bounded by
  `QDNA_HARDWARE_RESULT_TIMEOUT_SECONDS` (default 3,600 seconds). A local
  timeout cannot prove that an already accepted remote job was canceled.

## Task log

- Confirmed `quantum-helix-lab-full` is the clean current full-stack repository
  and created branch `feature/real-hardware-routing`.
- Read current IBM Runtime and qBraid Runtime/device/job documentation.
- Chose mock-only automated verification to preserve 10 IBM service minutes
  and the qBraid daily job allowance.
- Added `quantum_search_api/services/hardware/` with provider-neutral models,
  one-window circuit preparation, qBraid/IBM adapters, deterministic selection,
  shot capping, explicit confirmation, and asynchronous in-memory job tracking.
- Added hardware preview, create-job, status, and result routes in
  `quantum_search_api/app.py`.
- Added backend-only environment examples and the qBraid/IBM runtime
  dependencies. Preserved the existing NCBI environment variables.
- Added **Run on Real Hardware** beside **Run Search**, including a quota and
  scope confirmation dialog.
- Added `/quantum-hardware-results` with raw counts, resource mapping,
  representative-window data, circuit/ISA metrics, remote provider ID, and
  limitations. No simulated noise or mitigation controls are present.
- Added `docs/REAL_HARDWARE_EXECUTION.md` and linked it from the README.
- Installed qBraid 0.12.2 and qiskit-ibm-runtime 0.48.0 only in the ignored
  repository virtual environment to verify current imports/signatures. No
  credentials were loaded and no provider API was called.
- Verification:
  - new mocked hardware tests: `9 passed`;
  - complete backend suite: `56 passed`;
  - one complete-suite rerun briefly hit the existing 2.5-second asynchronous
    polling limit in `test_candidate_validation_is_on_demand`; the test passed
    alone and the next complete rerun passed `56 passed`, so no unrelated
    timing threshold was changed;
  - targeted ESLint: passed for `QuantumSearch.tsx`,
    `QuantumHardwareResults.tsx`, and the new route;
  - frontend production build: passed and generated the new TanStack route;
  - qBraid 0.12.2 locally converted a measured Qiskit circuit to OpenQASM 3;
  - secret scan found only documented placeholder values;
- no qBraid or IBM device discovery or job submission was performed.
- Follow-up fallback requirement:
  - record qBraid submission failures in the job status;
  - try the best eligible IBM candidate once;
  - expose a terminal **hardware calls failed** state with all sanitized
    provider errors when neither provider succeeds;
  - bound provider result waiting so a non-responsive provider eventually
    reaches fallback or terminal failure;
  - update the confirmation language and documentation to disclose that one
    click can make up to two cross-provider attempts.
- Follow-up implementation and verification:
  - implemented one-attempt qBraid to one-attempt IBM routing;
  - completed IBM results retain the sanitized qBraid failure and identify the
    fallback selection policy;
  - failed jobs expose both provider failures on the hardware-results page;
  - added a configurable 3,600-second default provider-result timeout;
  - restored placeholder-only values in the tracked backend environment
    template after finding actual-looking credentials there;
  - focused hardware tests: `11 passed`;
  - complete backend suite: `58 passed`;
  - targeted frontend ESLint: passed;
  - frontend production build: passed;
  - source scan found no non-placeholder qBraid or IBM credentials.

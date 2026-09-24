# Real Quantum Hardware Execution

## What the feature does

The quantum-search page now has two separate execution paths:

- **Run Search** keeps the existing bounded multi-window Aer simulator
  workflow.
- **Run on Real Hardware** builds one actual FRQI, Grover/QGSA, or Hybrid
  measured circuit and submits it to one resource-matched physical QPU.

Real-hardware execution has its own `/quantum-hardware-results` page. It shows
the selected provider and device, selection rationale, remote job ID, raw
counts and probabilities, logical/ISA metrics when available, the exact
bounded window sent to hardware, and limitations. It intentionally has no
ideal/noisy/mitigated comparison controls.

## Credential setup

Credentials are backend-only. Never place either token in React source,
`VITE_*` variables, URLs, API requests from the browser, screenshots, or Git.

Any credential previously pasted into chat or a plaintext prompt must be
revoked and rotated before use.

Copy:

```powershell
Copy-Item quantum_search_api\.env.example quantum_search_api\.env
```

Then configure one or both providers in the untracked
`quantum_search_api/.env` file:

```env
QBRAID_API_KEY=your_rotated_qbraid_key

QISKIT_IBM_TOKEN=your_rotated_ibm_token
QISKIT_IBM_CHANNEL=ibm_quantum_platform
QISKIT_IBM_INSTANCE=
QDNA_IBM_BACKENDS=ibm_fez,ibm_marrakesh,ibm_kingston

QDNA_REAL_HARDWARE_MAX_SHOTS=1024
QDNA_HARDWARE_RESULT_TIMEOUT_SECONDS=3600
```

`QDNA_IBM_BACKENDS` is an allow-list. Set it to the backend names currently
available to the account. Backend names and access can change, so the list
must be maintained rather than treated as a permanent IBM inventory.

The application continues to start and the Aer path continues to work if
neither hardware provider is configured.

## Safe execution flow

1. The user configures the search and runs **Estimate**.
2. The user clicks **Run on Real Hardware**.
3. A confirmation dialog explains that the action consumes one external job.
4. The backend retrieves and normalizes inputs using the existing rules.
5. It chooses the first accepted A/C/G/T-only bounded window. It does not run
   Aer to rank windows first.
6. It builds the algorithm's measured Qiskit circuit.
7. It discovers live provider devices using backend credentials.
8. It filters and ranks candidates.
9. It rechecks the selected provider immediately before submission.
10. It submits at most `QDNA_REAL_HARDWARE_MAX_SHOTS`.
11. If a qBraid submission fails, it tries the best eligible IBM device once.
12. If IBM is unavailable or also fails, the local job enters a terminal
    **hardware calls failed** state and returns sanitized errors for every
    attempted provider.
13. The dedicated page polls the local job and shows either raw provider
    results or those terminal provider failures.

There is no same-provider retry. One confirmation can make at most one qBraid
attempt and one IBM fallback attempt. This means a provider that accepts a job
and subsequently fails while returning its result can still consume quota
before fallback occurs.

Provider result waiting is bounded by
`QDNA_HARDWARE_RESULT_TIMEOUT_SECONDS` (default 3,600 seconds, constrained to
30–86,400 seconds). A timeout follows the same fallback/failure rules.

## Device eligibility

### qBraid

A qBraid device is eligible only when current metadata reports:

- status `ONLINE`;
- type `QPU`;
- enough qubits for the actual circuit;
- QASM 2 or QASM 3 input support;
- zero `perTask`, `perShot`, and `perMinute` pricing.

Account entitlements, daily limits, provider maintenance, and provider-side
validation remain authoritative even when metadata passes these filters.

### IBM

An IBM backend is eligible only when:

- it is accessible to the configured IBM account;
- it is operational and not a simulator;
- its name is in `QDNA_IBM_BACKENDS`, when that allow-list is non-empty;
- it has enough qubits for the actual circuit.

IBM circuits are transpiled to the selected backend's ISA with Qiskit's preset
pass manager before `SamplerV2` job-mode submission. Sessions are not used.

## Selection algorithm

For each eligible candidate:

```text
unused_qubits = device_qubits - circuit_logical_qubits
```

Candidates are ordered by:

1. smallest `unused_qubits`;
2. smallest queue depth;
3. provider and device ID for deterministic ties.

This is a best-fit policy: a 13-qubit circuit chooses a suitable 20-qubit QPU
over an otherwise idle 156-qubit QPU. A circuit near 156 qubits can select an
accessible 156-qubit IBM backend because smaller devices cannot fit it.

Queue depth is only a snapshot. It is not a guaranteed start-time estimate.

## API

Metadata-only device preview:

```http
POST /api/quantum-search/hardware/preview
```

Body: the normal `SearchRequest`. This endpoint builds the representative
circuit and discovers devices but does not submit a job.

Confirmed submission:

```http
POST /api/quantum-search/hardware/jobs
```

```json
{
  "searchRequest": {
    "querySource": "pasted",
    "querySequence": "ACGT",
    "referenceSequence": "ATGT",
    "databaseScope": "pasted_sequence",
    "algorithm": "hybrid",
    "shots": 128
  },
  "confirmRealHardware": true
}
```

Status and result:

```http
GET /api/quantum-search/hardware/jobs/{job_id}
GET /api/quantum-search/hardware/jobs/{job_id}/results
```

## Limitations

- The portal does not require a successful frontend estimate before opening
  the real-hardware confirmation. This removes stale or conservative UI
  eligibility gates; it does not bypass backend circuit validation or provider
  restrictions. Circuit construction, live device capacity, topology,
  transpilation, account entitlements, and provider limits can still reject
  the request before an external job is accepted.
- Pasted and FASTA inputs can contain up to 100,000 bases, but real-hardware
  execution compiles only the configured bounded quantum window. A successful
  156-qubit planning estimate is not a claim that both complete long strings
  are loaded coherently.
- Only one representative bounded window is prepared per click. It can be
  submitted once to qBraid and once to IBM when fallback is needed. This is
  not a full multi-window hardware search.
- The representative window is selected before hardware execution and without
  Aer ranking.
- Classical strings are compiled into circuit gates; free QRAM is not assumed.
- Grover `auto` mode uses a classical exact-match count to choose its
  small-example iteration count.
- Logical qubit fit does not imply practical hardware execution. Connectivity,
  native-gate decomposition, transpiled depth, calibration, and decoherence
  can make a fitting circuit too noisy or too expensive in quantum time.
- FRQI nucleotide states are nonorthogonal and its strip result is a bounded
  encoded similarity signal, not BLAST alignment.
- Hybrid is bounded mismatch localization, not edit distance or a complete
  genomic-search algorithm.
- Raw hardware counts include real noise. No readout correction, zero-noise
  extrapolation, dynamical decoupling, twirling, or other mitigation is
  enabled by this feature.
- Local hardware job records are in memory. A FastAPI restart loses local
  polling state. Retain the remote provider job ID for provider-side recovery.
- Device availability, pricing metadata, names, quotas, and APIs can change.
  The provider remains the final authority.
- A result timeout bounds local waiting but does not guarantee that a remote
  provider canceled an already accepted job. Inspect the provider account
  before manually resubmitting after a timeout.

## Verification without consuming jobs

```powershell
python -m pytest quantum_search_api\tests\test_hardware_execution.py -q --disable-warnings
python -m pytest quantum_search_api\tests -q --disable-warnings
npm run build
```

The hardware tests use fake provider metadata, fake queues, and fake results.
They do not use account credentials and do not submit external jobs.


## QML Clinical Lab hardware execution

The QML service has a separate, explicit provider selector. Local ideal simulation remains the default.

| Model | IBM | qBraid | Notes |
| --- | --- | --- | --- |
| BreastMNIST 4-qubit QCNN | Integrated | Integrated for online free QPUs | One measured circuit; raw finite-shot Z expectation feeds the unchanged learned scale, bias and threshold. |
| Framingham 2-qubit Angle QKSVM | Integrated | Unavailable | A faithful prediction needs 256 overlap circuits. IBM submits them as one SamplerV2 batch; qBraid would require separate jobs. |
| Framingham logistic / Cleveland RBF-SVM | Not applicable | Not applicable | Classical estimators have no quantum circuit. |

QML endpoints:

```text
GET  /api/qml/v1/hardware/capabilities
POST /api/qml/v1/hardware/preview
POST /api/qml/v1/hardware/jobs
POST /api/qml/v1/hardware/qcnn/breastmnist/jobs
GET  /api/qml/v1/hardware/jobs/{job_id}
GET  /api/qml/v1/hardware/jobs/{job_id}/results
```

Every submission requires `confirmRealHardware=true`, a provider choice and 32–1024 shots by default. The service discovers an eligible device again immediately before submission. IBM circuits are transpiled to the backend ISA; qBraid validates/converts the single QCNN circuit. Errors expose only sanitized provider/error types. Tokens remain process environment values and are never returned or logged.

Hardware primary scores use raw counts without mitigation. To avoid multiplying QPU work, QCNN occlusion and QKSVM feature perturbation explanations continue to run locally and the response marks `explainability.executionBackend=local_ideal_simulator`.

Live verification on 2026-09-22 found both credential variables present, but IBM rejected account initialization with `InvalidAccountError` and qBraid device discovery returned HTTP 401. No job was submitted. QML hardware integration is therefore **PARTIAL**, not complete, until refreshed credentials produce a result through the portal.

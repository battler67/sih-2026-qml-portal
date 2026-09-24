# Unbounded Hybrid Hardware Testing

## Branch

`feature/unbounded-hybrid-hardware-testing`

## Scope

- Remove the portal's fixed 32-base Hybrid Mutation limit.
- Allow equal-length, non-empty A/C/G/T Hybrid inputs through resource
  estimation, circuit construction, local execution requests, and real-hardware
  preparation.
- Keep this experimental behavior isolated from `main`.
- Preserve general input limits, equality/alphabet validation, backend circuit
  construction errors, provider discovery, live device capacity, topology,
  account entitlements, quotas, and explicit hardware confirmation.

## Scientific boundary

Removing the fixed input-length guard does not make large Hybrid circuits
practical. QROM loading, multi-controlled-gate decomposition, YLC repetitions,
routing, and raw hardware noise still grow rapidly. A successfully submitted
job is not evidence of quantum advantage.

## Planned verification

- Focused Hybrid schedule/circuit and API tests.
- A test showing a length greater than 32 is no longer rejected solely because
  of its length.
- Python compilation checks.
- Focused frontend tests and production build if frontend files change.

## Changed files

- `quantum_search_api/services/quantum/hybrid_search.py`
- `quantum_search_api/services/search/search_orchestrator.py`
- `quantum_search_api/tests/test_hybrid_search.py`
- `quantum_search_api/tests/test_search_orchestrator.py`
- `quantum_search_api/tests/test_hardware_execution.py`
- `src/components/QuantumSearch.tsx`
- `docs/QUANTUM_SEARCH.md`
- `docs/UNBOUNDED_HYBRID_HARDWARE_TESTING.md`
- `quantum_search_api/examples/submit_100k_hybrid_to_ibm.py`

## Verification

- Python compilation passed for the changed backend services and tests.
- All 8 Hybrid circuit tests passed.
- Three focused 33-base tests passed for direct circuit construction,
  resource estimation, and hardware preparation.
- Six estimate/resource tests passed with no production-code reference to the
  removed 32-base guard.
- Thirteen focused frontend action/scaling tests passed.
- Focused ESLint passed.
- Client, SSR, and Nitro production builds passed.
- A wider combined backend run reached 17 passes before an unrelated Grover
  Aer test caused a native Windows access violation; the affected Hybrid tests
  were rerun successfully in isolated processes.
- The standalone direct-IBM script passes Python compilation and CLI-help
  execution, and its non-submitting FASTA validation confirms 100,000 bases in
  each input with exactly 1,000 substitutions.
- The current interpreter does not have `qiskit-ibm-runtime` installed, so no
  IBM submission was attempted. The script reports the exact requirements
  installation command before any circuit construction.

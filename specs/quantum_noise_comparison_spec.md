# Optional Quantum Noise Comparison

## Scope

Implement on-demand ideal/noisy/mitigated comparison for completed local quantum-search jobs.
Only the local frontend under `Rit_Grover_project/quantum-helix-lab` is changed.

## Existing flow

`QuantumSearchResultsPage` -> FastAPI job endpoints -> `InMemoryJobService` ->
`SearchOrchestrator` -> FRQI, Grover/QGSA, or hybrid YLC engine.

## Decisions

- Add `POST /api/quantum-search/jobs/{job_id}/noise`.
- Reconstruct the same logical circuit from the stored job query and its top-ranked processed
  window. The page has no separate selected-hit state.
- Cache the response on the job. Never replace `job.result`.
- Use deterministic seeds and the job's original shot count.
- FRQI: single/two-qubit depolarizing errors on transpiled `u`/`cx`; optimization level 3.
- Grover/QGSA: scaled `u`/`cx` depolarizing noise at 1x, 2x, 3x; linear ZNE on target success.
- Hybrid YLC: readout error on measured position qubits; local assignment-matrix correction.
- Reject unsupported/oversized noise runs with readable API errors.
- Render the comparison after the existing result content and clear it whenever `jobId` changes.

## Files

- Create `quantum_search_api/services/noise/{__init__,noise_models,mitigation,noise_runner}.py`.
- Modify `quantum_search_api/services/search/job_service.py` and `quantum_search_api/app.py`.
- Add backend tests under `quantum_search_api/tests/test_noise_service.py`.
- Modify local `src/components/QuantumSearch.tsx`.
- Create `docs/QUANTUM_NOISE_IMPLEMENTATION.md`.

## Verification

- `python -m pytest quantum_search_api/tests -q --disable-warnings`: 40 passed.
- New noise/API regression selection: 10 passed.
- `bunx eslint src/components/QuantumSearch.tsx`: passed.
- `bun run build`: passed (existing bundle-size and Vite migration warnings only).
- No frontend unit-test framework is configured in this package, so UI behavior is covered by
  type/build validation and the documented manual check.

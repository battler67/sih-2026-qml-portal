# Configurable Noise Parameters

## Goal

Let users configure algorithm-relevant noise rates on the results page before running the
optional Aer comparison.

## Parameters

- FRQI: single-qubit and two-qubit depolarizing error.
- Grover/QGSA: base single-qubit and two-qubit depolarizing error; ZNE remains 1x/2x/3x.
- Hybrid YLC: readout `0 -> 1` and `1 -> 0` probabilities.

All probabilities are validated in `[0, 0.5]`. Existing defaults remain prefilled.

## Backend

- Accept an optional JSON body on `POST /api/quantum-search/jobs/{job_id}/noise`.
- Build noise models from validated request values.
- Cache by job ID plus normalized parameter set.
- Return the actual applied parameters.

## Frontend

- Show only controls relevant to the current result algorithm.
- Clear a displayed comparison when a parameter changes.
- Send parameters with Add Noise.

## Verification

- Custom values reach the noise response: verified.
- Different parameter sets create different cache entries: verified.
- Existing no-body requests continue using defaults: verified.
- Invalid probabilities outside `[0, 0.5]` return HTTP 422: verified.
- Backend suite: `46 passed`.
- Frontend targeted ESLint: passed.
- Frontend production build: passed.

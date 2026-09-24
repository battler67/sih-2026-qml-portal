# Metadata-Only Resource Estimate

## Goal

Make `/api/quantum-search/estimate` a fast, local calculation. NCBI assembly discovery,
genomic FASTA downloads, parsing, and window generation remain exclusively in the background
search job that the results page polls.

## Compatibility

- Preserve the endpoint and existing response fields.
- Treat record, base, window, run, and shot values as configured upper bounds.
- Keep exact local query validation for pasted DNA and uploaded FASTA.
- For an NCBI query accession, use `maxQueryLength` without fetching the accession.
- Preserve current simulator-limit checks.

## New estimate fields

- `estimateMode`
- `estimatedSimulationSecondsMin` / `estimatedSimulationSecondsMax`
- `estimatedEndToEndSecondsMin` / `estimatedEndToEndSecondsMax`
- `runtimeEstimateNote`

Runtime is a planning range, not a benchmark guarantee. End-to-end time includes a broad
allowance for NCBI retrieval; simulation time does not.

## Files

- Modify `quantum_search_api/services/ncbi/models.py`.
- Modify `quantum_search_api/services/search/search_orchestrator.py`.
- Update estimate regression tests.
- Modify local `src/components/QuantumSearch.tsx`.

## Verification

- Estimate-provider isolation test passes; remote estimates do not call NCBI providers.
- Real search progress is emitted at actual orchestration boundaries.
- Exact 12-base FRQI example returned in about 0.017 seconds locally.
- `python -m pytest quantum_search_api/tests -q --disable-warnings`: 41 passed.
- `bunx eslint src/components/QuantumSearch.tsx`: passed.
- `bun run build`: passed with existing bundle-size/Vite migration warnings only.

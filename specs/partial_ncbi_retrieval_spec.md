# Partial NCBI Retrieval

## Goal

Do not discard successful NCBI records when later record downloads time out or fail. Continue
window generation and quantum processing with usable records already retrieved.

## Design

- Keep metadata discovery unchanged.
- Download target assemblies/accessions incrementally during the background job.
- Preserve each successfully parsed record immediately.
- Skip failed accessions and add readable result warnings.
- Stop after three consecutive NCBI failures to avoid multiplying timeout delays.
- Stop once the configured total-base processing cap is satisfied.
- Fail the job only when zero usable records are available.
- Report incremental retrieval progress on the results page.

## Files

- Modify `quantum_search_api/services/search/search_orchestrator.py`.
- Add partial-timeout regression coverage in `test_search_orchestrator.py`.

## Verification

- Simulated record-2 timeout preserved records 1 and 3 and returned two quantum hits.
- Zero successful records returns attempted/failed accession details.
- `python -m pytest quantum_search_api/tests -q --disable-warnings`: 43 passed.
- `bunx eslint src/components/QuantumSearch.tsx`: passed.
- `bun run build`: passed with existing bundle-size/Vite migration warnings only.

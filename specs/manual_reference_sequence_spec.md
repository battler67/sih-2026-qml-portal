# Manual Reference Sequence

## Goal

Allow the user to enter a target/reference DNA sequence independently from the query when
`Reference Set` is `Pasted genomic DNA`.

## Request contract

- Keep `querySequence` as the pattern being searched.
- Add optional `referenceSequence`.
- Require `referenceSequence` only for `databaseScope="pasted_sequence"`.
- Normalize and validate the reference independently as A/C/G/T DNA.

## UI

- Show a `Reference DNA Sequence` textarea only for the pasted-reference scope.
- Display reference length and A/C/G/T validity.
- Clear the previous estimate when the reference changes.
- Block Estimate and Run until both query and manual reference are valid.

## Files

- Modify `quantum_search_api/services/ncbi/models.py`.
- Modify `quantum_search_api/services/search/local_providers.py`.
- Modify local `src/components/QuantumSearch.tsx`.
- Add request/provider/orchestrator regression tests.

## Verification

- Manual `ACGT` query against `TTACGTGG` reference preserved both independently and found the
  `ACGT` reference window.
- Result metadata includes reference source, first 10 bases, accession, coordinates, and selection
  explanation.
- `python -m pytest quantum_search_api/tests -q --disable-warnings`: 45 passed.
- `bunx eslint src/components/QuantumSearch.tsx`: passed.
- `bun run build`: passed with existing bundle-size/Vite migration warnings only.

# Remove reference-selection message

Date: 2026-07-30

## Goal

Remove long backend reference/window-selection explanations from the
`/quantum-search-results` page.

## Decision

- Remove only the rendered sentence.
- Preserve `selectionMethod` in the API result and downloadable JSON.
- Keep the compact reference source, accession, and coordinate information.
- Preserve the compact processed/accepted window counts, stride, strand, and
  ranking summary while removing the verbose window-selection description.

## Verification

- Run targeted ESLint for `QuantumSearch.tsx`.
- Run `git diff --check`.

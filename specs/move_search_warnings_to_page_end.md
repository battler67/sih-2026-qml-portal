# Move search warnings to page end

Date: 2026-07-30

## Goal

Move the completed-search warning list to the end of
`/quantum-search-results`.

## Decision

- Keep the job controls in their current location.
- Preserve every backend warning and its existing styling.
- Render the warning block after the methodology and optional noise-results
  sections so it is the final page section.

## Verification

- Run targeted ESLint for `QuantumSearch.tsx`.
- Run `git diff --check`.

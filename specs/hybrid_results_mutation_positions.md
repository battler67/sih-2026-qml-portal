# Hybrid mutation-position results

## Scope

Port the Hybrid Fixed-Point input and results changes into
`quantum-helix-lab-full` only. Preserve all existing hardware-routing and other
unrelated working-tree changes.

## Branch

- `feature/hybrid-mutation-position-results`
- Created from the existing `feature/real-hardware-routing` working state so
  that its uncommitted work remains intact.

## Plan

1. Require Hybrid query/reference inputs to be non-empty A/C/G/T strings of the
   same length, warn when lengths differ, and disable Estimate/Run while invalid.
2. Execute pasted Hybrid inputs as one direct equal-length comparison without
   generating sliding windows.
3. Render only circuit-derived mutation coordinates from
   `measuredCandidateIndices`, paired with measured probabilities and counts.
4. Remove candidate-validation and window-specific UI for Hybrid results.
5. Align the Hybrid hit chart and CSV with the mutation-position distribution.
6. Add focused tests and run backend/frontend verification.

## Change log

- Created the task branch and this plan before implementation edits.
- Updated Hybrid request validation to require pasted, equal-length inputs.
- Updated orchestration to run one direct comparison without sliding windows.
- Updated the Hybrid results table, hit graph, metrics, CSV, warnings, controls,
  and scientific-boundary text.
- Preserved the existing real-hardware routing and long-sequence work; bounded
  window behavior remains available to FRQI and Grover.
- Updated focused Hybrid/orchestrator tests.

## Verification

- Python compile: passed.
- Focused Hybrid/orchestrator tests: `22 passed`.
- Full `quantum_search_api/tests` suite: `65 passed`.
- Targeted frontend ESLint: passed.
- Frontend production build: passed.
- Direct `ACGTACGT` / `ATGTACAT` check: mutation candidates `[1, 6]`, no
  `windowSelection`, `windowsProcessed=0`, and `sequenceComparisons=1`.

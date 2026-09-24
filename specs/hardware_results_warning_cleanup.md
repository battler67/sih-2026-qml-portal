# Hardware results warning cleanup

Date: 2026-07-30

## Goal

Reduce warning noise on `/quantum-hardware-results` after a successful IBM
fallback.

## Branch

- `feature/real-hardware-routing`

## Decisions

- Do not show the qBraid failure panel after IBM has completed the hardware
  run successfully.
- Keep provider fallback details in the backend result for diagnostics; this
  task changes successful-result presentation only.
- Show only two scientifically relevant boundaries on the completed-results
  page:
  1. The run is not an entire-genome coherent search or evidence of quantum
     advantage.
  2. Counts are raw physical-device measurements without mitigation.
- Preserve provider errors on the failed-job view, where they are actionable.

## Verification

- Format and lint `QuantumHardwareResults.tsx`.
- Run the production frontend build.

## Implementation log

- Removed the completed-result qBraid/IBM fallback warning panel.
- Limited the completed scientific-boundary panel to the two selected
  messages.
- Kept detailed provider errors visible when the complete hardware job fails.
- Targeted ESLint passed.
- Production frontend build passed.
- `git diff --check` passed.

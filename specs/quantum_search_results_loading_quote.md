# Quantum search results loading quote

## Plan

- Reuse the existing `LoadingInsight` component on the quantum-search results page.
- Show it only while a valid job is pending and no result or error is present.
- Keep polling unchanged and remove the quote immediately when results arrive.
- Verify both frontend copies with their production builds.

## Implementation log

- Updated both `QuantumSearch.tsx` frontend copies so either local launch path displays the existing random science quote while a quantum-search job is pending.
- The loading insight is hidden for missing job IDs, completed results, and failed requests.
- Production builds passed for both frontend copies on 2026-07-29.

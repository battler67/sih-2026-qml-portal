# Move Hybrid Notice to Page Bottom

## Scope

- Repository: `quantum-helix-lab-full`
- Branch: `feature/move-hybrid-notice-to-page-bottom`
- Move the existing Quantum Search guidance notice from below the action buttons to the bottom of the page.
- Preserve Hybrid equal-length validation, disabled action buttons, and all notice text.

## Plan

1. Relocate the existing conditional notice without changing its logic.
2. Format the edited component.
3. Run targeted lint and a production build.

## Change Log

- Created the task branch from the current `main`.
- Moved the existing conditional guidance notice beneath the page's visible search content.
- Kept the Hybrid equal-length warning text and input/button validation unchanged.

## Verification

- `bunx prettier --write src/components/QuantumSearch.tsx` — passed.
- `bunx eslint src/components/QuantumSearch.tsx` — passed.
- `npm run build` — passed.

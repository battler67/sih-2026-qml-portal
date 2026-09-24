# Loading quote placement

## Goal

Keep the loading quote dialog below the global navbar instead of covering it.

## Change

- Updated `github_push_quantum_helix_lab/src/components/LoadingInsight.tsx`.
- The fixed loading layer now starts at `6.5rem`, matching the navbar's
  4rem primary row plus 2.5rem breadcrumb row.
- The loading layer uses `z-40`, below the navbar's `z-50`.

## Verification

- `npm run build` passed for `github_push_quantum_helix_lab`.
- Vite completed the client, SSR, and Nitro production builds successfully.

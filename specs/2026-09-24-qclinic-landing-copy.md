# QClinic landing-page copy refresh

## Goal

Refresh the existing landing-page text around QClinic's early-risk research workflows while preserving the page structure, styling, routes, and DNA animation.

## Scope

- Rewrite the hero and navigation labels.
- Replace legacy DNA-alignment feature copy with current EHR, genomics, imaging, explainability, and evidence language.
- Refresh the workflow and research callout.
- Keep claims appropriate for a research-use prototype and avoid diagnostic language.

## Verification

- Confirmed `DNAHelix`, motion configuration, layout classes, routes, and component structure are unchanged.
- `bun run lint` completed without reporting an ESLint error.
- Prettier check reports that `Landing.tsx` has existing formatting differences; formatting was not applied because this task is intentionally limited to copy changes.
- Reproduced the development SSR failure on an isolated Vite server: `/` timed out after 90 seconds with no response.
- Kept the `DNAHelix` implementation unchanged and deferred its WebGL canvas until browser mount so it cannot block SSR.
- Tested explicit prebundling for the animation libraries, then removed it because it made Vite dependency optimization stall for more than two minutes. The client-only boundary is the effective fix.
- Verified the isolated development server now returns HTTP 200 for `/` in about one second.
- Verified the full client, SSR, and Nitro production build completes successfully.
- Found and stopped a stale pre-fix Vite process on port 8081.
- Found two QML inference processes sharing port 8010; replaced them with one repository-managed instance.
- Confirmed the genomics backend returned HTTP 200 in 0.024 seconds.
- Confirmed a clean cold landing render returned HTTP 200, followed by warm route responses between 0.07 and 0.17 seconds.

## Files changed

- `src/components/Landing.tsx`
- `vite.config.ts`
- `specs/2026-09-24-qclinic-landing-copy.md`

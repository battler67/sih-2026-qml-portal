# Demo Genome Viewer Images

## Branch

`feature/demo-genome-viewer-images`

## Scope

- Use the images supplied in `cacheResults/Images` as local demo assets.
- On `/ncbi/search`, check the current search and selected NCBI record against a
  deterministic local image manifest.
- Prefer a matching local demo image in the Genome Data Viewer panel.
- Preserve the existing backend/Wikimedia image when no local image matches.
- Keep the existing layout, taxonomy tree, links, and NCBI search behavior.

## Implementation plan

1. Publish the supplied images from the frontend `public` directory.
2. Add a typed matcher for gene, organism, taxonomy ID, and accession metadata.
3. Pass the current search/selected-record metadata into the viewer image
   selection without changing the backend API.
4. Add focused matcher tests and run targeted formatting, lint, tests, and build.

## Task log

- Created branch `feature/demo-genome-viewer-images`.
- Confirmed the active demo page at `http://127.0.0.1:8080/ncbi/search`.
- Located six supplied images under `cacheResults/Images`.
- Copied the supplied assets to `public/demo/genome-viewer` with URL-safe names.
- Added local-first matching by gene, organism, taxonomy ID, and accession.
- Preserved the API/Wikimedia image as the fallback for unmatched searches.
- Verified the live `BRCA1` + `Homo sapiens` demo query returns nine records; its
  first `NBR1` record maps to the supplied NBR1 image.
- Extended the same local-first lookup to `/ncbi/record/$accession`.
- Verified live metadata for `L78833.1` identifies BRCA1, Homo sapiens, taxon
  9606, which maps to the supplied human BRCA images.

## Verification

- `bun test src/lib/demo-genome-images.test.ts` — 6 passed.
- Focused ESLint on the matcher/test, plus the component with the repository's
  existing whole-file Prettier rule disabled to avoid unrelated formatting
  churn.
- `bun run build`
- HTTP 200 from the live port 8080 for the demo asset and matcher module.

# Vercel full-stack deployment

## Goal

Deploy the current QClinic portal, genomics API, and QML inference API from this worktree to one Vercel project and verify the main user-facing routes.

## Plan

1. Package the portal and both Python APIs as Vercel Services with same-origin route prefixes.
2. Preserve the existing API contracts and model artifacts; add only the minimum ASGI adapter needed by the QML service.
3. Configure browser API bases for the deployed same-origin paths without changing local defaults.
4. Run lint, production build, Python tests, and local endpoint checks.
5. Deploy a preview, verify portal/API/model routes, then promote the verified artifact to production.

## Known deployment boundary

The current genomics and hardware job managers store job state in process memory. Core synchronous APIs can run on Vercel, but multi-request job polling is not guaranteed until job state is moved to durable storage.

## Change log

- Branch/worktree: `qml-portal-consolidation`
- Deployment target: Vercel Services
- The first Python Functions packaging attempt failed after a successful build. Vercel's injected `vercel-runtime` wheel contains Python source under its `.dist-info/licenses/src` tree, and bytecode packaging tried to move a cache file that did not exist, producing the repeatable `ENOENT` failure.
- The proposed Python exclusions were moved under each service's `functions` configuration, which is the valid location when `services` is present. They correctly excluded repository files, but could not affect Vercel's injected runtime layer, so they did not solve the failure and were removed.
- Both Python APIs now run in one repository-root container built by `Dockerfile`. `vercel_backend.py` mounts the existing genomics API under `/api/genomics` and the Vercel-safe QML API under its existing `/api/qml/v1` routes. The deployed image is 222.23 MB.
- The browser uses same-origin service rewrites. The QML client recognizes `/api/qml` as an already-prefixed deployment base, avoiding a duplicated `/api/qml/api/qml/v1` request path.
- Local QML service and real-hardware code paths remain available. The deployed adapter intentionally exposes analytic inference only; it does not submit paid or provider-backed hardware jobs.

## Verification

- Production: <https://qml-portal-consolidation.vercel.app>
- Vercel deployment: `dpl_e8snj4HuF4mF39v3TKkoqWP6i2sA`, status `READY`
- Portal: landing page and `/qml` rendered in a browser without page errors. The QML page loaded all 38 model records from the live API.
- Genomics API: `GET /api/genomics/api/health` returned `{"status":"ok","service":"quantum-search-api"}`. A synthetic pasted-sequence request to `/api/genomics/api/quantum-search/estimate` returned a Grover resource estimate.
- QML API: `GET /api/qml/v1/health` returned `ready` for bundle `2026-09-22-qcnn-1`. A synthetic Framingham request to `/api/qml/v1/predict` returned the saved Angle-QKSVM prediction and explanation.
- Local verification: `bun run build` passed; `bun test src/lib/qml-api.test.ts` passed 4 tests. The QML serving and hardware suites previously passed 20 tests after the deployment slimming changes.
- Non-blocking browser output is limited to Three.js deprecation/precision warnings from the existing DNA animation, which was not changed.

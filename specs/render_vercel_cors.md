# Render and Vercel CORS

## Scope

Allow the Render-hosted FastAPI service to accept browser requests from an
explicitly configured Vercel frontend origin without weakening the existing
localhost development policy.

## Plan

1. Add a backend-only, comma-separated `QDNA_CORS_ORIGINS` setting.
2. Preserve the current localhost origins and normalize configured origins.
3. Document the Render environment-variable value and add focused tests.
4. Run the API tests, commit only the scoped files, and push the authorized
   `main` branch so Render can redeploy.

## Change log

- Branch: `main` (minor deployment fix; direct push explicitly requested).
- Files created: this specification.
- Major edits: added exact environment-driven production origins while retaining
  the localhost defaults; documented the Render/Vercel variables and added parser
  coverage.
- Verification:
  - `python -m py_compile quantum_search_api/app.py`
  - focused API file: 8 passed
  - production-origin CORS preflight: 200 with the requested
    `Access-Control-Allow-Origin`
  - complete backend API suite: 73 passed

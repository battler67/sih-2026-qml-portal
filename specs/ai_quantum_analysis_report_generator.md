# AI Quantum Analysis Report Generator

## Branch

`feature/ai-quantum-analysis-reports`

## Scope

- Add a backend-only OpenAI Responses API integration for completed quantum DNA
  search jobs.
- Send only an allowlisted, mode-aware set of computed result facts to OpenAI.
- Keep measured facts separate from AI-written interpretations.
- Never send raw DNA sequences, NCBI record content, user credentials, or
  unrelated job data to OpenAI.
- Add `Generate Report` and `Download PDF` actions to the existing results page
  without changing its visual system.
- Include mutation/mismatch and YLC fields only for Hybrid Fixed-Point results.
- Include ideal/noisy/mitigated analysis only when a noise comparison has
  actually been run.
- Do not make medical, clinical, pathogenicity, or quantum-advantage claims.

## API endpoint

### `POST /api/quantum-search/jobs/{job_id}/report`

Generates or returns a cached report for the current completed result and latest
noise comparison. The response contains:

- algorithm and model metadata;
- server-extracted measured facts;
- five AI interpretation sections;
- a scientific-use disclaimer.

Errors:

- `404` when the job does not exist;
- `409` when the job has no completed result;
- `503` when OpenAI is not configured or report generation is unavailable.

## Environment

Place the key only in `quantum_search_api/.env`:

```dotenv
OPENAI_API_KEY=your_openai_api_key
OPENAI_REPORT_MODEL=gpt-5.6-sol
OPENAI_REPORT_TIMEOUT_SECONDS=60
```

Never expose the key through a `VITE_*` variable or frontend source.

## Implementation plan

1. Build and test strict per-algorithm fact extraction.
2. Add a strong system prompt and structured Responses API output.
3. Cache reports by the exact measured-fact payload.
4. Add the FastAPI report endpoint and error mapping.
5. Add the results-page report state, mode-aware fact display, and actions.
6. Generate a browser-side PDF without sending another API request.
7. Run focused backend tests, frontend tests/lint, and a production build.

## Task log

- Created branch `feature/ai-quantum-analysis-reports`.
- Confirmed the active results component is
  `src/components/QuantumSearch.tsx`.
- Confirmed completed results and latest noise comparisons are retained by
  `InMemoryJobService`.
- Resolved the current OpenAI model guidance to `gpt-5.6-sol` and selected the
  Responses API with structured output.
- Added strict mode-aware fact extraction that excludes raw sequences and record
  metadata.
- Added the structured OpenAI report client, fact-keyed cache, and report API.
- Added frontend report types, a dependency-free PDF builder, and results-page
  report actions/presentation.
- Added `docs/AI_REPORT_GENERATOR.md` with the endpoint, environment,
  mode-field matrix, and changed-file inventory.
- Extended the existing asynchronous Grover API test poll window because its
  2.5-second Windows cold-start limit repeatedly expired while the job was still
  running; the assertion and production timeout behavior are unchanged.
- Tracked the most recently selected noise cache key so a report uses the same
  cached comparison currently displayed by the frontend.

## Verification

- Python compilation passed for the report service, app, job service, and tests.
- `test_ai_report_service.py` plus `test_api.py`: 11 passed.
- Report/noise/search-orchestrator regression set: 27 passed.
- Frontend report PDF test: 1 passed; broader touched utility set: 11 passed.
- Focused ESLint passed for the report utilities and `QuantumSearch.tsx`
  (whole-file Prettier rule disabled for the already modified component to avoid
  unrelated formatting churn).
- Full Vite client, SSR, and Nitro production build passed.
- The live port-8080 module exposes both requested buttons and the measured-fact
  label; the live backend recognizes the report endpoint.
- A live OpenAI call was not run because `OPENAI_API_KEY` is intentionally absent
  from `quantum_search_api/.env`.

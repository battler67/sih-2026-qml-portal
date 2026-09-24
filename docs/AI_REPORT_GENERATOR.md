# AI Quantum DNA Analysis Reports

## Purpose

The results page can generate a concise research report from a completed QDNA
job. The model does not receive raw DNA sequences, NCBI record text, complete job
objects, API keys, or user-entered metadata. The backend sends only an allowlisted
set of computed facts:

- measured mismatch-candidate positions for Hybrid Fixed-Point only;
- measured counts or index-probability distributions;
- logical and transpiled circuit depth, qubit count, and gate counts;
- measured execution times;
- YLC iterations for Hybrid Fixed-Point only;
- the latest ideal/noisy/mitigated comparison, if one exists;
- noise configuration and mitigation results, if one exists.

The response deliberately separates `measuredFacts`, produced by QDNA, from
`aiInterpretations`, produced by OpenAI.

## Environment configuration

Copy `quantum_search_api/.env.example` to `quantum_search_api/.env`, then set:

```dotenv
OPENAI_API_KEY=your_openai_api_key
OPENAI_REPORT_MODEL=gpt-5.6-sol
OPENAI_REPORT_TIMEOUT_SECONDS=60
```

The API key is backend-only. Do not put it in `.env.local`, browser storage,
frontend source, or any `VITE_*` variable.

`OPENAI_REPORT_MODEL` is configurable. The default follows the current OpenAI
model guidance and uses `gpt-5.6-sol`.

## API

### Generate a report

```http
POST /api/quantum-search/jobs/{job_id}/report
```

No request body is accepted. The backend resolves the completed result and the
latest cached noise comparison for that job.

Successful response:

```json
{
  "reportId": "fact-fingerprint",
  "jobId": "job-id",
  "algorithm": "hybrid",
  "model": "gpt-5.6-sol",
  "generatedAt": "ISO-8601 timestamp",
  "measuredFacts": {},
  "aiInterpretations": {
    "executive_summary": "...",
    "dna_interpretation": "...",
    "circuit_resource_analysis": "...",
    "noise_mitigation_comparison": "...",
    "reliability_limitations_conclusion": "..."
  },
  "disclaimer": "..."
}
```

Status codes:

- `200`: generated or cached report;
- `400`: unsupported/malformed stored algorithm result;
- `404`: job not found;
- `409`: job has not completed;
- `503`: OpenAI is unconfigured, unreachable, or returned an invalid report.

Reports are cached by a SHA-256 fingerprint of the measured-fact payload. Adding
noise or changing a stored computed result produces a different fingerprint and
therefore a new report.

## Mode-aware fields

| Field                          | Grover               | FRQI                 | Hybrid Fixed-Point   |
| ------------------------------ | -------------------- | -------------------- | -------------------- |
| Probability/count distribution | Yes, when returned   | Yes, when returned   | Yes, when returned   |
| Circuit depth/qubits/gates     | Yes, when returned   | Yes, when returned   | Yes, when returned   |
| Execution time                 | Yes, when returned   | Yes, when returned   | Yes, when returned   |
| Mismatch candidates            | No                   | No                   | Yes                  |
| YLC iterations                 | No                   | No                   | Yes                  |
| Ideal/noisy/mitigated          | Only after Add Noise | Only after Add Noise | Only after Add Noise |

The system prompt prohibits medical conclusions, pathogenicity claims, invented
statistics, hardware claims, and quantum-advantage claims. It also prevents
Grover/FRQI reports from using mutation or YLC terminology.

## PDF download

`Download PDF` uses the already generated report in the browser. It does not send
another OpenAI request. The dependency-free PDF builder includes both the
application-computed facts and the separately labeled AI interpretations.

## Changed files

- `quantum_search_api/app.py` — report endpoint and error mapping.
- `quantum_search_api/.env.example` — backend OpenAI configuration.
- `quantum_search_api/services/reports/__init__.py` — report service exports.
- `quantum_search_api/services/reports/ai_report.py` — fact allowlist, system
  prompt, structured Responses API call, and validation.
- `quantum_search_api/services/search/job_service.py` — fact-keyed report cache.
- `quantum_search_api/tests/test_ai_report_service.py` — extraction, privacy,
  prompt, schema, and OpenAI transport tests.
- `quantum_search_api/tests/test_api.py` — endpoint and cache test.
- `src/components/QuantumSearch.tsx` — buttons, request state, fact display, and
  interpretation panel.
- `src/lib/ai-report.ts` — frontend report types and fact formatting.
- `src/lib/ai-report-pdf.ts` — dependency-free PDF generation/download.
- `src/lib/ai-report-pdf.test.ts` — PDF artifact test.
- `docs/AI_REPORT_GENERATOR.md` — this implementation and API reference.
- `docs/QUANTUM_SEARCH.md` — report documentation link.
- `README.md` — feature documentation link.
- `specs/ai_quantum_analysis_report_generator.md` — plan and verification log.

## OpenAI references

- [Model guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [GPT-5.6 Sol model](https://developers.openai.com/api/docs/models/gpt-5.6-sol)

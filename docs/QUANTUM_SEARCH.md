# Genomic Quantum Search

AI-generated, mode-aware result reports are documented in
[AI_REPORT_GENERATOR.md](AI_REPORT_GENERATOR.md).

The Hybrid/Grover theoretical query and timing projections are documented in
[CLASSICAL_QUANTUM_SCALING.md](CLASSICAL_QUANTUM_SCALING.md).

The branch-only removal of the fixed Hybrid length guard is documented in
[UNBOUNDED_HYBRID_HARDWARE_TESTING.md](UNBOUNDED_HYBRID_HARDWARE_TESTING.md).

## Overview

The new genomic quantum search workflow is a BLAST-like nucleotide search experience, not an implementation of the BLAST algorithm. NCBI performs genomic sequence discovery and retrieval. The project then normalizes and windows retrieved genomic DNA before calling the existing FRQI or Grover/QGSA quantum simulator code.

Hybrid mode executes a coherent per-position mismatch predicate followed by
Yoder-Low-Chuang fixed-point amplitude amplification. Its schedule uses the
lower bound `lambda_min = 1/N`, so it does not need the actual mismatch count
`M`.

## Startup

Backend:

```powershell
python -m uvicorn quantum_search_api.app:app --reload --port 8000
```

Frontend:

```powershell
cd Rit_Grover_project\quantum-helix-lab
npm run dev
```

Open:

```text
http://localhost:5173/quantum-search
```

## Environment

Use `.env.example` as the variable list. Do not put `NCBI_API_KEY` in frontend code.

```env
NCBI_API_KEY=
NCBI_TOOL_NAME=quantum_dna_search
NCBI_DEVELOPER_EMAIL=
NCBI_REQUEST_TIMEOUT_SECONDS=30
NCBI_MAX_RETRIES=3
NCBI_CACHE_TTL_SECONDS=86400
NCBI_MAX_RECORDS_PER_SEARCH=20
NCBI_MAX_TOTAL_BASES=1000000
VITE_QUANTUM_API_BASE_URL=http://localhost:8000
```

## Supported Genomic Scopes

- RefSeq reference genome assemblies.
- RefSeq representative genome assemblies.
- GenBank GCA genome assemblies.
- RefSeq GCF genome assemblies.
- Genome assemblies selected by organism.
- Genome assemblies selected by NCBI Taxonomy ID.
- Exact GCA or GCF assembly accessions.
- Exact nucleotide accessions only when NCBI metadata identifies genomic DNA.
- Gene searches only as a modeled field; genomic region retrieval is disabled in this pass.
- User-uploaded genomic nucleotide FASTA.
- User-pasted DNA sequences.

Generic BioProject search and virus searches are disabled initially. RNA, transcript, protein, SRA, GEO, FASTQ, mRNA, ncRNA, CDS, and protein records are rejected.

## Search Modes

FRQI Similarity:

- Uses `frqi_dna.src.analysis.compare_dna_frqi`.
- Processes equal-length query/window pairs.
- Returns strip-qubit probability, FRQI similarity, shot counts, angle mapping, logical metrics, and transpiled metrics.
- Ranks windows by quantum similarity.

Grover Search:

- Uses `qgsa_grover.qgsa.search_dna_qgsa`.
- Uses exact ACGT pattern matching in bounded windows.
- Returns measured candidate indices, index probabilities, success probability, false-positive probability, iteration details, counts, and circuit metrics.
- Classical exact validation is reported separately and does not replace quantum results.

Hybrid Search:

- Independently compiles the query and target window into reversible two-bit
  A/C/G/T lookup gates.
- Computes `reference != query` inside the circuit with reversible XOR/OR
  logic; Python does not supply mismatch positions.
- Uses an analytic fixed-point phase schedule selected from `N` and
  `delta=0.2`, not from the actual `M`.
- Reports shot-inferred candidate indices, exact simulator probabilities,
  phase schedule, query count, and logical/transpiled circuit metrics.
- Ranks by amplified mismatch evidence. It is an experimental mismatch
  localization mode, not an edit-distance or BLAST score.

The fixed-point phase construction follows Yoder, Low, and Chuang,
[“Fixed-point quantum search with an optimal number of queries”](https://arxiv.org/abs/1409.3305).
The complete register derivation, phase equations, numerical experiment, and
complexity discussion are in
[`HYBRID_FIXED_POINT_MATHEMATICS.md`](HYBRID_FIXED_POINT_MATHEMATICS.md).

## Limits

- User query alphabet: A, C, G, T only.
- Target genomic sequences may contain IUPAC ambiguity, but windows containing non-ACGT symbols are skipped.
- Ambiguous characters are not deleted because that would change genomic coordinates.
- Coordinates are zero-based half-open internally and displayed as one-based inclusive coordinates.
- Complete downloaded records are never sent directly into a quantum circuit.
- Results include `quantumAlphabet: "ACGT"`.

## API

Main endpoints:

```http
POST /api/quantum-search/estimate
POST /api/quantum-search/jobs
GET  /api/quantum-search/jobs/{job_id}
GET  /api/quantum-search/jobs/{job_id}/results
DELETE /api/quantum-search/jobs/{job_id}
```

NCBI helper endpoints:

```http
GET  /api/ncbi/search
GET  /api/ncbi/records/{accession}
POST /api/ncbi/records/batch
GET  /api/ncbi/taxa/search
GET  /api/ncbi/assemblies/search
```

Example local FRQI request:

```json
{
  "querySource": "pasted",
  "querySequence": "ACGT",
  "algorithm": "frqi",
  "databaseScope": "uploaded_fasta",
  "uploadedFasta": ">demo\nACGTNNACGT\n",
  "maxWindows": 4,
  "shots": 1024
}
```

Example local Grover request:

```json
{
  "querySource": "pasted",
  "querySequence": "ACGT",
  "algorithm": "grover",
  "databaseScope": "uploaded_fasta",
  "uploadedFasta": ">demo\nACGTNNACGT\n",
  "maxWindows": 4,
  "shots": 1024
}
```

## User Navigation

1. Start the backend and frontend.
2. Open `/quantum-search`.
3. Choose query source: pasted sequence, uploaded FASTA text, or NCBI accession.
4. Select one genomic DNA scope.
5. Choose FRQI Similarity, Grover Search, or Hybrid Fixed-Point.
6. Configure shots, maximum records, maximum windows, stride, and strand mode.
7. Click `Estimate`.
8. Review record/window/qubit/shot warnings.
9. Click `Run Search`.
10. Watch progress through retrieval, preprocessing, circuit construction, simulation, validation, and results.
11. Inspect ranked hits, one-based coordinates, quantum metrics, validation status, and actual probability/count charts.
12. Download JSON, CSV, or FASTA for returned windows.

## Action availability

- `Estimate` remains clickable whenever another estimate/search operation is
  not running. Missing or invalid inputs are explained by a dialog instead of
  leaving the button silently disabled.
- `Run Search` is resource-driven. It requires a fresh successful estimate and
  remains disabled when that estimate reports that the bounded circuit exceeds
  local simulator limits.
- `Run on Real Hardware` is not blocked by the frontend estimate or its
  planning-capacity flag. The confirmation remains explicit, and backend
  circuit construction, live provider discovery, topology, transpilation,
  account access, and provider limits remain authoritative.
- Changing any search configuration clears the previous estimate, so simulator
  execution cannot use stale resource information.

## Testing

```powershell
python -m pytest quantum_search_api\tests -q
python -m pytest frqi_dna\tests -q
$env:PYTHONPATH='qgsa_grover\src'; python -m pytest qgsa_grover\tests -q
npm run build
npm run lint
```

External NCBI calls are mocked in automated tests.

## Scientific Limitations

- The portal accepts up to 100,000 A/C/G/T bases for pasted or FASTA-formatted
  query and reference inputs. `maxQueryLength` remains the bounded quantum
  window length and is limited to 128 bases.
- When a query is longer than the configured quantum window, only its leading
  bounded window is compiled into each circuit. The reference is scanned using
  the existing `maxWindows`, stride, strand, and base caps.
- Estimate reports the full input length, bounded quantum window length,
  truncation status, and separate Aer and 156-qubit hardware eligibility.
  Live device discovery and transpilation remain authoritative.
- Long-input support does not coherently encode or compare both complete
  100,000-base strings in one circuit. Grover/QGSA can remain ineligible
  because its bounded circuit is qubit-heavy.
- This is nucleotide sequence search and similarity analysis, not DNA sequencing.
- It is not a complete BLAST clone and does not compute BLAST E-values or gapped local alignments.
- FRQI scores are angle-overlap similarity scores, not percent identity.
- Grover mode supports exact matching only with the current oracle.
- On the experimental `feature/unbounded-hybrid-hardware-testing` branch,
  Hybrid mode has no fixed 32-base algorithm guard. Equal-length A/C/G/T input,
  general portal input bounds, circuit construction, transpilation, live
  provider capacity, and provider quotas still apply. Its fixed-point guarantee
  assumes at least one but not every position is marked; the all-match and
  all-mismatch extremes both remain uniform over positions and cannot be
  localized from the position histogram alone.
- Hybrid inputs are still classical strings compiled into QROM-style gates.
  This avoids classical mismatch discovery but does not assume free QRAM or
  establish end-to-end quantum advantage.
- Simulator execution is not equivalent to fault-tolerant quantum hardware execution.
- Large database searches are staged and bounded; the entire GenBank database is never loaded into a quantum circuit.

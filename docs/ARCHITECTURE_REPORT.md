# Existing Project Architecture Report

## Repository Shape

- `Rit_Grover_project/quantum-helix-lab`: React web application.
- `frqi_dna`: standalone Python/Qiskit FRQI DNA comparison package.
- `qgsa_grover`: standalone Python/Qiskit Grover/QGSA exact-pattern search package.
- `Images`, `pdf_pages`, `qgsa_grover_paper_pages`, `outputs`: research and generated artifacts.

## Frontend Architecture

- Framework: TanStack Start with React 19 and Vite.
- Routing: file-based TanStack Router routes under `src/routes`; generated tree in `src/routeTree.gen.ts`.
- Existing routes: `/` renders `Landing`, `/dashboard` renders `Dashboard`.
- CSS system: Tailwind CSS v4 from `src/styles.css`; no separate Tailwind config.
- UI primitives: local shadcn/Radix-style components under `src/components/ui`.
- Visual design: dark emerald/cyan quantum DNA theme using `glass`, `glass-strong`, `glow-emerald`, `text-gradient-emerald`, rounded panels, mono sequence text, and framer-motion entrance animations.
- Charts: Recharts is already installed and used by the dashboard.

## Backend / Quantum Architecture

- No existing web API routes were found in the TanStack app.
- FRQI package exposes `frqi_dna.src.analysis.compare_dna_frqi`, which returns strip probability, FRQI similarity, shot counts, angle mapping, logical metrics, transpiled metrics, and timing.
- Grover package exposes `qgsa_grover.qgsa.search_dna_qgsa`, which builds the QGSA circuit, runs AerSimulator, measures candidate-index probabilities, reports valid positions, success probability, false-positive probability, iterations, circuit metrics, warnings, and separate classical validation metadata.

## Baseline Verification

- `python -m pytest frqi_dna\tests -q`: 19 passed.
- `PYTHONPATH=qgsa_grover/src python -m pytest qgsa_grover\tests -q`: 19 passed.
- `npm run build`: passed after allowing dependency execution outside the sandbox.
- `npm run lint`: pre-existing failure due to repository CRLF/prettier formatting, before implementation changes.

## Planned Integration

Create a Python backend package under `quantum_search_api` because the current web app has no API layer and the existing quantum algorithms are Python/Qiskit modules.

Planned backend files:

- `quantum_search_api/app.py`
- `quantum_search_api/services/ncbi/*`
- `quantum_search_api/services/sequence/*`
- `quantum_search_api/services/quantum/*`
- `quantum_search_api/services/search/*`
- `quantum_search_api/tests/*`
- `quantum_search_api/fixtures/demo_genomic.fna`
- `quantum_search_api/requirements.txt`

Planned frontend files:

- `Rit_Grover_project/quantum-helix-lab/src/components/QuantumSearch.tsx`
- `Rit_Grover_project/quantum-helix-lab/src/routes/quantum-search.tsx`
- update `Rit_Grover_project/quantum-helix-lab/src/routeTree.gen.ts` only to register the new route if route generation is not available.
- optionally add a navigation link from existing pages only if it preserves the current visual hierarchy.

Planned docs/env files:

- `.env.example`
- `docs/QUANTUM_SEARCH.md`

## Genomic-Only Scope

The integration will restrict NCBI-backed retrieval to genomic DNA:

- NCBI Datasets Genome API for organism, taxonomy, and assembly discovery.
- Assembly scopes limited to RefSeq reference, RefSeq representative, GenBank GCA, RefSeq GCF, organism-selected assemblies, taxonomy-selected assemblies, and exact GCA/GCF accessions.
- Entrez Nucleotide retrieval only for exact nucleotide accessions that satisfy `biomol_genomic[PROP]`; RefSeq-only retrieval also adds `srcdb_refseq[PROP]`.
- Generic BioProject search and virus search are disabled initially.
- Download handling accepts genomic FASTA records only, normally `*_genomic.fna`, and rejects RNA, transcript, protein, SRA, GEO, FASTQ, mRNA, ncRNA, CDS, and protein records after metadata validation.

## Implementation Notes

- Hybrid mode was subsequently enabled with a bounded coherent mismatch
  predicate and Yoder-Low-Chuang fixed-point amplification. It uses a
  `lambda_min=1/N` schedule rather than the actual mismatch count and keeps
  optional classical validation outside the quantum engine.
- Complete downloaded records will never be sent directly into a quantum circuit; sequences are normalized, bounded, windowed, and filtered to A/C/G/T windows first.
- User queries are restricted to A/C/G/T for compatibility with the existing circuits.
- Target windows containing ambiguous or unsupported IUPAC symbols are skipped without deleting characters, preserving genomic coordinates.
- Every result will include `quantumAlphabet: "ACGT"` and identify the actual algorithm that produced it.

# Hybrid Classical Mutation Analysis

## Scope

- Repository: `quantum-helix-lab-full`
- Branch: `feature/hybrid-classical-mutation-analysis`
- Results mode: Hybrid only
- Input assumption: the user pastes two normalized, equal-length A/C/G/T sequences.

## Biological Analyses Available from Two Sequences

1. List every substitution as reference base to query base.
2. Report both the circuit's zero-based coordinate and a biologist-facing one-based position.
3. Classify each substitution as a transition or transversion.
4. Calculate the mutation count and mutation rate.
5. Count transitions, transversions, and the transition/transversion ratio.
6. Show all 12 directed substitution classes in a mutation-spectrum chart.
7. Show local reference and query sequence context around every substitution.
8. Retain the corresponding Hybrid measurement state, probability, and shot count.

## Explicit Limits

- Pasted strings alone do not identify a genome assembly, chromosome, accession,
  transcript, gene model, feature strand, or reading frame.
- Therefore the page must not claim genomic coordinate mapping, gene/feature
  annotation, codon consequences, protein effects, or clinical interpretation.
- Equal-length A/C/G/T comparison supports substitutions only. It does not call
  insertions, deletions, frameshifts, or structural variants.
- Classical mutation identity is derived directly from the two strings. Quantum
  probability remains circuit output and is not biological confidence or
  pathogenicity.

## UI Plan

1. Derive a deterministic mutation-analysis model from the returned query and
   reference strings.
2. Add a compact classical-analysis summary to the Hybrid results.
3. Expand the Hybrid mutation table with identity, class, and sequence context.
4. Add a 12-class substitution-spectrum chart beside the quantum mutation chart.
5. Export the enriched Hybrid mutation table to CSV.
6. Preserve the existing styling, quantum distribution, noise analysis, and
   circuit metrics.

## Verification Plan

- Unit-test substitution classification, mutation positions, contexts, spectrum,
  mutation rate, and all-match behavior.
- Run targeted frontend lint.
- Run the production frontend build.

## Change Log

- Created the dedicated feature branch.
- Added a pure sequence-analysis module for substitution identity, coordinate
  systems, transition/transversion classification, contexts, summary metrics,
  and the 12-class spectrum.
- Replaced the Hybrid candidate-only table with an enriched table containing
  every actual reference-to-query substitution and its quantum measurement.
- Added a Hybrid classical-analysis summary and substitution-spectrum chart.
- Expanded Hybrid CSV export with the new biological fields.
- Preserved the existing quantum distribution, mutation-probability chart,
  noise comparison, and circuit-metrics visualization.

## Verification

- `bun test src/lib/hybridMutationAnalysis.test.ts` — 4 passed, 0 failed.
- `bunx eslint src/components/QuantumSearch.tsx src/lib/hybridMutationAnalysis.ts src/lib/hybridMutationAnalysis.test.ts`
  — passed.
- `npm run build` — passed.

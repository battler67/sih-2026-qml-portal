# Classical vs Quantum Scaling

## Scope

- Branch: `feature/classical-quantum-scaling`
- Source prompt: `cacheResults/prompt.txt`
- Add a responsive scaling section at the bottom of the Quantum Search form.
- Include a local selector for all three modes: FRQI, Grover, and Hybrid.
- Preserve the existing visual system and avoid any wall-clock speedup claim.
- Revision: the visible portal form contains only algorithm, reference length
  `N`, query length `m`, and marked count `K/M`. It shows complexity cards and a
  graph, not projected time or the three detailed limitation panels.

## Formula contract

All equations and timing assumptions live in `src/lib/scaling-formulas.ts`. UI
components consume the returned model and do not duplicate mathematical logic.
The exported formula set is replaceable so future formula changes do not require
rewriting the cards or chart.

### Shared inputs

- `N_r`: reference length.
- `N_q`: query length.
- `M`: marked items. In Hybrid this is the number of substitutions; in Grover
  this is the number of exact matching candidate positions.
- `t_g`: assumed average gate duration in nanoseconds.

### Hybrid

- Equal length is required: `N = N_r = N_q`.
- Classical direct comparison: `C_classical = N`.
- Ideal known-M query reference:
  `Q_ideal = ceil((pi / 4) * sqrt(N / M))` for `0 < M < N`.
- The implemented unknown-M YLC schedule uses `lambda_min = 1/N`; its predicate
  query count is derived from the same shortest-odd-sequence construction as the
  backend and does not use the actual `M`.
- Projected search-stage gates use an explicit, replaceable high-level model.
  The result is labeled projected and excludes DNA loading, transpilation,
  routing, queueing, readout, reset, and error-correction overhead.

### Grover

- Candidate search space: `S = max(0, N_r - N_q + 1)`.
- Classical exhaustive candidate checks: `C_classical = S`.
- Best-case Grover query complexity with `K=M` marked candidates:
  `Q = ceil((pi / 4) * sqrt(S / K))`, with `O(1)` when every candidate is
  marked and no solution projection when `K=0`.
- Pattern-check work inside an oracle is shown separately; it is not hidden
  inside the square-root query count.

### Timing projections

- Classical projection:
  `T_classical = C_classical * t_comparison`.
- Quantum search-stage projection:
  `T_quantum = G_projected * t_g`.
- Both are assumption-driven projections, not measured runtime. Qiskit/Aer
  execution time is never used as evidence of quantum hardware speedup.

## Required limitations

- DNA loading/oracle construction may require `O(N)` work.
- Reporting all `M` mutation positions adds output and sampling cost.
- The comparison is a theoretical query-complexity advantage inside the search
  circuit, not a proven end-to-end wall-clock speedup.
- Projected hardware time is not measured hardware time.

## Planned files

- `src/lib/scaling-formulas.ts`
- `src/lib/scaling-formulas.test.ts`
- `src/components/ScalingComparisonCard.tsx`
- `src/components/ScalingComparisonChart.tsx`
- `src/components/ClassicalQuantumScaling.tsx`
- `src/components/QuantumSearch.tsx`
- `docs/CLASSICAL_QUANTUM_SCALING.md`
- `docs/QUANTUM_COMPLEXITY_FORMULAS.md`
- `docs/QUANTUM_SEARCH.md`
- `README.md`

## Verification log

- `bun test src/lib/scaling-formulas.test.ts`: 9 passed, including FRQI,
  multiple Hybrid `N/M` cases, and Grover best-case coverage.
- Combined scaling and existing affected frontend utilities: 19 passed.
- Focused ESLint passed for the new components, formula module/tests, and
  `QuantumSearch.tsx` with the unrelated whole-file Prettier rule disabled.
- Prettier check passed for every new source, test, documentation, and spec file.
- `bun run build` passed client, SSR, and Nitro production builds.
- The live port `8080` module contains all three selector choices and none of
  the three removed limitation panels or the removed gate-duration field.
- Added `docs/QUANTUM_COMPLEXITY_FORMULAS.md` as the dedicated reference for
  gate, space, circuit-depth/time, and query formulas across all three modes.
- Refactored action availability so Estimate is clickable and explains invalid
  inputs, simulator Run Search is enabled only by a fresh within-resource
  estimate, and Real Hardware is not blocked by frontend estimate eligibility.
- Added focused availability tests in
  `src/lib/quantum-action-availability.test.ts`.

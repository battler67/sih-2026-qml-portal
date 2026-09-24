# Hybrid fixed-point mismatch experiment

Date: 2026-07-27

## Goal

Enable the application's Hybrid mode with a Qiskit experiment that:

- compares equal-length A/C/G/T sequences coherently at every position;
- never builds a list of mismatch positions in Python;
- does not use the number of mismatches, `M`, to choose the amplification length;
- applies Yoder-Low-Chuang (YLC) fixed-point amplitude amplification;
- returns measurement-inferred mismatch candidates and honest resource/circuit metadata.

## Design

1. Encode the reference and query bases as two-bit symbols in reversible
   position-controlled lookup circuits (QROM-style gate synthesis).
2. Compute the mismatch predicate inside the circuit by XORing the two loaded
   symbols and reversibly ORing the difference bits into a flag.
3. Apply the mismatch phase to that computed flag and uncompute all work.
4. Use the YLC analytic phase schedule. Select its odd length `L` only from a
   configured lower bound `lambda_min = 1/N` and failure amplitude `delta`, not
   from the actual mismatch count.
5. Measure only the position register. Rank windows by the measured probability
   mass above the uniform baseline; keep any exact classical comparison outside
   the quantum engine as an optional validation layer.

The input sequences remain classical and are compiled into lookup gates. This
is coherent mismatch evaluation over a bounded circuit input, not free QRAM and
not a claim of end-to-end quantum genomic search.

## Planned files

- `quantum_search_api/services/quantum/hybrid_search.py`
- `quantum_search_api/services/search/search_orchestrator.py`
- `quantum_search_api/services/ncbi/models.py`
- `quantum_search_api/tests/test_hybrid_search.py`
- `quantum_search_api/examples/run_hybrid_fixed_point_experiment.py`
- `quantum_search_api/outputs/hybrid_fixed_point/*`
- `Rit_Grover_project/quantum-helix-lab/src/components/QuantumSearch.tsx`
- `docs/QUANTUM_SEARCH.md`

## Task log

- Branch: current working tree (no branch/history rewrite requested).
- 2026-07-27: Confirmed existing Hybrid backend and UI paths were disabled
  placeholders.
- 2026-07-27: Confirmed the older `quantum_dna` oracle classically computes
  mismatch positions and `M`; this experiment is intentionally a separate,
  coherent predicate implementation.
- 2026-07-27: Added reversible two-bit lookup, XOR/OR mismatch computation,
  YLC schedule generation, phase-shifted target/source reflections, Aer
  execution, shot candidate inference, and resource metadata.
- 2026-07-27: Enabled Hybrid request validation, orchestration, estimation, and
  frontend Estimate/Run controls.
- 2026-07-27: Added a reproducible artifact generator and focused tests.
- 2026-07-27 experiment `ACGTACGT / ATGTACAT`: measured candidates `[1, 6]`;
  exact probability `0.480774` on each mismatch and `0.006409` on each
  unmarked position; `L=7`, three generalized iterations, six predicate
  queries, 10 logical qubits.
- Created 13 artifacts under
  `quantum_search_api/outputs/hybrid_fixed_point`, including actual QASM,
  text circuits, predicate PNG, probability PNG/CSV, JSON, and report.
- Added the full mathematical explanation, register derivation, fixed-point
  phase equations, numerical experiment, complexity, and limitations in
  `docs/HYBRID_FIXED_POINT_MATHEMATICS.md`.
- Verification: `python -m pytest quantum_search_api/tests -q
  --disable-warnings` passed (33 tests); frontend `npm run build` passed.

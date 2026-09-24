# Grover Sparse Noise Performance

## Problem

The Grover Add Noise path transpiles and simulates the complete QGSA circuit four times:
one ideal run plus global depolarizing-noise runs at 1x, 2x, and 3x. QGSA output
artifacts show that decomposition can produce thousands to hundreds of thousands of
gates, so attaching noise to every `u` and `cx` operation makes Aer simulation slow.

## Measured evidence

- `qgsa_grover/outputs/non_power_acgta_gta/result.json`:
  - 36 logical qubits
  - transpiled depth 288,125
  - 148,860 transpiled CX gates
- Representative portal-sized `ACG` / `CG` circuit:
  - 20 qubits
  - transpiled depth about 5,955
  - the least-used `u` qubit has one gate occurrence
  - the least-used CX pair has two gate occurrences
- Explicit quantum-channel insertion was still slow.
- A targeted Aer noise model with `matrix_product_state` completed 16 shots in
  approximately 0.66 seconds.

## Implementation

- Transpile the Grover comparison circuit once and reuse it for ideal and noisy runs.
- Select the least-used transpiled `u` qubit and CX qubit pair.
- Apply noise only when their combined occurrence count is at most four.
- Use Aer `matrix_product_state` for Grover noise comparisons.
- Preserve 1x/2x/3x linear zero-noise extrapolation.
- Cap only the optional Grover noise comparison at 128 shots. The original search and
  its configured shots remain unchanged.
- Return requested/executed shots, selected qubits, affected/total gate occurrences,
  coverage fraction, simulator method, and the sparse-model limitation.

## Scientific boundary

This is a sparse sensitivity experiment, not a full-device or full-circuit hardware
noise model. The API and UI must report that limitation explicitly.

## Verification

- Sparse target selection never exceeds four affected gate occurrences: verified.
- Noise response exposes accurate scope and shot-cap metadata: verified.
- Representative 20-qubit benchmark:
  - 13.582 seconds for ideal plus 1x/2x/3x sparse comparisons
  - 3 of 7,168 eligible transpiled gate occurrences affected
  - 128 executed shots from 512 requested
- The ideal search result remains unchanged: verified by API regression test.
- Existing FRQI and Hybrid noise behavior remains unchanged: verified.
- Focused noise/API suite: 12 passed.
- Complete backend suite: 47 passed.
- Frontend targeted ESLint and production build: passed.

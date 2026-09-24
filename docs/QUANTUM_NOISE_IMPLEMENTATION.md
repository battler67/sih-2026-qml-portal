# Optional Quantum Noise Comparison

## Overview

The results page keeps the normal ideal search unchanged. **Add Noise** runs a separate,
cached Qiskit Aer comparison for the current job's top-ranked processed window. The page then
shows ideal, noisy, and mitigated probabilities together.

## Algorithm-to-noise mapping

| Algorithm | Noise model | Why relevant | Mitigation |
| --- | --- | --- | --- |
| FRQI | Rotation and controlled-gate error | FRQI information is encoded through controlled rotations | Circuit optimization |
| Grover/QGSA | Sparse targeted depolarizing error | Oracle and diffuser can decompose into thousands of gates, so the optional sensitivity run targets only the least-used locations | Zero-noise extrapolation |
| YLC | Readout error | Final result depends strongly on measured bitstrings | Readout-error mitigation |

## Implemented sections

- On-demand `POST /api/quantum-search/jobs/{job_id}/noise`
- Per-job comparison caching without overwriting ideal results
- Shared noise models and mitigation helpers
- FRQI `u`/`cx` noise with optimization level 3
- Grover sparse 1x/2x/3x noise scaling with linear success-probability extrapolation
- YLC assignment-matrix readout correction
- Qubit guard for expensive noise simulations
- Responsive result cards, comparison chart, circuit metrics, and noise parameters
- Algorithm-specific results-page controls for configuring the simulated error rates
- API validation that accepts only probabilities from `0` through `0.5`
- Parameter-aware caching, so each distinct configuration gets its own comparison
- Noise state reset when the results job changes

## Exact implementation points

| Algorithm | Circuit builder | Noisy gates | Parameters | Mitigation |
| --- | --- | --- | --- | --- |
| FRQI | `build_measured_comparison_circuit` | transpiled `u`, `cx` | configurable single-/two-qubit rates; defaults 0.002, 0.01 | optimization level 3 |
| Grover | `build_qgsa_circuit` | least-used transpiled `u` qubit and `cx` pair, at most four affected occurrences | configurable base rates; defaults 0.001, 0.015 at 1x/2x/3x | linear ZNE of target probability |
| YLC | `build_hybrid_fixed_point_circuits` | measured position bits | configurable `0 -> 1`/`1 -> 0` rates; defaults 0.03, 0.04 | local matrix inversion, clipping, normalization |

All runs use the original shot count and deterministic simulator/transpiler seed 42. Qiskit
bitstrings are displayed most-significant bit first. These are Aer simulations, not hardware runs.

Grover is the exception to the original-shot rule: its optional noise comparison uses at most
128 shots and Aer `matrix_product_state`, while the original ideal search keeps the user's full
configured shot count. The Grover response reports requested and executed shots, selected qubits,
affected and total eligible gate occurrences, and coverage fraction. This is a sparse sensitivity
experiment rather than a full-circuit hardware-noise claim.

## Manual check

1. Run a normal quantum search.
2. Open the results page and confirm the ideal output remains visible.
3. Set the algorithm-specific rates in **Noise configuration**, or keep the defaults.
4. Click **Add Noise**.
5. Confirm the loading label appears.
6. Confirm Ideal, Noisy, and Mitigated cards, the chart, and the applied parameters appear.
7. Change a rate and confirm the previous comparison clears before the next run.
8. Change to another job and confirm the previous comparison disappears.

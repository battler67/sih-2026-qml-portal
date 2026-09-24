# Unknown-M hybrid fixed-point amplification experiment

## Goal

Build and verify one Qiskit circuit that amplifies DNA mismatch positions
without first calculating the mismatch positions or mismatch count `M` in
Python.

## Circuit design

1. Prepare a uniform superposition of valid position indices.
2. Reversibly load two-bit DNA symbols for the reference and query strings.
3. Compute their bitwise XOR and a coherent `different` flag.
4. Apply the Yoder-Low-Chuang fixed-point target phase.
5. Uncompute the flag, XOR, and loaded data.
6. Apply the matching fixed-point source phase.

The schedule uses only the conservative lower bound `lambda_min = 1/N` and a
chosen failure-amplitude bound `delta`; it never uses `M`.

## Verification

Run one exact statevector experiment for `ACGT` versus `ATGA`, whose expected
mismatch indices are supplied directly as `[1, 3]` for verification. Check:

- total probability on `[1, 3]` exceeds the fixed-point guarantee;
- every work qubit is returned to zero;
- the circuit source contains no call to the legacy classical mismatch helper.

## Scientific boundary

The two DNA strings are classical inputs used to synthesize reversible QROM
lookup gates. The circuit evaluates equality coherently across a superposition
of positions; it does not receive precomputed mismatch positions or `M`.
This is a proof-of-concept lookup model, not a claim that fault-tolerant QRAM is
free or that a quantum speedup has been demonstrated.

## Full implementation plan

The initial one-circuit experiment passed on 2026-07-27. The expanded task on
2026-07-28 is to make the experiment reproducible at the same level as the
existing FRQI-Grover proof of concept.

Planned files:

- `quantum_dna/src/fixed_point_hybrid.py`: circuit primitives, phase schedule,
  coherent oracle, complete circuit assembly, and exact verification.
- `quantum_dna/src/fixed_point_analysis.py`: exact/Aer analysis API and
  artifact orchestration.
- `quantum_dna/src/fixed_point_cli.py`: standalone command-line interface.
- `quantum_dna/src/models.py`: machine-readable fixed-point result model.
- `quantum_dna/src/visualization.py`: fixed-point schedule/success plots and
  QASM3 export helpers.
- `quantum_dna/examples/run_fixed_point_experiments.py`: reproducible cases
  with manually disclosed verification truth.
- `quantum_dna/tests/test_fixed_point_hybrid.py`: oracle, schedule, cleanup,
  guarantee, padding, shot, artifact, and export checks.
- `quantum_dna/FIXED_POINT_HYBRID.md`: method, equations, use, claims,
  scaling, qBraid preparation, and limitations.
- `quantum_dna/outputs/fixed_point_hybrid/`: generated experiment artifacts.

Verification sequence:

1. Run the fixed-point focused tests.
2. Run the full `quantum_dna/tests` suite.
3. Generate all fixed-point experiment directories and the combined summary.
4. Parse every generated JSON and QASM file, inspect every PNG signature, and
   confirm every recorded artifact path exists.
5. Record exact commands, counts, numerical results, and any unavailable
   hardware dependency here.

Real-QPU submission is intentionally outside automatic generation because it
can consume credits. The generated OpenQASM artifacts and readiness manifest
prepare the experiment without falsely recording a remote execution.

## Task log

- 2026-07-27: Added the coherent two-bit QROM/XOR comparator and shortest
  unknown-`M` fixed-point schedule. The `ACGT/ATGA` exact experiment reached
  `0.961856224307` target probability with clean-work probability `1.0`.
- 2026-07-28: Expanded scope to full code, artifacts, tests, documentation,
  and qBraid-ready exports.
- Added the full analysis API, CLI, reusable component circuits, typed result
  model, exact/Aer simulation, schedule and success-curve plots, QASM2/QASM3
  exports, qBraid readiness manifests, five-case generator, output auditor,
  focused tests, and `FIXED_POINT_HYBRID.md`.
- Initial generation showed that the legacy `1/N + 1/shots` readout threshold
  could label ordinary shot noise in uniform controls. Replaced it with a
  conservative four-binomial-standard-deviation threshold and regenerated all
  results. The no-mismatch and all-mismatch controls now infer no localized
  positions.
- Verified the simulated probabilities against the independent closed-form
  Chebyshev success polynomial for one, two, three, and four marked positions.
- Final focused regression:
  `python -m pytest quantum_dna\tests -q --disable-warnings` -> `34 passed`.
- Final generator:
  `python -m quantum_dna.examples.run_fixed_point_experiments` -> five
  complete experiment sets, each with 46 recorded artifacts.
- CLI smoke:
  `python -m quantum_dna.src.fixed_point_cli --reference ACGT --query ATGA
  --verification-positions 1,3 --shots 1024 --output-dir
  quantum_dna\outputs\fixed_point_hybrid\cli_smoke` -> passed.
- Final artifact audit:
  `python -m quantum_dna.examples.audit_fixed_point_outputs` -> 42 valid JSON,
  92 valid PNG, 50 parsed QASM2, 5 checked QASM3, 6 reports with limitations,
  6 result files, and 243/243 recorded artifact paths present.
- Output tree: 245 files, 11,606,486 bytes.
- qBraid SDK was not installed in this environment. Each readiness manifest
  records `submitted=false`; no remote device was selected and no credits were
  consumed.

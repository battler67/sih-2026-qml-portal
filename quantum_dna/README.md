# FRQI–Grover DNA Mutation Localization

This standalone Qiskit proof of concept explores an **FRQI-inspired DNA state
representation combined with a reversible mutation-position phase oracle and
FRQI-compatible amplitude amplification**. It addresses the hackathon's
quantum DNA-analysis objective without frontend, database, NCBI, or web
integration.

It is a simulator demonstration, not evidence of quantum advantage or a
clinical interpretation system.

## Research basis and contribution

Kösoglu-Kind et al., *Scientific Reports* 13, 14552 (2023), represent a
sequence as position qubits plus a rotation-encoded DNA/color qubit. A strip
qubit selects two sequences; interference of that strip gives a global
angle-overlap score. The baseline module reproduces this experiment and uses
the paper's formula `similarity = 1 - 2 P(strip=1)`.

Li et al., *Computational and Structural Biotechnology Journal* 30 (2025),
apply a Boolean match oracle and Grover diffusion to biological pattern
matching. Their contribution motivates phase marking, reversible uncomputation,
and amplitude amplification.

This project combines the ideas to localize substitutions. It deliberately
separates nonorthogonal FRQI value states from the Boolean predicate Grover
needs. For this proof of concept, the finite A/C/G/T inputs are compared
classically to synthesize position-controlled phase gates:

`f(i) = 1` exactly when `reference[i] != query[i]`.

That preprocessing is also used to choose the iteration count. It is not hidden
and is a major scalability assumption.

## Encoding and mathematics

The exact central mapping from the FRQI paper is in `src/config.py`:

| Base | paper state angle passed to Qiskit `RY` | paper decomposition rotation |
|---|---:|---:|
| A | π | π/4 |
| C | π/2 | π/8 |
| T | π/6 | π/24 |
| G | 0 | 0 |

Qiskit uses `RY(α)|0> = cos(α/2)|0> + sin(α/2)|1>`. Passing the
paper state angle reproduces its reported probability convention; the smaller
decomposition angles are recorded but are not passed directly to `RY`.

For `N` bases and `n = max(1, ceil(log2 N))`, the paired preparation is

```text
|Psi> = A|0> =
  1/sqrt(N) sum_{i=0}^{N-1} |i>
  (cos(alpha_ref,i/2)|0> + sin(alpha_ref,i/2)|1>)
  (cos(alpha_qry,i/2)|0> + sin(alpha_qry,i/2)|1>).
```

The phase oracle is

```text
O_f |i>|ref_i>|qry_i> = (-1)^f(i) |i>|ref_i>|qry_i>.
```

The reliable implementation synthesizes one phase operation for every known
mismatch position. It does not claim that one nonorthogonal color qubit can
perfectly discriminate all four nucleotides.

The prepared-state reflection is

```text
D_A = A S_0 A†,
S_0 = I - 2|0...0><0...0|,
Q = D_A O_f
```

up to a physically irrelevant global sign convention. The circuit applies
`A`, then repeats `O_f` followed by `D_A`. This is mathematically valid even
while the position and FRQI color registers are entangled. A position-only
generalized diffuser helper is also provided, but it is valid only after all
color/work registers have been uncomputed or when the prepared state contains
only the position register.

For `M` mutations among `N` valid positions:

```text
theta = asin(sqrt(M/N))
r = round(pi/(4 theta) - 1/2).
```

`M=0` skips Grover safely. `M=N` also uses zero iterations because marking the
entire search space cannot improve localization.

## Registers

The localization circuit uses:

- `pos[n]`: little-endian position register, measured into `c_pos[n]`;
- `ref[1]`: reference FRQI color qubit;
- `qry[1]`: query FRQI color qubit.

Total logical qubits: `n + 2`. Length 4 uses 4 qubits; lengths 5–8 use 5.
The separate baseline circuit uses `strip[1] + pos[n] + dna[1]`, also `n+2`.

For non-powers of two, a reversible `StatePreparation` creates exactly uniform
amplitude on `0..N-1`; padded basis states start with zero amplitude, are never
marked, and the `A S_0 A†` reflection preserves the intended valid-position
search space.

## Install and run

From the repository root:

```powershell
python -m pip install -r quantum_dna\requirements.txt
python -m quantum_dna.src.cli `
  --reference ACGT `
  --query ACTT `
  --shots 8192 `
  --backend aer `
  --save-circuits `
  --output-dir quantum_dna\outputs\demo
```

Python integration:

```python
from quantum_dna import analyze_sequences

result = analyze_sequences(
    reference="ACGT",
    query="ACTT",
    shots=8192,
    backend_type="aer_simulator",
)
print(result.to_dict())
```

Run examples and all required experiments:

```powershell
python -m quantum_dna.examples.demo_single_mutation
python -m quantum_dna.examples.demo_multiple_mutations
python -m quantum_dna.examples.run_required_experiments
```

Run tests:

```powershell
python -m pytest quantum_dna\tests -q
```

## Outputs

Each required experiment directory contains:

- baseline, reference, query, combined-state, oracle, diffuser, one-iteration,
  full-final, Aer-transpiled, and representative IBM-basis circuits;
- `.png`, text, and QASM2 artifacts where export is supported;
- before/after histograms, alignment, expected/detected mutation JSON, and
  circuit metric plot;
- `result.json` and `report.txt`.

All position outputs are zero-based internally. Mutation records also provide a
one-based position. Qiskit count keys are normal binary renderings of the
little-endian measured register.

Results distinguish `oracle_marked_positions_zero_based` (the disclosed
classical truth used to synthesize the phase oracle) from
`measured_detected_positions_zero_based` (peaks inferred from Aer shot
probabilities). This avoids presenting classical oracle construction as though
it had been independently discovered by the circuit.

## Optional IBM Quantum preparation

Simulator use requires no account. Hardware support is deliberately lazy:

```powershell
python -m pip install qiskit-ibm-runtime
$env:IBM_QUANTUM_TOKEN="..."
$env:IBM_QUANTUM_CHANNEL="ibm_quantum_platform"
$env:IBM_QUANTUM_INSTANCE="optional-instance"
$env:IBM_QUANTUM_BACKEND="explicit-backend-name"
```

Then call `prepare_for_ibm_backend(circuit)` from
`quantum_dna.src.hardware_adapter`. It selects/resolves a backend and reports
backend name, transpiled depth, gate counts, qubit layout, and circuit. It
**does not submit a job**. If Runtime or credentials are unavailable it returns
a local Aer preparation unless `simulator_fallback=False`. Tokens are never
hardcoded. Saved-account resolution is supported when no token environment
variable is set.

Real submission is a separate, explicit action:

```python
from quantum_dna.src.hardware_adapter import submit_to_ibm_hardware

job = submit_to_ibm_hardware(
    measured_circuit,
    backend_name="explicit-backend-name",
    shots=8192,
    confirm_real_hardware=True,
)
```

This call may consume paid allocation and is never invoked by tests, examples,
or simulator analysis.

## Limitations and next research steps

- Only equal-length substitutions are supported. Alignment, insertions,
  deletions, ambiguity symbols, reverse complements, and long sliding windows
  are future work.
- The reliable oracle and iteration count use classical mismatch knowledge.
  Potential Grover speedup requires an efficient coherent data-loading and
  mismatch oracle model; state preparation and QRAM cannot be assumed free.
- FRQI angle states are nonorthogonal. An angle-difference/threshold oracle
  would be experimental and is not substituted for the exact Boolean oracle.
- Direct multi-controlled rotations and prepared-state diffusion create deep
  transpiled circuits. Whole-genome execution is not practical on current
  hardware, and noise studies are still required.
- The paper's FRQI score is an angle-overlap score, not Hamming identity. The
  returned `similarity_percentage` for mutation reporting is classical percent
  identity; baseline FRQI values are reported separately without silently
  changing the paper formula.
- Measurement frequencies demonstrate amplitude localization; they are not
  biological or clinical confidence.

Next work should compare generalized versus explicitly uncomputed
position-only amplification, develop reversible sequence-access assumptions,
study robust fixed-point amplification when `M` is unknown, add noisy backend
models and error mitigation, and perform a broader literature/patent review
before making novelty claims.

## Coherent fixed-point hybrid extension

The unknown-`M` extension is now implemented separately from the original
classically synthesized oracle. It loads two-bit DNA symbols reversibly,
computes inequality with coherent XOR/OR gates, uncomputes all work registers,
and applies matched fixed-point phases selected from `lambda_min=1/N` rather
than the actual `M`.

See [FIXED_POINT_HYBRID.md](FIXED_POINT_HYBRID.md) for the mathematics, CLI,
artifacts, qBraid-ready export, supported claims, and scaling limitations.

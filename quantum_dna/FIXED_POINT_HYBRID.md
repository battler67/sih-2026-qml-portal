# Coherent unknown-M fixed-point DNA mismatch amplification

## What this experiment changes

The earlier FRQI-Grover proof of concept constructs its phase oracle from a
classically calculated mismatch-position list and chooses the Grover iteration
count from the classically known number of mismatches `M`.

This experiment removes both dependencies from circuit construction:

- no mismatch-position list is passed to the oracle;
- no value of `M` is passed to the amplification scheduler;
- two DNA bases are loaded as computational-basis data and compared by
  reversible gates while the position register is in superposition;
- a Yoder-Low-Chuang fixed-point schedule avoids Grover over-rotation when `M`
  is unknown.

It is still a hybrid proof of concept: the classical sequence strings are
compiled into explicit QROM-style controlled gates.

## Registers

For sequence length `N`, let `n = max(1, ceil(log2(N)))`.

| Register | Qubits | Purpose |
|---|---:|---|
| `pos` | `n` | position index |
| `ref_data` | 2 | loaded reference base |
| `qry_data` | 2 | loaded query base |
| `different` | 1 | reversible inequality flag |
| `c_pos` | `n` classical bits | measured position |

The circuit therefore uses `n + 5` logical qubits before any device-specific
routing ancillas.

## Basis encoding and coherent comparison

The exact two-bit basis encoding is:

```text
A -> 00
C -> 01
G -> 10
T -> 11
```

For every table bit equal to one, a position-controlled `X` loads that bit:

```text
sum_i |i>|00>|00>
    -> sum_i |i>|reference[i]>|query[i]>.
```

Two `CX` gates compute the bitwise XOR into `ref_data`. A reversible OR of the
two XOR bits sets `different=1` exactly when the bases differ. A phase
`exp(i beta)` is applied to that flag, after which the OR, XOR, and both
lookups are uncomputed.

The work registers return to `|00000>`; exact statevector verification records
their cleanup probability.

## Unknown-M fixed-point schedule

The implementation follows the matched-phase fixed-point amplitude
amplification of Yoder, Low, and Chuang:

<https://arxiv.org/abs/1409.3305>

For user-selected failure-amplitude bound `delta` and odd sequence parameter
`L=2l+1`,

```text
gamma = 1 / cosh(acosh(1/delta) / L)
w(L) = 1 - gamma^2.
```

The code chooses the shortest odd `L` satisfying:

```text
w(L) <= lambda_min.
```

By default, `lambda_min=1/N`: if any mismatch exists, at least one of the `N`
positions is marked. This is a lower-bound promise, not the actual `M/N`.

For round `j=1..l`, the matched phases are:

```text
alpha_j = 2 arccot(tan(2 pi j/L) sqrt(1-gamma^2))
beta_j  = -alpha_(l-j+1).
```

Each round applies the coherent target phase `S_mismatch(beta_j)` followed by
the prepared-position source phase `S_initial(alpha_j)`. If the promise holds,
ideal success is at least `1-delta^2`.

## Run

Install the existing environment:

```powershell
python -m pip install -r quantum_dna\requirements.txt
```

Generate all five experiment sets:

```powershell
python -m quantum_dna.examples.run_fixed_point_experiments
```

Run one CLI experiment:

```powershell
python -m quantum_dna.src.fixed_point_cli `
  --reference ACGT `
  --query ATGA `
  --verification-positions 1,3 `
  --shots 8192 `
  --delta 0.2 `
  --save-circuits `
  --output-dir quantum_dna\outputs\fixed_point_hybrid\cli_demo
```

Python API:

```python
from quantum_dna import analyze_fixed_point_sequences

result = analyze_fixed_point_sequences(
    "ACGT",
    "ATGA",
    verification_positions=[1, 3],
    shots=8192,
    delta=0.2,
    save_circuits=True,
    output_dir="quantum_dna/outputs/fixed_point_hybrid/demo",
)
```

`verification_positions` is disclosed experiment truth. The analysis builds
the circuit first and uses this list only afterward to score the output. It is
never passed to the lookup, comparator, oracle, or phase scheduler.

## Generated artifacts

Each experiment directory contains:

- position preparation, QROM pair loader, XOR comparator, coherent mismatch
  oracle, source phase, first round, final, measured, Aer-transpiled, and
  representative hardware-basis circuits;
- text circuit drawings, PNG circuit diagrams, and OpenQASM 2 exports;
- a qBraid-ready lowered OpenQASM 3 program;
- before, exact-after, and shot-after probability histograms;
- DNA alignment, circuit metrics, phase schedule, and theoretical success
  curve plots;
- schedule, verification truth, measurement inference, resource estimate,
  representative hardware metrics, and qBraid readiness JSON;
- complete `result.json` and human-readable `report.txt`.

Shot-based positions are called amplified only when their probability exceeds
the uniform null by four binomial standard deviations. This conservative rule
prevents ordinary shot noise in the no-mismatch control from being presented
as a detected mutation.

## qBraid preparation

The generated `fixed_point_qbraid_ready.qasm3` is a preparation artifact, not
evidence of hardware execution. `qbraid_readiness.json` records:

- whether the qBraid SDK was installed during generation;
- that no job was submitted;
- that no target device was silently assumed;
- the need for a device-specific transform and compiled-depth review.

qBraid supports program conversion and device-specific transforms, but device
paradigm, gate set, connectivity, availability, and pricing must be inspected
before using credits:

- <https://docs.qbraid.com/sdk/user-guide/transforms>
- <https://docs.qbraid.com/lab/user-guide/quantum-jobs>

Automatic paid submission is intentionally excluded. A real job should be
submitted only after selecting a compatible gate-model QPU and explicitly
approving the expected credit use.

## Supported claims

The generated evidence supports these statements:

1. Both bases are compared coherently with quantum gates across a position
   superposition.
2. Circuit construction does not receive mismatch positions.
3. Phase scheduling does not receive the actual number of mismatches `M`.
4. The work registers are uncomputed in the ideal circuit.
5. Fixed-point amplification raises total marked-state probability to the
   promised ideal bound in the verified nonzero-mismatch cases.

## Claims that are not supported

Do not claim:

- end-to-end quantum advantage;
- efficient physical QRAM;
- whole-genome readiness on current noisy hardware;
- that a simulator run is a real-QPU experiment;
- that measurement frequency is biological confidence;
- that the approach is fully quantum from data acquisition onward.

## Scaling limitation

The position register grows logarithmically, but the explicit table loader
does not. It uses `O(N)` position-controlled operations for each phase oracle.
The fixed-point procedure then calls this oracle multiple times. Therefore,
counting only logical qubits creates a misleading scaling picture: a
108-qubit device may have enough width while still lacking the fidelity and
depth budget for a useful long-sequence circuit.

A future end-to-end advantage argument requires an efficient coherent-access
model, algorithmically generated data, or another predicate that avoids
explicitly compiling every table entry, followed by a fair scaling comparison
against an optimized classical implementation.

## Verified local results

All experiments used `delta=0.2`, so the promised ideal success probability
was `1-delta^2 = 0.96` whenever at least one mismatch existed.

| Case | Verification positions | Inferred positions | Exact target probability | Clean work |
|---|---|---|---:|---:|
| no mismatch | `[]` | `[]` | `0` | `1.0` |
| single mismatch | `[3]` | `[3]` | `0.999348258290` | `1.0` |
| multiple mismatches | `[1, 3]` | `[1, 3]` | `0.961856224307` | `1.0` |
| non-power-of-two | `[1, 4]` | `[1, 4]` | `0.967227599275` | `0.999999999999979` |
| all mismatch | `[0, 1, 2, 3]` | `[]` | `1.0` | `1.0` |

The all-mismatch case has total target probability one but no localized peak:
all positions remain equally valid targets. Reporting no inferred localized
position is therefore intentional.

Final verification:

```text
34 tests passed
42 JSON files valid
92 PNG files valid
50 OpenQASM 2 files parsed
5 OpenQASM 3 files checked
243 recorded artifact paths exist
```

The output tree is under `quantum_dna/outputs/fixed_point_hybrid`. No remote
job was submitted and no qBraid credits were consumed.

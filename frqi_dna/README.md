# FRQI DNA Sequence Comparison in Qiskit

This project reproduces the FRQI-based DNA sequence comparison method from
Koesoglu-Kind et al., "A biological sequence comparison algorithm using quantum
computers", Scientific Reports 13, 14552 (2023).

The implementation is intentionally limited to the paper's FRQI-style sequence
encoding and strip-qubit comparison. It does not implement Grover search,
Grover oracles, diffusion operators, mutation localization, a web frontend, or a
binary A/C/G/T register encoding.

## Paper Method Summary

FRQI represents an image by putting position qubits into superposition and
rotating a color qubit by an angle controlled on each position. The DNA
adaptation treats a nucleotide sequence as a one-dimensional image:

- the position register addresses residue positions;
- the DNA-value qubit is the FRQI color qubit;
- nucleotide identity is encoded by a parameterized rotation angle;
- a strip qubit selects which sequence is being encoded.

For two equal-length sequences, strip `0` encodes the reference sequence and
strip `1` encodes the comparison sequence. After state preparation, a Hadamard
gate is applied to the strip qubit and then the strip qubit is measured. The
probability `P1 = P(strip=1)` is converted into the paper's similarity score:

```text
similarity(sequence1, sequence2) = 1 - 2 P1
```

This is a global angle-overlap similarity. It is not ordinary Hamming identity,
and substitutions with different angular separations contribute differently.

## Quantum State

For sequence length `N`, the implementation prepares:

```text
|Psi> = 1/sqrt(2N) sum_s sum_i |s>|i>
        (cos(alpha_s,i / 2)|0> + sin(alpha_s,i / 2)|1>)
```

where `s in {0,1}`, `i` is a valid sequence position, and `alpha_s,i` is the
Qiskit `RY` angle for the nucleotide at strip `s`, position `i`.

Qiskit uses:

```text
RY(alpha)|0> = cos(alpha/2)|0> + sin(alpha/2)|1>
```

The paper also writes the FRQI color state as `cos(theta)|0> + sin(theta)|1>`.
Its Table 2 probabilities are reproduced by passing the paper's quantum-state
angle to Qiskit `RY`. For example, A vs T gives:

```text
P1 = (1 - cos((pi - pi/6)/2)) / 2 = 0.3705904774
```

This matches the paper's reported A-vs-T value of about `0.371` and the
four-position A/A/A/A vs T/T/T/T experiment.

The Table 1 "parameterized gate rotations" (`pi/4`, `pi/8`, `pi/24`, `0`) are
stored centrally too. They are consistent with the sub-rotation labels shown in
the decomposed three-controlled rotation diagrams, but passing them directly to
Qiskit `RY` does not reproduce Table 2.

## Nucleotide Mapping

The mapping is defined once in `src/config.py`.

| Base | Paper quantum-state angle | Paper parameterized gate rotation |
| ---- | ------------------------- | --------------------------------- |
| A | `pi` | `pi/4` |
| C | `pi/2` | `pi/8` |
| T | `pi/6` | `pi/24` |
| G | `0` | `0` |

Default angle mode:

```text
paper_state
```

Optional ambiguity-analysis modes:

```text
table_parameter_direct
frqi_color_angle
```

## Register Layout

For length `N`:

- `strip[0]`: reference branch `0`, query branch `1`;
- `pos[k]`: little-endian position bit `2**k`;
- `dna[0]`: nucleotide value/color qubit;
- `c[0]`: classical measurement bit for the strip qubit.

For a four-letter sequence the logical circuit has four qubits:

```text
strip[0], pos[0], pos[1], dna[0]
```

No explicit ancilla qubits are added by the source circuit. Qiskit may introduce
decomposition details during transpilation.

## Non-Power-of-Two Lengths

This project does not pad sequence positions as ordinary DNA. For non-power-of-
two lengths, it prepares an exact uniform state over valid positions only using
Qiskit state initialization; unused basis states have zero amplitude. This keeps
the measured strip probability from being biased by artificial padded matches.

For powers of two, the position register uses Hadamard gates exactly as in the
paper figures.

## Install

From the repository root:

```powershell
python -m pip install -r frqi_dna\requirements.txt
```

Installed environment used for this run:

```text
Python 3.13.1
Qiskit 2.5.0
qiskit-aer 0.17.2
```

## CLI

```powershell
python -m frqi_dna.src.cli `
  --reference ACGT `
  --query ACTT `
  --shots 8000 `
  --output-dir frqi_dna\outputs\acgt_actt `
  --save-circuits
```

The CLI prints `P(0)`, `P(1)`, raw similarity, theoretical similarity, circuit
depth, gate count, and artifact paths.

## Python API

```python
from frqi_dna.src.analysis import compare_dna_frqi

result = compare_dna_frqi(
    reference="ACGT",
    query="ACTT",
    shots=8000,
    simulator_type="aer",
)

print(result.p1)
print(result.similarity)
print(result.to_dict())
```

The public state-preparation circuit is:

```python
from frqi_dna.src.frqi_encoding import build_frqi_dna_state

circuit = build_frqi_dna_state("ACGT", "ACTT")
print(circuit.draw("text"))
```

## Examples

```powershell
python -m frqi_dna.examples.demo_identical
python -m frqi_dna.examples.demo_different
python -m frqi_dna.examples.demo_mixed
python -m frqi_dna.examples.run_required_experiments
```

## Tests

```powershell
python -m pytest frqi_dna\tests -q
```

Current result:

```text
19 passed
```

Pytest emitted a cache warning because the sandbox could not write its default
`.pytest_cache` directory; this does not affect the tests.

## Generated Artifacts

Each experiment folder contains:

- `position_superposition.*`
- `single_nucleotide_controlled_rotation.*`
- `reference_sequence_encoding.*`
- `query_sequence_encoding.*`
- `frqi_encoding.*`
- `comparison_circuit.*`
- `measured_circuit.*`
- `transpiled_circuit.*`
- `histogram.png`
- `statevector_probabilities.json`
- `result.json`
- `report.txt`

Circuit files are saved as text diagrams and PNG diagrams. QASM2 is saved where
Qiskit can export the circuit.

## Required Experiment Results

All experiments used `8000` Aer shots with seed `12345`.

| Experiment | Reference | Query | Theoretical P1 | Shot P1 | Theoretical similarity | Shot similarity |
| ---------- | --------- | ----- | -------------- | ------- | ---------------------- | --------------- |
| Identical A | `AAAA` | `AAAA` | `0.000000` | `0.000000` | `1.000000` | `1.000000` |
| A vs T repeated | `AAAA` | `TTTT` | `0.370590` | `0.371500` | `0.258819` | `0.257000` |
| One substitution | `AAAA` | `AAAT` | `0.092648` | `0.089625` | `0.814705` | `0.820750` |
| Mixed identical | `ACGT` | `ACGT` | `0.000000` | `0.000000` | `1.000000` | `1.000000` |
| Mixed substitution | `ACGT` | `ACTT` | `0.004259` | `0.003750` | `0.991481` | `0.992500` |
| Eight-base | `ACGTACGT` | `ACCTTCGT` | `0.064630` | `0.065000` | `0.870741` | `0.870000` |

The A-vs-T repeated experiment agrees with the paper's discussion: the paper
reports about `P1 = 0.378` from 8000 shots and a similarity of about `0.246`.
The ideal value from the encoded angle formula is `P1 = 0.370590` and
similarity `0.258819`; the seeded simulator run measured `P1 = 0.371500`.

## Circuit Metrics

Logical circuit metrics from the saved measured circuits:

| Reference | Query | Qubits | Depth | Size | Operation counts |
| --------- | ----- | ------ | ----- | ---- | ---------------- |
| `AAAA` | `AAAA` | 4 | 110 | 133 | `cu:56, cx:48, x:24, h:4, barrier:2, measure:1` |
| `AAAA` | `TTTT` | 4 | 110 | 133 | `cu:56, cx:48, x:24, h:4, barrier:2, measure:1` |
| `AAAA` | `AAAT` | 4 | 110 | 133 | `cu:56, cx:48, x:24, h:4, barrier:2, measure:1` |
| `ACGT` | `ACGT` | 4 | 84 | 101 | `cu:42, cx:36, x:18, h:4, barrier:2, measure:1` |
| `ACGT` | `ACTT` | 4 | 97 | 116 | `cu:49, cx:42, x:20, h:4, barrier:2, measure:1` |
| `ACGTACGT` | `ACCTTCGT` | 5 | 575 | 890 | `cx:312, t:208, tdg:156, h:109, x:52, ry:52, barrier:2, measure:1` |

The eight-base circuit is deeper because it uses one more position qubit and
therefore four-control rotations.

## Files

- `src/config.py`: central Table 1 mapping and defaults.
- `src/validation.py`: sequence validation and register sizing.
- `src/angle_mapping.py`: angle lookup and Qiskit angle-convention modes.
- `src/frqi_encoding.py`: strip/position/DNA registers and controlled rotations.
- `src/comparison_circuit.py`: final strip Hadamard and strip measurement.
- `src/simulator.py`: Statevector and AerSimulator execution.
- `src/analysis.py`: public `compare_dna_frqi` API and classical overlap check.
- `src/visualization.py`: circuit diagrams, histograms, JSON, and reports.
- `src/models.py`: result dataclasses.
- `src/cli.py`: command-line interface.
- `tests/`: pytest coverage.
- `examples/`: runnable demos and required experiment runner.
- `outputs/`: generated artifacts.

## Limitations

- This is a simulator-based reproduction, not a claim of quantum advantage.
- The score is a global FRQI angle-overlap score, not percentage identity.
- The nucleotide states are nonorthogonal, so this is not a perfectly
  distinguishable nucleotide encoding.
- The method does not locate mutation positions.
- Insertions, deletions, gaps, and alignment scoring are not implemented.
- Multi-controlled rotations become deep as sequence length grows.
- The paper's circuit diagrams show decomposition sub-rotations; the default
  Qiskit circuit applies the corresponding full controlled `RY` angle needed to
  reproduce the paper's probability table.

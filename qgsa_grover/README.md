# QGSA Grover DNA Exact-Pattern Search

This is a standalone Qiskit implementation of the Grover-based Quantum Gene Sequence Alignment (QGSA) algorithm from `Grover_rit.pdf`, "Developing a quantum computing model for sequence annotation of interferon protein".

QGSA is implemented here as a Grover-based quantum exact-pattern search circuit intended to replace or accelerate the candidate-location search stage of a larger sequence-alignment workflow. It is not a complete BLAST replacement: this project does not implement database retrieval, gapped local alignment, insertions/deletions, E-values, NCBI/GenBank access, web integration, authentication, deployment, FRQI encoding, or biological annotation by itself.

## Paper Understanding

The paper targets the second stage of BLAST: given selected words or pattern sequences, search candidate positions in a target/database sequence. The target sequence is the unknown or unannotated DNA sequence. The pattern sequence is a known DNA word or motif used to locate candidate matches. The proposed circuit encodes DNA bases, puts an index register into superposition, cyclically shifts the target according to the index, compares the shifted target prefix with the pattern, marks exact matches with a phase oracle, and applies Grover diffusion to amplify matching index states.

Section 2.1 gives the QGSA stages. Table 1 maps `A -> 00`, `C -> 01`, `G -> 10`, `T -> 11`. Eq. 1 is the initialized superposition over index states, target bits, and pattern bits. Eq. 2 is the index-controlled cyclic-shift state. Eq. 3 computes mismatches as `pattern_bit XOR shifted_target_bit` by CNOT. Eq. 4 flips phase only when all mismatch bits are zero. Eq. 5 defines diffusion as reflection about the uniform index state, implemented as `H`, all-zero reflection by MCZ, then `H`.

The paper's Figure 1 and Table 2 inherit a bit-level cyclic shift from the 01-string alignment algorithm, but the text explicitly warns that shifting DNA encodings one bit at a time corrupts nucleotide grouping. This implementation therefore shifts complete nucleotide units: two qubits per base in `paper_cyclic` mode and three qubits per symbol in boundary-safe terminator mode.

## Encoding

The central two-bit mapping lives in [config.py](src/qgsa_grover/config.py):

```text
A -> 00
C -> 01
G -> 10
T -> 11
```

Reusable helpers are provided by [encoding.py](src/qgsa_grover/encoding.py):

```python
encode_base("A")
encode_sequence("ACGT")
decode_base("00")
```

Lowercase input is normalized. Invalid DNA symbols are rejected unless terminator mode is used internally for boundary-safe padding.

## Registers And Endianness

The circuit register order is `idx`, `tgt`, `pat`, and optionally `c_idx`. The index register encodes candidate shift positions and is measured. The target register stores the target sequence in computational basis. The pattern register stores the pattern and is reused as the reversible mismatch register during oracle computation.

Within each nucleotide, offset 0 stores the left bit of the paper code. For example, `C -> 01` means the first qubit for that base remains `0` and the second is initialized with `X`.

Qiskit count strings are displayed with the highest classical bit on the left. Because this project measures `idx[i]` into `c_idx[i]`, a count key such as `00` is decoded as index position 0. This `00` index state is distinct from the base encoding `A -> 00`; reports label index measurements and base encodings separately.

## Algorithmic Stages

1. Validate and normalize target and pattern DNA strings.
2. Encode target and pattern into computational-basis registers.
3. Apply Hadamards to all index qubits.
4. Apply an index-controlled complete-base cyclic-shift network using CSWAP/Fredkin-style controlled swaps.
5. CNOT each shifted target-prefix bit into the corresponding pattern bit to compute mismatches.
6. Apply `X` to mismatch qubits, use an MCZ phase flip on the all-one state, then undo the `X` gates.
7. Uncompute the CNOT mismatch and inverse cyclic shift so target/pattern work registers are restored.
8. Apply manual Grover diffusion on only the index register.
9. Repeat the Grover iteration and measure the index register.
10. Validate the measured candidate positions against a classical exact-substring baseline.

The oracle is explicit; it is not implemented as a classical match list followed by a generic phase oracle. Classical matching is used only for tests, validation reporting, and the known-solution iteration mode.

## Boundary Modes

`paper_cyclic` reproduces the paper's small cyclic-search construction. All cyclic shifts are candidates, so wrap-around matches can be marked. This is useful for the paper example `target=ACGT`, `pattern=A`.

`boundary_safe` prevents linear false positives. Only positions `0` through `N-M` are marked by the oracle. The target is padded to a power-of-two symbol length with the paper's terminator idea. The paper explicitly gives `$ -> 100` but does not provide a full three-bit nucleotide table, so this implementation uses a documented engineering interpretation:

```text
A -> 000
C -> 001
G -> 010
T -> 011
$ -> 100
```

Invalid padded index states and positions beyond `N-M` are never marked. The test `target=AT`, `pattern=TA` verifies that a circular false match is rejected.

## Iterations

`iterations="paper"` reports the paper expression `floor(pi/4 * sqrt(N/M) + 1)`. For small validation experiments, if that count differs from the standard known-solution optimum, the implementation reports the paper value and executes the known-solution validation count so the experiment can be checked against exact statevector behavior.

`iterations="auto"` and `iterations="known_solution_validation"` use `floor(pi/4 * sqrt(S/K))` when the classical validator finds `K > 0` matches in search space `S`. When `K = 0`, zero Grover iterations are executed and the result reports `matches_found = false`.

## OPTIQUE Status

The unoptimized QGSA circuit is the main implementation. [optique.py](src/qgsa_grover/optique.py) implements the supported core of the paper's truth-table optimization: remove unused target qubits and reconstruct only the shifted target prefix from index-controlled truth-table logic. The paper refers to supplementary material for the clearest reconstruction subroutine, so this project marks OPTIQUE as partial rather than claiming an exact reproduction. For `ACGT`/`A`, the reduced circuit uses 6 logical qubits, matching the paper's reported optimized qubit count; Qiskit gate counts and transpiled metrics may differ because of decomposition choices.

## Installation

From the repository root:

```powershell
cd qgsa_grover
python -m pip install -e .
```

For direct development without installation:

```powershell
$env:PYTHONPATH='qgsa_grover\src'
```

## Package Layout

```text
qgsa_grover/
  src/qgsa_grover/
    config.py              central DNA encoding tables
    encoding.py            encode/decode helpers
    validation.py          input and search-space validation
    registers.py           Qiskit register layout
    initialization.py      index and basis-state preparation
    cyclic_shift.py        complete-base controlled shifts
    comparator.py          CNOT mismatch computation
    oracle.py              exact-match phase oracle
    diffuser.py            manual Grover diffuser
    grover_iteration.py    iteration composition and counts
    qgsa.py                public builder and search API
    simulator.py           Aer execution helpers
    visualization.py       artifacts, diagrams, histograms
    optique.py             partial supported OPTIQUE reconstruction
  tests/                   pytest validation suite
  examples/                demos and required experiment runner
  outputs/                 generated experiment artifacts
```

## CLI

```powershell
python -m qgsa_grover.cli --target ACGT --pattern A --shots 8192 --iterations paper --encoding-mode paper_2bit --boundary-mode paper_cyclic --output-dir qgsa_grover/outputs/paper_acgt_a --save-circuits
```

```powershell
python -m qgsa_grover.cli --target ACGTA --pattern GTA --shots 8192 --iterations auto --boundary-mode boundary_safe --output-dir qgsa_grover/outputs/acgta_gta --save-circuits
```

## Examples

```powershell
python qgsa_grover/examples/demo_paper_acgt_a.py
python qgsa_grover/examples/demo_all_bases.py
python qgsa_grover/examples/demo_multiple_matches.py
python qgsa_grover/examples/demo_boundary_safe.py
python qgsa_grover/examples/demo_no_match.py
python qgsa_grover/examples/run_required_experiments.py
```

## Tests

```powershell
$env:PYTHONPATH='qgsa_grover\src'
python -m pytest -q qgsa_grover/tests
```

The tests cover input validation, Table 1 encoding, register sizing, complete-base shifts, truth-table agreement, mismatch behavior, oracle phase inversion, uncomputation behavior through statevector comparison, diffuser amplification, all required search cases, seeded simulation reproducibility, output schema, and OPTIQUE reduced-circuit equivalence for the paper example.

## Outputs

Each experiment directory under `qgsa_grover/outputs/` contains JSON result data, statevector or large-circuit fallback analysis, text circuit diagrams, PNG circuit diagrams, QASM where supported, a histogram, and a report. Logical diagrams are saved without forcing full decomposition; transpiled diagrams are saved separately.

For large circuits, PNG rendering is skipped when `num_qubits > 28` or `circuit.size() > 2500`. The skip affects only Matplotlib diagram generation. The runner still saves text diagrams, QASM where Qiskit supports export, result JSON, counts JSON, probabilities JSON, statevector-analysis JSON, reports, and histogram PNGs. A `*.png.skipped.txt` file records the reason and thresholds. For very large transpiled circuits, the runner may store explicit `transpiled_circuit.*.skipped.txt` notes while retaining transpilation metrics in `result.json`.

The repeatable experiment runner is:

```powershell
$env:PYTHONPATH='qgsa_grover\src'
python qgsa_grover/examples/run_required_experiments.py
```

The runner validates existing output directories and reuses complete artifacts. It regenerates missing or inconsistent experiments and writes `qgsa_grover/outputs/required_experiments_summary.json`.

The detailed paper interpretation is in [PAPER_UNDERSTANDING.md](PAPER_UNDERSTANDING.md).

## Simulator And Reproducibility

Shot simulations use `AerSimulator` with a deterministic seed, default `42`. Circuits larger than the local default Aer target limit use `method="matrix_product_state"`. Small circuits also get exact marginal index probabilities from `Statevector`; larger circuits record an explicit statevector-skip warning and use shot probabilities for the large-circuit analysis field.

Qiskit currently emits deprecation warnings for controlled `SwapGate.control()` under Qiskit 2.5.0. The implementation keeps this construction because it is compatible with the installed environment and preserves the explicit complete-base controlled-swap structure.

## Future IBM Quantum Integration

The circuit builders do not depend on Aer. A later portal or hardware workflow can call `build_qgsa_circuit(..., measured=False)` or `build_qgsa_circuit(..., measured=True)` and transpile the returned circuit for an IBM Quantum backend. This package intentionally does not load IBM credentials or submit hardware jobs.

## Limitations

Direct encoding uses target-register qubits proportional to sequence length. Controlled shifts and MCZ gates decompose into many hardware-native operations. State preparation and oracle construction are not free and must be included in realistic resource analysis. Simulator success does not imply practical current-device advantage. Grover's quadratic query advantage assumes a coherent oracle. The paper itself reports that real-hardware results were dominated by noise for the unoptimized QGSA circuit and that resource limits remain a major obstacle.

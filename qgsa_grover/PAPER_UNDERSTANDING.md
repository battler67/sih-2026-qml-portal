# Paper Understanding: Grover/QGSA DNA Exact-Pattern Search

This report records how `Grover_rit.pdf`, "Developing a quantum computing model for sequence annotation of interferon protein", was interpreted for the standalone `qgsa_grover` implementation.

## What The Paper Explicitly Describes

The paper proposes Quantum Gene Sequence Alignment (QGSA) to accelerate the candidate-location search step of BLAST. BLAST is described as a three-stage process: word screening, locating matching sites in the indexed database, and extension around matching sites. QGSA targets the second stage only. It does not implement gapped alignment, local extension, E-value statistics, or biological annotation by itself.

The target sequence is the unknown or unannotated sequence. The pattern sequence is a known sequence or word used to search the target. The target length is denoted by `N`, and the pattern length by `M`.

Table 1 defines the two-bit nucleotide encoding:

```text
A -> 00
C -> 01
G -> 10
T -> 11
```

Section 2.1 states that the encoded target and pattern lengths are `2N` and `2M`. The initial state uses three logical groups of qubits: index qubits, target-string qubits, and pattern-string qubits. Hadamard gates prepare the index register in uniform superposition, while `X` gates prepare computational-basis target and pattern encodings.

The paper's cyclic-shift step uses index qubits as controls and target-string qubits as CSWAP/Fredkin targets. Equation 2 represents the target shifted according to the index. Equation 3 applies CNOT comparison so the pattern register contains `p_j XOR t_{j+r}`. Equation 4 marks a match by flipping phase only when the mismatch/pattern register is all zero. The paper says this phase inversion is implemented with `X` gates and MCZ. Equation 5 gives Grover diffusion as reflection about the uniform index state.

The paper reports a repetition expression written as approximately:

```text
floor(pi / 4 * sqrt(N / M) + 1)
```

It also notes that no more than `sqrt(N)` repetitions are needed in the usual Grover sense.

The paper identifies two boundary problems in the inherited 01-string alignment method: cyclic shift cannot be directly realized when the target-string length is not a power of two, and cyclic wrap-around can produce matches crossing the target boundary. It proposes adding a termination character `$`, encoded as `100`, so the terminator does not match DNA bases and can pad non-power-of-two targets.

Section 2.2 describes OPTIQUE as a truth-table-based circuit optimization. Its goal is to remove target qubits that do not participate in later comparison and reconstruct a smaller circuit. The paper reports that, for `target=ACGT` and `pattern=A`, the logical circuit decreases from 12 qubits and 42 gates to 6 qubits and 22 gates. It also reports virtual and real-hardware experiments, with real-device errors motivating optimization.

## What Was Inferred From Equations And Figures

The index register represents candidate shifts or candidate starting positions. In the paper example `target=ACGT`, `pattern=A`, two measured index bits represent four candidate positions. The reported measurement `00` is therefore index zero, not a direct use of the base code `A -> 00`.

Figure 1 and Table 2 are visually consistent with the underlying 01-string cyclic-shift algorithm, but the surrounding text explicitly warns that one-bit shifts corrupt two-bit DNA encodings. The implementation therefore treats a nucleotide as an indivisible group of bits during cyclic shifts.

The paper's high-level circuit diagram does not emphasize oracle uncomputation, but Grover diffusion must operate on a clean index register. The implementation uses the reversible structure:

```text
U_shift
U_compare
phase flip when mismatch register is all zero
U_compare inverse
U_shift inverse
diffuser on index
```

This is required to avoid leaving target/pattern garbage entangled with index amplitudes before diffusion.

The paper gives `$ -> 100` but does not explicitly define a full three-bit nucleotide table. Boundary-safe mode therefore uses a documented engineering interpretation:

```text
A -> 000
C -> 001
G -> 010
T -> 011
$ -> 100
```

This preserves the Table 1 ordering by zero-prefixing the two-bit DNA codes and reserves `100` for the terminator.

## Engineering Decisions In This Implementation

The package provides two boundary modes:

`paper_cyclic`: reproduces the small cyclic-shift construction and treats every cyclic shift as a candidate. This is the mode used for the paper example.

`boundary_safe`: pads the target to a power-of-two symbol length using `$` and marks only valid linear positions `0..N-M`. Index states outside that range are never marked by the oracle. This prevents false circular matches such as `target=AT`, `pattern=TA`.

The public API reports both the paper iteration formula and the executed iteration count. For deterministic validation experiments, `auto` uses the standard known-solution Grover count `floor(pi/4 * sqrt(S/K))`, where `S` is search-space size and `K` is the number of exact matches found by the classical validator. This validator is not used to construct the main oracle; it is used for testing, no-solution handling, and choosing validation iterations.

When `K=0`, the implementation executes zero Grover iterations, returns `matches_found=false`, and does not choose the largest noisy count as a match.

The simulator uses `AerSimulator` with a fixed seed. Circuits with more than 28 qubits use Aer's `matrix_product_state` method because the local Aer target reports a 28-qubit limit for the default statevector-style target. Exact statevector analysis is skipped for circuits above that practical threshold and the result JSON records that fallback.

Large circuit PNG rendering is skipped when `num_qubits > 28` or `circuit.size() > 2500`. Text diagrams, QASM where supported, JSON reports, and histograms are still saved. The skip is an artifact-generation limit only; it does not change circuit construction or simulation results.

OPTIQUE is implemented only as a supported partial reconstruction: it builds the shifted target prefix directly from an index-controlled truth table and removes unused target qubits. Because the paper refers to supplementary material for the clearest subroutine details, this implementation does not claim a complete exact OPTIQUE reproduction.

## Measurement Interpretation

Qiskit prints classical bitstrings with the highest classical bit on the left. The package measures `idx[i]` into `c_idx[i]`, so a count key such as `01` decodes as integer index 1 in normal binary notation. Reports distinguish measured index bitstrings from nucleotide encodings. For example, measured index `00` means candidate position zero; base encoding `A -> 00` is a separate register-level convention.

## Scalability And Hardware Limits

The direct QGSA encoding uses `O(N + M + log N)` logical qubits before optimization. Controlled shifts and MCZ gates decompose into many hardware-native operations, producing deep circuits. State preparation and oracle construction costs are not free. Grover's quadratic query advantage assumes an efficiently available coherent oracle, which is exactly the hard part for long biological sequences.

The paper's real-hardware experiment shows that NISQ noise can wash out the expected result for the unoptimized circuit. Simulator success in this package should therefore be interpreted as functional circuit validation, not proof of practical quantum advantage or production-scale genome search.

## Future IBM Quantum Use

Circuit construction is simulator-independent. The package exposes unmeasured and measured circuits that can later be transpiled for an IBM Quantum backend. The current project does not require an IBM Quantum API key, does not submit real jobs, and does not include web, database, NCBI, GenBank, authentication, or deployment code.

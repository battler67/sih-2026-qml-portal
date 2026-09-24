# Hybrid Fixed-Point DNA Mismatch Amplification

## Purpose

The Hybrid Fixed-Point mode compares two equal-length DNA strings coherently
inside a Qiskit circuit and amplifies positions where the bases differ.

Its two main design requirements are:

1. Python must not calculate a list of mismatch positions for the oracle.
2. The amplification schedule must not use the actual number of mismatches
   \(M\).

The implementation is in
[`quantum_search_api/services/quantum/hybrid_search.py`](../quantum_search_api/services/quantum/hybrid_search.py).

## Parameters

| Parameter | Meaning | Implementation value |
|---|---|---:|
| \(N\) | Number of DNA positions | Input sequence length |
| \(M\) | Actual number of mismatches | Unknown and unused |
| \(\lambda=M/N\) | Initial marked-state fraction | Unknown |
| \(\lambda_{\min}\) | Assumed lower bound when at least one mismatch exists | \(1/N\) |
| \(\delta\) | Fixed-point failure amplitude | \(0.2\) |
| \(1-\delta^2\) | Guaranteed target success probability | \(0.96\) |
| \(L\) | Odd fixed-point sequence length | Calculated from \(N,\delta\) |
| \(l=(L-1)/2\) | Generalized fixed-point iterations | Calculated |
| Shots | Number of Aer measurements | Portal default: 1024 |
| Maximum \(N\) | Current simulator safety limit | 32 bases |

## Logical-qubit requirement

### Position register

For \(N\) sequence positions, the number of position qubits is

$$
n=\max\left(1,\left\lceil\log_2 N\right\rceil\right).
$$

The `max(1, ...)` term ensures that a one-base input still has a measurable
position register.

### Complete register allocation

| Register | Qubits | Purpose |
|---|---:|---|
| Position | \(n\) | Represents the position \(i\) |
| Reference base | 2 | Stores the reference nucleotide |
| Query base | 2 | Stores the query nucleotide |
| XOR work register | 2 | Stores the two bitwise differences |
| Mismatch flag | 1 | Marks whether the two bases differ |

Therefore, the total number of logical qubits is

$$
\boxed{
Q_{\mathrm{total}}
=
\max\left(1,\left\lceil\log_2 N\right\rceil\right)+7
}.
$$

Examples:

| \(N\) | Position qubits \(n\) | Total logical qubits |
|---:|---:|---:|
| 4 | 2 | 9 |
| 8 | 3 | 10 |
| 16 | 4 | 11 |
| 32 | 5 | 12 |

The \(n\) classical measurement bits are not additional logical qubits.

## DNA base encoding

Each nucleotide is represented using two computational-basis bits:

$$
\mathrm{A}=00,\qquad
\mathrm{C}=01,\qquad
\mathrm{G}=10,\qquad
\mathrm{T}=11.
$$

The reference and query strings are compiled independently into reversible,
position-controlled lookup gates. The preparation unitary \(A\) creates

$$
|s\rangle
=
\frac{1}{\sqrt N}
\sum_{i=0}^{N-1}
|i\rangle_{\mathrm{pos}}
|R_i\rangle_{\mathrm{ref}}
|Q_i\rangle_{\mathrm{query}}
|00\rangle_{\mathrm{xor}}
|0\rangle_{\mathrm{flag}}.
$$

Here, \(R_i\) and \(Q_i\) are the encoded reference and query bases at
position \(i\).

If \(N\) is not a power of two, the position register has capacity
\(2^n>N\), but padded states are assigned zero amplitude:

$$
\Pr(i)=0
\qquad\text{for}\qquad
N\leq i<2^n.
$$

## Coherent mismatch predicate

Let the two-bit reference symbol be \((r_0,r_1)\) and the query symbol be
\((q_0,q_1)\). The circuit first computes

$$
d_0=r_0\oplus q_0,
$$

$$
d_1=r_1\oplus q_1.
$$

The bases differ if either difference bit equals one:

$$
f=d_0\lor d_1.
$$

For reversible gates, the OR is implemented as

$$
\boxed{
f=d_0\oplus d_1\oplus(d_0d_1)
}.
$$

Therefore,

$$
f(i)=
\begin{cases}
1, & R_i\neq Q_i,\\
0, & R_i=Q_i.
\end{cases}
$$

The circuit applies a phase to the computed mismatch flag and then runs the
logic backward:

$$
|d_0d_1\rangle|f\rangle
\longrightarrow
|00\rangle|0\rangle.
$$

This uncomputation prevents the work registers from remaining entangled with
the position register.

Most importantly, the phase oracle receives the two sequences, not a
Python-generated list such as `[1, 6]`.

## Why ordinary Grover amplification is not used

If there are \(M\) marked positions among \(N\) positions, ordinary Grover
amplification uses approximately

$$
r_{\mathrm{Grover}}
\approx
\frac{\pi}{4}\sqrt{\frac{N}{M}}
$$

iterations.

This requires \(M\). When \(M\) is unknown, running too many Grover iterations
can rotate the state past the marked subspace and reduce the success
probability. This is commonly called the Grover over-rotation or
“soufflé” problem.

## Unknown-\(M\) fixed-point schedule

The implemented approach uses the Yoder-Low-Chuang fixed-point schedule.
Although

$$
\lambda=\frac{M}{N}
$$

is unknown, if at least one mismatch exists then

$$
\lambda\geq\lambda_{\min}=\frac{1}{N}.
$$

Thus, the schedule is generated from \(N\) and \(\delta\), without calculating
\(M\).

### Step 1: calculate \(\gamma\)

For each odd candidate sequence length \(L\), calculate

$$
\boxed{
\gamma
=
\frac{1}{
\cosh\left(
\dfrac{\operatorname{arcosh}(1/\delta)}{L}
\right)
}
}.
$$

### Step 2: calculate the guaranteed width

The guaranteed amplification width is

$$
\boxed{
w=1-\gamma^2
}.
$$

### Step 3: select \(L\)

The implementation selects the smallest odd \(L\) satisfying

$$
\boxed{
w\leq\lambda_{\min}=\frac{1}{N}
}.
$$

Only \(N\) and \(\delta\) occur in this selection. The actual mismatch count
\(M\) is not used.

### Iterations and predicate queries

The number of generalized fixed-point iterations is

$$
\boxed{
l=\frac{L-1}{2}
}.
$$

Each generalized iteration computes and uncomputes the mismatch predicate.
Therefore, the predicate-query count is

$$
\boxed{
Q_{\mathrm{predicate}}=2l=L-1
}.
$$

## Fixed-point phase angles

For

$$
j=1,2,\ldots,l,
$$

the source-reflection phases are

$$
\boxed{
\alpha_j
=
2\cot^{-1}
\left[
\tan\left(\frac{2\pi j}{L}\right)
\sqrt{1-\gamma^2}
\right]
}.
$$

The target phases are the reversed negatives:

$$
\boxed{
\beta_j=-\alpha_{l-j+1}
}.
$$

Each generalized iterate is

$$
\boxed{
G(\alpha_j,\beta_j)
=
-S_s(\alpha_j)S_t(\beta_j)
}.
$$

The target phase operator is

$$
S_t(\beta)
=
I-\left(1-e^{i\beta}\right)\Pi_{\mathrm{mismatch}},
$$

where \(\Pi_{\mathrm{mismatch}}\) projects onto the positions whose coherently
computed flag is one.

The phase-shifted reflection about the prepared state is

$$
S_s(\alpha)
=
I-\left(1-e^{-i\alpha}\right)|s\rangle\langle s|.
$$

In circuit order, this source reflection is implemented as

$$
A^\dagger
\;\longrightarrow\;
S_0(-\alpha)
\;\longrightarrow\;
A.
$$

This circuit order realizes the matrix

$$
A\,S_0(-\alpha)\,A^\dagger.
$$

The phase construction follows T. J. Yoder, G. H. Low, and I. L. Chuang,
[“Fixed-point quantum search with an optimal number of
queries”](https://arxiv.org/abs/1409.3305).

## Performed eight-base experiment

The experiment used

$$
R=\mathtt{ACGTACGT},
$$

$$
Q=\mathtt{ATGTACAT}.
$$

### Resource calculation

The sequence length is

$$
N=8.
$$

Therefore,

$$
n=\left\lceil\log_2 8\right\rceil=3
$$

and

$$
\boxed{
Q_{\mathrm{total}}=3+7=10
}.
$$

The schedule used

$$
\lambda_{\min}=\frac{1}{8}=0.125,
$$

$$
\delta=0.2,
$$

$$
L=7,
$$

$$
l=\frac{7-1}{2}=3,
$$

and

$$
Q_{\mathrm{predicate}}=L-1=6.
$$

The resulting phase angles, in radians, were

$$
\boldsymbol{\alpha}
=
(2.386479,\;5.032919,\;3.443879),
$$

$$
\boldsymbol{\beta}
=
(-3.443879,\;-5.032919,\;-2.386479).
$$

The strings happen to contain two mismatches, but this value was not used to
construct the circuit or select \(L\).

### Simulation result

The exact statevector probabilities at the two amplified positions were

$$
P(1)=0.480774,
$$

$$
P(6)=0.480774.
$$

Thus, the total probability in the mismatch subspace was

$$
\boxed{
P_{\mathrm{mismatch}}
=
P(1)+P(6)
=
0.961548
}.
$$

The configured fixed-point lower bound was

$$
1-\delta^2
=
1-(0.2)^2
=
0.96.
$$

Therefore,

$$
P_{\mathrm{mismatch}}=0.961548>0.96.
$$

Each unmarked position had exact probability approximately

$$
P_{\mathrm{unmarked},i}\approx0.006409.
$$

The full result is stored in
[`quantum_search_api/outputs/hybrid_fixed_point/result.json`](../quantum_search_api/outputs/hybrid_fixed_point/result.json).

## Measurement-based candidate selection

Before amplification, every valid position has uniform probability

$$
p_0=\frac{1}{N}.
$$

For \(S\) shots, the estimated standard deviation of a uniform-position count
is

$$
\sigma
=
\sqrt{
\frac{p_0(1-p_0)}{S}
}.
$$

A measured position is reported as a candidate when

$$
\boxed{
\widehat{p}_i
>
\frac{1}{N}
+
3\sqrt{
\frac{(1/N)(1-1/N)}{S}
}
}.
$$

This threshold uses the measured probability, sequence length, and shot count.
It does not compare the two strings classically to decide which positions to
return.

## Complexity and scientific limitations

The logical-qubit requirement grows slowly:

$$
Q_{\mathrm{total}}=O(\log N).
$$

However, the current lookup circuits compile the classical sequence symbols
into position-controlled gates. Their gate count is at least linear in \(N\),
and decomposing multi-controlled gates increases circuit depth:

$$
\text{lookup cost}=O\!\left(N\,\operatorname{poly}(\log N)\right).
$$

The lookup and mismatch operations are repeated by the fixed-point sequence,
so a simplified circuit-cost description is

$$
\text{total gate cost}
=
O\!\left(
L\,N\,\operatorname{poly}(\log N)
\right).
$$

Important boundaries:

- The circuit does not calculate mismatch positions classically.
- The fixed-point schedule does not use the actual \(M\).
- The input strings are still classical and are compiled into reversible
  QROM-style gates.
- Free QRAM is not assumed.
- If \(M=0\), there is no marked state to amplify.
- If \(M=N\), all positions receive the same target phase, so the position
  distribution remains uniform even though every position is a mismatch.
- The experiment demonstrates coherent predicate evaluation and robust
  amplification on a simulator; it does not establish end-to-end quantum
  advantage.

## Generated artifacts

- [Coherent mismatch predicate diagram](../quantum_search_api/outputs/hybrid_fixed_point/coherent_mismatch_predicate.png)
- [Probability chart](../quantum_search_api/outputs/hybrid_fixed_point/position_probabilities.png)
- [Unmeasured QASM circuit](../quantum_search_api/outputs/hybrid_fixed_point/unmeasured.qasm)
- [Measured QASM circuit](../quantum_search_api/outputs/hybrid_fixed_point/measured.qasm)
- [Experiment report](../quantum_search_api/outputs/hybrid_fixed_point/report.txt)
- [Position probabilities CSV](../quantum_search_api/outputs/hybrid_fixed_point/position_probabilities.csv)

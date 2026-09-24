# Quantum DNA Complexity Formulas

## Scope

This document records the high-level gate, space, circuit-depth/time, and query
complexity formulas used to interpret the three Quantum Search modes. These are
asymptotic circuit models, not measured Qiskit Aer or quantum-hardware runtime.

## Symbols

| Symbol                             | Meaning                                                        |
| ---------------------------------- | -------------------------------------------------------------- |
| \(N\)                              | Reference-sequence length                                      |
| \(m\)                              | Query-sequence length                                          |
| \(S=N-m+1\)                        | Valid Grover candidate starting positions                      |
| \(K\)                              | Number of Grover candidate positions containing an exact match |
| \(M\)                              | Number of Hybrid character-by-character mismatches             |
| \(p=\max(1,\lceil\log_2 N\rceil)\) | Position/index-register width                                  |
| \(L\)                              | Odd Yoder-Low-Chuang fixed-point sequence length               |
| \(b\)                              | Bits per encoded DNA symbol                                    |

## FRQI similarity

FRQI requires equal-length reference and query sequences.

### Classical comparison

$$
C_{\mathrm{classical}}=N,
\qquad
C_{\mathrm{classical}}\in\Theta(N).
$$

### Space

The implemented strip circuit contains one strip qubit, \(p\) position qubits,
and one DNA-value qubit:

$$
Q_{\mathrm{FRQI}}=p+2
=\max(1,\lceil\log_2N\rceil)+2.
$$

Therefore:

$$
Q_{\mathrm{FRQI}}\in O(\log N).
$$

### Gate and depth cost

State preparation applies position-controlled rotations for both input
sequences. If decomposing a \(p\)-controlled rotation costs
\(\operatorname{poly}(p)\), then:

$$
G_{\mathrm{load}}
\in O\!\left(N\,\operatorname{poly}(\log N)\right).
$$

The current rotations are applied sequentially, so the high-level depth has the
same loading-dominated upper-bound form:

$$
D_{\mathrm{FRQI}}
\in O\!\left(N\,\operatorname{poly}(\log N)\right).
$$

After the state has been prepared, the final strip-interference comparison is:

$$
Q_{\mathrm{compare}}=1,
\qquad
Q_{\mathrm{compare}}\in O(1).
$$

The \(O(1)\) expression applies only to this final comparison stage. It does
not make FRQI state loading or the complete workflow \(O(1)\).

## Grover DNA search

### Candidate search space

For boundary-safe exact-pattern matching:

$$
S=\max(0,N-m+1).
$$

### Classical work

Checking every candidate character by character gives:

$$
C_{\mathrm{classical}}=S\,m,
\qquad
C_{\mathrm{classical}}\in O(Sm).
$$

The best case is \(\Theta(m)\) when the first candidate matches.

### Query complexity

For \(K>0\) marked candidate positions:

$$
Q_{\mathrm{Grover}}
=
\left\lceil
\frac{\pi}{4}\sqrt{\frac{S}{K}}
\right\rceil,
\qquad
Q_{\mathrm{Grover}}\in O\!\left(\sqrt{\frac{S}{K}}\right).
$$

When every candidate is marked, \(K=S\), the best-case query complexity is:

$$
Q_{\mathrm{Grover}}\in O(1).
$$

No successful-search query count is fabricated when \(K=0\).

### Space

The current QGSA circuit allocates an index register, encoded target register,
and encoded pattern register:

$$
Q_{\mathrm{Grover}}^{\mathrm{space}}
=p+bT+bm,
$$

where \(T\) is the target-register symbol capacity.

For the default boundary-safe mode:

$$
T=2^{\lceil\log_2N\rceil},
\qquad b=3,
$$

so:

$$
Q_{\mathrm{boundary\ safe}}
=p+3T+3m.
$$

For the paper-style cyclic mode:

$$
T=N,\qquad b=2,
$$

so:

$$
Q_{\mathrm{paper\ cyclic}}
=p+2N+2m.
$$

### Gate and depth cost

Let \(G*{\mathrm{init}}\), \(G*{\mathrm{oracle}}\), and
\(G\_{\mathrm{diffuser}}\) be the decomposed gate counts of the corresponding
circuit stages. Then:

$$
G_{\mathrm{Grover}}
=
G_{\mathrm{init}}
+
Q_{\mathrm{Grover}}
\left(
G_{\mathrm{oracle}}+G_{\mathrm{diffuser}}
\right).
$$

Similarly, for circuit depth:

$$
D_{\mathrm{Grover}}
\lesssim
D_{\mathrm{init}}
+
Q_{\mathrm{Grover}}
\left(
D_{\mathrm{oracle}}+D_{\mathrm{diffuser}}
\right).
$$

The pattern-comparison and oracle-construction work is not hidden inside the
square-root query count.

## Hybrid YLC mutation search

Hybrid Mutation requires equal lengths:

$$
N=m.
$$

It treats every unequal character as one substitution with equal weight.

### Classical comparison

$$
C_{\mathrm{classical}}=N,
\qquad
C_{\mathrm{classical}}\in\Theta(N).
$$

### Ideal known-\(M\) query reference

For \(M>0\):

$$
Q_{\mathrm{ideal}}
=
\left\lceil
\frac{\pi}{4}\sqrt{\frac{N}{M}}
\right\rceil,
\qquad
Q_{\mathrm{ideal}}\in O\!\left(\sqrt{\frac{N}{M}}\right).
$$

This is a theoretical known-\(M\) reference. The implemented fixed-point
schedule does not use the actual mismatch count \(M\).

### Implemented unknown-\(M\) schedule

The implemented YLC schedule uses:

$$
\lambda_{\min}=\frac{1}{N},
\qquad
\delta=0.2.
$$

For an odd sequence length \(L\):

$$
\gamma(L)
=
\frac{1}{
\cosh\!\left(
\operatorname{acosh}(1/\delta)/L
\right)
},
$$

$$
w(L)=1-\gamma(L)^2.
$$

The implementation selects the smallest odd \(L\) satisfying:

$$
w(L)\leq\frac{1}{N}.
$$

The number of generalized YLC iterations and predicate queries are:

$$
l=\frac{L-1}{2},
\qquad
Q_{\mathrm{YLC}}=2l=L-1.
$$

### Space

The current circuit uses \(p\) position qubits and seven work/data qubits:

$$
Q_{\mathrm{Hybrid}}
=p+7
=\max(1,\lceil\log_2N\rceil)+7.
$$

Therefore:

$$
Q_{\mathrm{Hybrid}}\in O(\log N).
$$

### Gate and depth cost

The classical sequences are compiled into reversible QROM-style loading gates.
The preparation and inverse preparation are repeated by the fixed-point
sequence:

$$
G_{\mathrm{Hybrid}}
\in
O\!\left(
L\,N\,\operatorname{poly}(\log N)
\right).
$$

For the current sequential construction, circuit depth is likewise
loading-dominated:

$$
D_{\mathrm{Hybrid}}
\in
O\!\left(
L\,N\,\operatorname{poly}(\log N)
\right).
$$

## Projected circuit time

If a future estimate uses decomposed gate counts \(g_i\) and explicitly
configured gate-duration assumptions \(t_i\), the transparent projection is:

$$
T_{\mathrm{projected}}=\sum_i g_i t_i.
$$

If one uniform duration \(t_g\) is assumed:

$$
T_{\mathrm{projected}}=G_{\mathrm{decomposed}}t_g.
$$

This must be labelled **projected**, not measured. Qiskit Aer wall-clock time is
classical simulation time and is not evidence of quantum-hardware speedup.

## Interpretation limits

- The formulas compare theoretical operations or oracle/predicate queries, not
  equivalent measured wall-clock units.
- DNA loading and oracle construction may require at least \(O(N)\) work.
- Reporting all \(K\) matches or \(M\) mutation positions adds sampling and
  output cost.
- Native-gate decomposition, routing, queueing, reset, readout, noise,
  mitigation, and error correction can add substantial overhead.
- The square-root formulas describe query complexity inside a search circuit,
  not a proven end-to-end speedup.

# Classical vs Quantum Scaling

## Purpose

The Quantum Search form shows a theoretical scaling comparison for FRQI,
Grover, and Hybrid Mutation. It does not use Qiskit simulator wall-clock time
as evidence of quantum speedup.

The four reactive controls are:

1. Algorithm: FRQI, Grover, or Hybrid.
2. Reference length `N`.
3. Query length `m`.
4. Marked count: mutations `M` for Hybrid, exact matches `K` for Grover, or
   input differences `K` for the FRQI illustration.

Hybrid requires `N = m`. Valid pasted sequences initialize their lengths and
exact substitution count. Grover initializes its marked count from a pasted
reference when available. All values remain editable for theoretical study.

The portal displays only operation/query complexity cards and the comparison
graph. It does not display projected timing or the detailed limitation panels;
the scientific boundaries remain documented below.

## Flexible formula design

All formula functions and timing assumptions are exported from
`src/lib/scaling-formulas.ts`.

The complete gate, space, depth/time, and query-complexity derivations for all
three modes are recorded in
[`QUANTUM_COMPLEXITY_FORMULAS.md`](QUANTUM_COMPLEXITY_FORMULAS.md).

- `DEFAULT_SCALING_FORMULAS` contains replaceable functions.
- `DEFAULT_SCALING_ASSUMPTIONS` contains replaceable timing/model constants.
- `calculateScalingComparison()` accepts alternative formula and assumption
  objects.
- UI components render the returned model and contain no independent scaling
  equations.

This separation allows later equation changes without rewriting the cards or
chart.

## FRQI formulas

For two equal-length encoded sequences:

```text
C_classical = N
```

The chart presents the prepared-state strip comparison as:

```text
Q_comparison = 1
```

Therefore the comparison stage is displayed as `O(1)` after state preparation,
while the classical character scan is `Theta(N)`. This does not make FRQI an
end-to-end `O(1)` workflow: the encoded sequence states must already exist.

## Hybrid formulas

For equal sequence length `N` and `M` substitution positions:

### Classical direct comparison

```text
C_classical = N
T_classical_projected = C_classical * t_comparison
```

The default comparison-duration assumption is `1 ns`. This is an illustrative
configuration value, not a benchmark.

### Ideal known-M query reference

For `M > 0`:

```text
Q_ideal = ceil((pi / 4) * sqrt(N / M))
```

This is only an ideal amplitude-amplification reference. The implemented Hybrid
circuit does not use the actual mismatch count to choose its schedule.

### Implemented unknown-M fixed-point schedule

The backend uses:

```text
lambda_min = 1 / N
delta = 0.2
```

For odd schedule length `L`:

```text
gamma(L) = 1 / cosh(acosh(1 / delta) / L)
width(L) = 1 - gamma(L)^2
```

The smallest odd `L` satisfying:

```text
width(L) <= 1 / N
```

is selected, and:

```text
Q_YLC = L - 1
```

The displayed search-stage gate model uses:

```text
g_predicate = 15 high-level gates/query
G_projected = Q_YLC * g_predicate
T_quantum_projected = G_projected * t_g
```

The replaceable value `15` represents seven mismatch-compute gates, one phase
gate, and seven uncompute gates. It is not a transpiled device gate count.

## Grover formulas

For reference length `N`, query length `m`, and `K` exact matching candidate
positions:

### Candidate positions

```text
S = max(0, N - m + 1)
```

### Classical direct baseline

```text
C_classical_exhaustive = S * m
```

The direct-search best case is `Theta(m)` when the first candidate matches.

### Grover query count

For `K > 0`:

```text
Q_Grover = ceil((pi / 4) * sqrt(S / K))
```

Therefore:

```text
Q_Grover is O(sqrt(S / K)) oracle queries
```

When every candidate is marked (`K = S`), the displayed best case is `O(1)`
oracle queries. Work required to check the `m`-base pattern inside the oracle is
shown separately and is not hidden inside the square root.

The replaceable high-level gate model is:

```text
index_qubits = max(1, ceil(log2(S)))
g_query = m + 2 * index_qubits
G_projected = Q_Grover * g_query
T_quantum_projected = G_projected * t_g
```

This is a unit-cost search-stage projection, not an actual QGSA transpiled gate
count.

## Interpretation and limitations

- Projected timing formulas remain available in the replaceable formula module
  for future use, but are not rendered in the portal.
- Qiskit Aer wall-clock execution is classical simulation time and is not used
  to claim quantum speedup.
- DNA loading and oracle construction may require `O(N)` work.
- Reporting all `M` mutation positions introduces additional sampling and
  output cost.
- State preparation, routing, queueing, readout, reset, noise, mitigation, and
  error-correction overhead are excluded from the search-stage projection.
- The chart presents theoretical query complexity inside the search circuit,
  not a proven end-to-end wall-clock advantage.
- `M=0` or `K=0` does not fabricate a Grover hardware-time projection.

## Changed files

- `specs/classical_quantum_scaling.md`: branch plan, formula contract, and task
  log.
- `src/lib/scaling-formulas.ts`: replaceable formulas, assumptions, validation,
  projections, and chart data.
- `src/lib/scaling-formulas.test.ts`: Hybrid and Grover tests across different
  `N`, `m`, and marked-count values.
- `src/components/ScalingComparisonCard.tsx`: reusable metric/formula card.
- `src/components/ScalingComparisonChart.tsx`: reusable responsive complexity
  chart.
- `src/components/ClassicalQuantumScaling.tsx`: four-field three-mode selector,
  mode-specific complexity cards, and graph integration.
- `src/components/QuantumSearch.tsx`: initial values from current sequences and
  bottom-of-page Hybrid/Grover integration.
- `docs/CLASSICAL_QUANTUM_SCALING.md`: formulas and changed-file inventory.
- `docs/QUANTUM_COMPLEXITY_FORMULAS.md`: gate, space, depth/time, and query
  formulas for FRQI, Grover, and Hybrid YLC.
- `docs/QUANTUM_SEARCH.md`: documentation link.
- `README.md`: feature documentation link.

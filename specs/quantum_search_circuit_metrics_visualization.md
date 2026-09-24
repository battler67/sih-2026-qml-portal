# Quantum search circuit-metrics visualization

Date: 2026-07-30

## Goal

Show the circuit metrics already returned with a completed local quantum search
as a visualization on `/quantum-search-results`.

## Branch

- `feature/real-hardware-routing`

## Design

- Read `circuitMetrics` and `transpiledCircuitMetrics` from the top-ranked
  processed window's `quantumDetails`.
- Compare logical and Aer-transpiled values for circuit depth, total
  operations, one-qubit gates, and two-qubit gates.
- Show logical and transpiled qubit counts alongside the chart.
- Reuse the existing visualization card, chart library, colours, typography,
  and responsive layout.
- Label these as metrics for the representative top-ranked bounded window.
  They are not totals across every processed window and are not physical
  hardware metrics.
- If an older result does not contain circuit metrics, show an explanatory
  empty state rather than inventing values.

## Verification

- Format the changed component.
- Run targeted ESLint for `QuantumSearch.tsx`.
- Run the production frontend build.

## Implementation log

- Added a grouped logical-versus-Aer-transpiled bar chart to the existing
  results visualization grid.
- Included depth, total operations, one-qubit gate count, and two-qubit gate
  count.
- Included logical and transpiled qubit counts in the visualization
  description.
- Added a safe empty state for older result payloads without circuit metrics.
- `bunx prettier --write`: passed.
- Targeted `bunx eslint src/components/QuantumSearch.tsx`: passed.
- Production `bun run build`: passed.

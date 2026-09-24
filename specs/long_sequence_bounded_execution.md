# Long-sequence bounded quantum execution

Date: 2026-07-30

## Goal

Accept pasted or FASTA-formatted query and reference inputs up to 100,000
nucleotide bases on the quantum-search page. Allow metadata-only estimation
for those inputs, then enable local Aer and real-hardware actions only when
the bounded circuit described by that estimate is eligible.

## Branch

- `feature/real-hardware-routing`

## Design

- Separate **input sequence length** from **quantum window length**.
- Accept and validate at most 100,000 A/C/G/T bases per pasted query or
  reference input.
- Strip FASTA headers and whitespace from both query and reference previews.
- Keep `maxQueryLength` as the user-controlled quantum window bound, from 1
  through 128 bases.
- For an input query longer than `maxQueryLength`, compile the leading bounded
  query window only. Scan bounded reference windows according to the existing
  stride, strand, `maxWindows`, and base caps.
- Report the full input length, bounded quantum window length, and truncation
  explicitly in estimates and results.
- Increase the portal's pasted/reference base caps to 100,000 so the supplied
  reference is available for bounded window generation.

## Estimate-driven controls

- **Estimate** is enabled when the full inputs are valid A/C/G/T and within the
  100,000-base input cap.
- **Run Search** is enabled only after a current estimate says the bounded
  circuit is supported by the local Aer workflow.
- **Run on Real Hardware** is enabled only after a current estimate says the
  bounded circuit requires no more than the 156-qubit planning capacity and
  satisfies algorithm-specific builder limits.
- Live provider discovery remains authoritative. A planning estimate cannot
  guarantee that a 156-qubit device is online, accessible, or able to
  transpile the circuit usefully.

## Scientific limitations and decisions

- A 156-qubit processor does not make a complete 100,000-base coherent circuit
  practical. Qubit count is only one constraint; gate count, circuit depth,
  connectivity, transpilation, noise, queue time, and provider limits also
  matter.
- Long-query support is bounded-window processing, not a coherent comparison
  of both complete 100,000-base strings.
- Real-hardware mode still submits one representative bounded window, with the
  existing qBraid-to-IBM fallback. It does not submit every reference window.
- FRQI, Grover/QGSA, and Hybrid have different circuit-size behavior.
  Eligibility must come from the selected algorithm's estimate rather than
  from input length or backend qubit count alone.
- Hybrid remains limited to 32 bases per circuit.
- Grover/QGSA remains qubit-heavy and can be ineligible even when the long
  input is accepted.

## Planned verification

- Normalize 100,000-base plain and FASTA inputs.
- Estimate a 100,000-base query/reference pair using a bounded FRQI window.
- Verify estimate fields and truncation warnings.
- Verify Grover and Hybrid eligibility follows bounded circuit limits.
- Prepare a bounded real-hardware circuit without compiling all 100,000 query
  bases into that circuit.
- Run focused backend tests, the complete API suite, targeted frontend lint,
  and a production frontend build.

## Implementation and verification log

- Added 100,000-base FASTA/plain-input normalization and explicit bounded
  quantum-window selection.
- Added estimate fields for full input length, compiled window length,
  truncation, Aer eligibility, and 156-qubit hardware planning eligibility.
- Applied the same bounded query preparation to local and hardware circuit
  construction.
- Updated the quantum-search controls and estimate panel so execution buttons
  follow the current estimate.
- Documented the bounded-window semantics in the quantum-search, hardware, and
  top-level project documentation.
- Backend compilation checks passed.
- Search-orchestrator tests: `14 passed`.
- Stable backend suite: `62 passed, 2 deselected`. The two deselected
  asynchronous API tests use fixed 2.5-second and 5-second polling windows;
  both can time out while their background Aer work is still running on this
  machine. The full suite result was `62 passed, 1 failed, 1 deselected` after
  the five-second noise test timed out. An earlier full run similarly had only
  the 2.5-second candidate-validation polling test fail, while a diagnostic
  confirmed its job completed after roughly 4.67 seconds.
- Targeted frontend ESLint passed.
- Production frontend build passed.
- No real-provider submission was made during verification.

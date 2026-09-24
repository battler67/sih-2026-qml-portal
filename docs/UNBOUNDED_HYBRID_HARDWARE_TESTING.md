# Unbounded Hybrid Hardware Testing

## Branch-only behavior

The experimental branch
`feature/unbounded-hybrid-hardware-testing` removes the fixed 32-base Hybrid
Mutation guard. It is intentionally not merged into `main`.

For Hybrid mode, the complete pasted query and equal-length pasted reference
are used for:

- resource estimation;
- coherent Hybrid circuit construction;
- local Aer execution requests;
- real-hardware circuit preparation and provider discovery.

The `maxQueryLength` window setting does not truncate Hybrid inputs.

## Validation that remains

- Inputs must be non-empty A/C/G/T strings.
- Query and reference lengths must match.
- The portal's general input cap still applies.
- Local simulator eligibility uses its logical-qubit planning capacity.
- Real-hardware execution still requires explicit confirmation.
- Live provider access, device capacity, topology, ISA transpilation, queue,
  quotas, and provider errors remain authoritative.

## Important execution warning

Logical-qubit fit is not a practical execution guarantee. The current Hybrid
implementation compiles both classical strings into reversible QROM-style
gates and repeats preparation and inverse preparation in the YLC sequence:

$$
G_{\mathrm{Hybrid}}
\in
O\!\left(LN\,\operatorname{poly}(\log N)\right).
$$

Increasing the sequence length can make circuit construction, transpilation,
local simulation, or hardware execution extremely expensive even while the
logical-qubit count remains below a device's capacity. Start with a previously
verified small input, inspect the backend-transpiled depth and two-qubit gate
count, and increase length gradually.

A completed hardware job demonstrates physical-device execution. It does not
by itself establish end-to-end quantum advantage.

## Standalone direct IBM submission

`quantum_search_api/examples/submit_100k_hybrid_to_ibm.py` is a standalone
experiment. It does not call the portal hardware API, `HardwareJobService`, or
the portal's provider-selection feature. It:

1. loads `quantum_search_api/.env`;
2. validates the reference and mutated FASTA files;
3. builds the complete Hybrid YLC circuit;
4. connects directly through `QiskitRuntimeService`;
5. transpiles for the requested IBM backend;
6. submits with `SamplerV2`;
7. waits for raw results and writes a recovery/result JSON file.

Install the declared dependencies, then run from the repository root:

```powershell
python -m pip install -r quantum_search_api/requirements.txt
python -m quantum_search_api.examples.submit_100k_hybrid_to_ibm --backend ibm_marrakesh --yes
```

Omit `--yes` to require typing `SUBMIT` before circuit construction and
external submission. The remote job ID and submission metadata are written as
soon as IBM accepts the job, before the script begins waiting.

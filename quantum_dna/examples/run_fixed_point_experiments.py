"""Generate the complete coherent fixed-point experiment artifact set."""

from __future__ import annotations

import json
from pathlib import Path

from quantum_dna import analyze_fixed_point_sequences


# These positions are disclosed verification fixtures. They score completed
# circuits but are never passed to circuit or schedule construction.
CASES = {
    "no_mismatch": ("AAAA", "AAAA", []),
    "single_mismatch": ("AAAA", "AAAT", [3]),
    "multiple_mismatches": ("ACGT", "ATGA", [1, 3]),
    "non_power_of_two": ("ACGTA", "ATGTT", [1, 4]),
    "all_mismatch": ("AAAA", "TTTT", [0, 1, 2, 3]),
}


def main() -> None:
    root = Path("quantum_dna/outputs/fixed_point_hybrid")
    root.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, (reference, query, truth) in CASES.items():
        result = analyze_fixed_point_sequences(
            reference,
            query,
            verification_positions=truth,
            shots=8192,
            seed=12345,
            delta=0.2,
            save_circuits=True,
            output_dir=root / name,
        )
        summary[name] = {
            "reference": reference,
            "query": query,
            "verification_positions_zero_based": truth,
            "measurement_inferred_positions_zero_based": (
                result.measurement_inferred_positions_zero_based
            ),
            "rounds": result.fixed_point_rounds,
            "exact_verified_target_probability": (
                result.exact_verified_target_probability
            ),
            "shot_verified_target_probability": (
                result.shot_verified_target_probability
            ),
            "guarantee_applicable": result.guarantee_applicable,
            "guarantee_satisfied_exactly": (
                result.guarantee_satisfied_exactly
            ),
            "clean_work_probability": result.clean_work_probability,
            "invalid_padded_probability_exact": (
                result.invalid_padded_probability_exact
            ),
            "logical_metrics": result.circuit_metrics.__dict__,
            "transpiled_metrics": result.transpiled_metrics.__dict__,
            "artifact_count": len(result.artifact_paths),
        }

    summary_path = root / "experiments_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

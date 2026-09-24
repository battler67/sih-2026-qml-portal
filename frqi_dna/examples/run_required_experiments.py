from __future__ import annotations

import json
from pathlib import Path

from frqi_dna.src.analysis import compare_dna_frqi


EXPERIMENTS = [
    ("identical_aaaa", "AAAA", "AAAA"),
    ("different_aaaa_tttt", "AAAA", "TTTT"),
    ("one_difference_aaat", "AAAA", "AAAT"),
    ("mixed_identical_acgt", "ACGT", "ACGT"),
    ("mixed_substitution_actt", "ACGT", "ACTT"),
    ("eight_base_accttcgt", "ACGTACGT", "ACCTTCGT"),
]


def main() -> int:
    output_root = Path("frqi_dna/outputs")
    summary = []
    for name, reference, query in EXPERIMENTS:
        result = compare_dna_frqi(
            reference=reference,
            query=query,
            shots=8000,
            seed=12345,
            output_dir=output_root / name,
            save_circuits=True,
        )
        summary.append(result.to_dict())
        print(
            f"{name}: P1={result.p1:.6f}, theoretical_P1={result.theoretical_p1:.6f}, "
            f"similarity={result.similarity:.6f}, theoretical_similarity={result.theoretical_similarity:.6f}"
        )

    summary_path = output_root / "required_experiments_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

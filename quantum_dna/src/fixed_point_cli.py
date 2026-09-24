"""CLI for coherent unknown-M fixed-point DNA mismatch amplification."""

from __future__ import annotations

import argparse
import json
import logging

from .fixed_point_analysis import analyze_fixed_point_sequences


def _positions(value: str) -> list[int]:
    if not value.strip():
        return []
    try:
        return [int(item.strip()) for item in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "verification positions must be comma-separated integers"
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Coherent DNA mismatch oracle plus unknown-M fixed-point "
            "amplitude amplification"
        )
    )
    parser.add_argument("--reference", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument(
        "--verification-positions",
        type=_positions,
        default=[],
        help=(
            "comma-separated zero-based truth used only to score the completed "
            "experiment; never used to construct the circuit"
        ),
    )
    parser.add_argument("--shots", type=int, default=8192)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--delta", type=float, default=0.2)
    parser.add_argument(
        "--lambda-min",
        type=float,
        default=None,
        help="promised lower bound; defaults to 1/N and never uses actual M",
    )
    parser.add_argument("--save-circuits", action="store_true")
    parser.add_argument(
        "--output-dir",
        default="quantum_dna/outputs/fixed_point_hybrid/cli_demo",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    result = analyze_fixed_point_sequences(
        args.reference,
        args.query,
        verification_positions=args.verification_positions,
        shots=args.shots,
        seed=args.seed,
        delta=args.delta,
        lambda_min=args.lambda_min,
        save_circuits=args.save_circuits,
        output_dir=args.output_dir,
    )
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()

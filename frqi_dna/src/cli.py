"""Command-line entry point for FRQI DNA comparison."""

from __future__ import annotations

import argparse
from pathlib import Path

from .analysis import compare_dna_frqi
from .config import DEFAULT_ANGLE_MODE, DEFAULT_SEED, DEFAULT_SHOTS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FRQI DNA sequence comparison")
    parser.add_argument("--reference", required=True, help="reference DNA sequence")
    parser.add_argument("--query", required=True, help="query DNA sequence")
    parser.add_argument("--shots", type=int, default=DEFAULT_SHOTS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--angle-mode", default=DEFAULT_ANGLE_MODE)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--save-circuits", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = compare_dna_frqi(
        reference=args.reference,
        query=args.query,
        shots=args.shots,
        seed=args.seed,
        angle_mode=args.angle_mode,
        output_dir=args.output_dir,
        save_circuits=args.save_circuits,
    )

    print(f"Reference: {result.reference}")
    print(f"Query: {result.query}")
    print(f"P(0): {result.p0:.6f}")
    print(f"P(1): {result.p1:.6f}")
    print(f"Similarity: {result.similarity:.6f}")
    print(f"Similarity percentage: {result.similarity_percentage:.3f}%")
    print(f"Theoretical P(1): {result.theoretical_p1:.6f}")
    print(f"Theoretical similarity: {result.theoretical_similarity:.6f}")
    print(f"Circuit depth: {result.circuit_metrics.depth}")
    print(f"Gate count: {result.circuit_metrics.size}")
    if result.output_paths:
        print("Output paths:")
        for key, value in sorted(result.output_paths.items()):
            print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

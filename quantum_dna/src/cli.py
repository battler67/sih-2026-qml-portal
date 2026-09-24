"""Command-line interface for the standalone simulator."""

from __future__ import annotations

import argparse
import json
import logging

from .analysis import analyze_sequences


def main() -> None:
    parser = argparse.ArgumentParser(description="FRQI–Grover DNA mutation localization")
    parser.add_argument("--reference", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--shots", type=int, default=8192)
    parser.add_argument("--backend", choices=["aer", "aer_simulator"], default="aer")
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--save-circuits", action="store_true")
    parser.add_argument("--output-dir", default="quantum_dna/outputs/demo")
    args = parser.parse_args()
    # Keep third-party transpiler internals quiet; the JSON result is the CLI's
    # intentional user-facing output.
    logging.basicConfig(level=logging.WARNING)
    result = analyze_sequences(
        args.reference, args.query, args.shots, args.backend,
        seed=args.seed, save_circuits=args.save_circuits, output_dir=args.output_dir,
    )
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()

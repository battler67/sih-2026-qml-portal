"""Command-line interface for QGSA."""

from __future__ import annotations

import argparse

from .encoding import encode_sequence
from .qgsa import search_dna_qgsa


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Grover/QGSA DNA exact-pattern search")
    parser.add_argument("--target", required=True)
    parser.add_argument("--pattern", required=True)
    parser.add_argument("--shots", type=int, default=8192)
    parser.add_argument("--iterations", default="auto")
    parser.add_argument("--encoding-mode", default="paper_2bit")
    parser.add_argument("--boundary-mode", choices=["paper_cyclic", "boundary_safe"], default="paper_cyclic")
    parser.add_argument("--output-dir", default="outputs/qgsa_run")
    parser.add_argument("--save-circuits", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--optimize", action="store_true")
    return parser


def _parse_iterations(value: str):
    try:
        return int(value)
    except ValueError:
        return value


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    result = search_dna_qgsa(
        target=args.target,
        pattern=args.pattern,
        shots=args.shots,
        iterations=_parse_iterations(args.iterations),
        encoding_mode=args.encoding_mode,
        boundary_mode=args.boundary_mode,
        output_dir=args.output_dir,
        save_circuits=args.save_circuits,
        seed=args.seed,
        optimize=args.optimize,
    )
    encoding_mode = "terminator_3bit" if "$" in result.encoding.values() else args.encoding_mode
    print(f"target: {result.target}")
    print(f"pattern: {result.pattern}")
    print(f"target_length: {result.target_length}")
    print(f"pattern_length: {result.pattern_length}")
    print(f"encoded_target: {''.join(map(str, encode_sequence(result.target, 'paper_2bit')))}")
    print(f"encoded_pattern: {''.join(map(str, encode_sequence(result.pattern, 'paper_2bit')))}")
    print(f"valid_candidate_positions: {result.valid_position_count}")
    print(f"index_qubits: {result.index_qubits}")
    print(f"grover_iterations: {result.iterations_executed}")
    print(f"paper_iteration_formula_value: {result.paper_iteration_formula_value}")
    print(f"classical_expected_positions: {result.classical_match_positions}")
    print(f"decoded_quantum_candidates: {result.quantum_candidate_positions}")
    print(f"measurement_probabilities: {result.index_probabilities}")
    print(f"success_probability: {result.success_probability:.6f}")
    print(f"logical_qubits: {result.circuit_metrics['logical_qubits']}")
    print(f"circuit_depth: {result.circuit_metrics['depth']}")
    print(f"gate_count: {result.circuit_metrics['size']}")
    print(f"transpiled_depth: {result.transpiled_metrics['depth']}")
    print(f"output_paths: {result.output_paths}")
    print(f"warnings: {result.warnings}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

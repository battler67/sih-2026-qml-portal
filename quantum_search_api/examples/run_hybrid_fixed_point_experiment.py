"""Generate reproducible unknown-M hybrid mismatch experiment artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
from qiskit import qasm2, transpile

from quantum_search_api.services.quantum.base import QuantumRunOptions
from quantum_search_api.services.quantum.hybrid_search import (
    HybridQuantumSearchEngine,
    build_hybrid_fixed_point_circuits,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", default="ACGTACGT")
    parser.add_argument("--query", default="ATGTACAT")
    parser.add_argument("--shots", type=int, default=8192)
    parser.add_argument(
        "--output-dir",
        default="quantum_search_api/outputs/hybrid_fixed_point",
    )
    args = parser.parse_args()

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    circuits = build_hybrid_fixed_point_circuits(args.reference, args.query)
    result = HybridQuantumSearchEngine().run(
        args.query,
        args.reference,
        QuantumRunOptions(shots=args.shots, enable_classical_validation=False),
    )

    for name in ("preparation", "predicate", "unmeasured", "measured"):
        circuit = circuits[name]
        (output / f"{name}.txt").write_text(str(circuit.draw(output="text")), encoding="utf-8")
        lowered = transpile(
            circuit,
            basis_gates=["u1", "u2", "u3", "cx"],
            optimization_level=0,
            seed_transpiler=12345,
        )
        (output / f"{name}.qasm").write_text(qasm2.dumps(lowered), encoding="utf-8")

    circuits["predicate"].draw(
        output="mpl",
        filename=str(output / "coherent_mismatch_predicate.png"),
        fold=-1,
    )
    positions = [int(index) for index in result["exactIndexProbabilities"]]
    exact = [result["exactIndexProbabilities"][str(index)] for index in positions]
    sampled = [result["indexProbabilities"][str(index)] for index in positions]
    figure, axis = plt.subplots(figsize=(9, 4.5))
    axis.bar([index - 0.18 for index in positions], exact, 0.36, label="Exact statevector")
    axis.bar([index + 0.18 for index in positions], sampled, 0.36, label="Aer shots")
    axis.axhline(1 / len(positions), color="black", linestyle="--", label="Uniform baseline")
    axis.set(
        xlabel="Position (zero-based)",
        ylabel="Probability",
        title="Unknown-M fixed-point mismatch localization",
        xticks=positions,
    )
    axis.legend()
    figure.tight_layout()
    figure.savefig(output / "position_probabilities.png", dpi=180)
    plt.close(figure)

    (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    with (output / "position_probabilities.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["position_zero_based", "shot_probability", "exact_probability"])
        for index, probability in result["indexProbabilities"].items():
            writer.writerow([index, probability, result["exactIndexProbabilities"][index]])

    report = [
        "Hybrid fixed-point coherent mismatch experiment",
        f"Reference: {args.reference}",
        f"Query:     {args.query}",
        f"Shots: {args.shots}",
        f"YLC L: {result['fixedPointSequenceLength']}",
        f"Generalized iterations: {result['iterationsExecuted']}",
        f"Predicate queries: {result['predicateQueries']}",
        f"lambda_min: {result['lambdaLowerBound']}",
        f"delta: {result['fixedPointDelta']}",
        f"Measured candidates (zero-based): {result['measuredCandidateIndices']}",
        f"Exact position probabilities: {json.dumps(result['exactIndexProbabilities'], sort_keys=True)}",
        "",
        "No mismatch positions or actual M were calculated to build this circuit.",
        "The supplied classical sequences were compiled independently into reversible lookup gates.",
    ]
    (output / "report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"outputDir": str(output), **result}, indent=2))


if __name__ == "__main__":
    main()

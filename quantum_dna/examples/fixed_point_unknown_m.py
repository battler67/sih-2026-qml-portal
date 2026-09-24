"""One unknown-M coherent mismatch experiment."""

from quantum_dna.src.fixed_point_hybrid import run_fixed_point_experiment


def main() -> None:
    result = run_fixed_point_experiment(
        "ACGT",
        "ATGA",
        expected_positions=[1, 3],
        delta=0.2,
    )
    print(
        "circuit: "
        f"{result.circuit.num_qubits} qubits, "
        f"depth {result.circuit.depth()}, "
        f"{result.circuit.size()} operations"
    )
    print(f"operation counts: {dict(result.circuit.count_ops())}")
    print(f"fixed-point rounds: {len(result.phases)}")
    print(f"position probabilities: {result.position_probabilities}")
    print(f"mismatch success probability: {result.success_probability:.12f}")
    print(f"clean-work probability: {result.clean_work_probability:.12f}")
    print(
        "guaranteed success for any nonzero M: "
        f"{result.guaranteed_success_probability:.12f}"
    )


if __name__ == "__main__":
    main()

from __future__ import annotations


def gate_count_groups(operation_counts: dict[str, int]) -> dict[str, int]:
    one_qubit = {"x", "h", "ry", "rz", "rx", "s", "sdg", "t", "tdg", "measure", "barrier"}
    two_qubit = {"cx", "cz", "swap"}
    return {
        "oneQubitGateCount": sum(count for gate, count in operation_counts.items() if gate.lower() in one_qubit),
        "twoQubitGateCount": sum(count for gate, count in operation_counts.items() if gate.lower() in two_qubit),
    }

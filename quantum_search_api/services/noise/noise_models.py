from __future__ import annotations

from collections import Counter
from typing import Any

from qiskit import QuantumCircuit
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error


FRQI_SINGLE_QUBIT_ERROR = 0.002
FRQI_TWO_QUBIT_ERROR = 0.01
GROVER_SINGLE_QUBIT_ERROR = 0.001
GROVER_TWO_QUBIT_ERROR = 0.015
YLC_ZERO_TO_ONE_ERROR = 0.03
YLC_ONE_TO_ZERO_ERROR = 0.04
GROVER_MAX_NOISY_GATE_OCCURRENCES = 4
YLC_READOUT_MATRIX = (
    (1.0 - YLC_ZERO_TO_ONE_ERROR, YLC_ZERO_TO_ONE_ERROR),
    (YLC_ONE_TO_ZERO_ERROR, 1.0 - YLC_ONE_TO_ZERO_ERROR),
)


def build_frqi_noise_model(
    single_qubit_error: float = FRQI_SINGLE_QUBIT_ERROR,
    two_qubit_error: float = FRQI_TWO_QUBIT_ERROR,
) -> NoiseModel:
    model = NoiseModel()
    model.add_all_qubit_quantum_error(depolarizing_error(single_qubit_error, 1), ["u"])
    model.add_all_qubit_quantum_error(depolarizing_error(two_qubit_error, 2), ["cx"])
    return model


def build_grover_noise_model(
    scale_factor: float = 1.0,
    *,
    single_qubit_error: float = GROVER_SINGLE_QUBIT_ERROR,
    two_qubit_error: float = GROVER_TWO_QUBIT_ERROR,
) -> NoiseModel:
    if scale_factor <= 0:
        raise ValueError("Noise scale factor must be positive")
    single = min(0.999, single_qubit_error * scale_factor)
    two = min(0.999, two_qubit_error * scale_factor)
    model = NoiseModel()
    model.add_all_qubit_quantum_error(depolarizing_error(single, 1), ["u"])
    model.add_all_qubit_quantum_error(depolarizing_error(two, 2), ["cx"])
    return model


def select_sparse_grover_noise_targets(
    circuit: QuantumCircuit,
    *,
    max_gate_occurrences: int = GROVER_MAX_NOISY_GATE_OCCURRENCES,
) -> dict[str, Any]:
    """Select least-used transpiled locations without exceeding the occurrence budget."""
    single_counts: Counter[int] = Counter()
    two_counts: Counter[tuple[int, int]] = Counter()
    for instruction in circuit.data:
        if instruction.operation.name == "u":
            single_counts[circuit.find_bit(instruction.qubits[0]).index] += 1
        elif instruction.operation.name == "cx":
            pair = tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits)
            two_counts[pair] += 1

    remaining = max(0, max_gate_occurrences)
    selected_pair: tuple[int, int] | None = None
    selected_pair_occurrences = 0
    if two_counts:
        candidate, occurrences = min(
            two_counts.items(),
            key=lambda item: (item[1], item[0]),
        )
        if occurrences <= remaining:
            selected_pair = candidate
            selected_pair_occurrences = occurrences
            remaining -= occurrences

    selected_qubit: int | None = None
    selected_qubit_occurrences = 0
    if single_counts:
        candidate, occurrences = min(
            single_counts.items(),
            key=lambda item: (item[1], item[0]),
        )
        if occurrences <= remaining:
            selected_qubit = candidate
            selected_qubit_occurrences = occurrences

    affected = selected_pair_occurrences + selected_qubit_occurrences
    total = sum(two_counts.values()) + sum(single_counts.values())
    return {
        "singleQubit": selected_qubit,
        "singleQubitGateOccurrences": selected_qubit_occurrences,
        "twoQubitPair": list(selected_pair) if selected_pair is not None else None,
        "twoQubitGateOccurrences": selected_pair_occurrences,
        "affectedGateOccurrences": affected,
        "maximumAffectedGateOccurrences": max_gate_occurrences,
        "totalEligibleGateOccurrences": total,
        "totalSingleQubitGates": sum(single_counts.values()),
        "totalTwoQubitGates": sum(two_counts.values()),
        "coverageFraction": affected / total if total else 0.0,
    }


def build_sparse_grover_noise_model(
    targets: dict[str, Any],
    scale_factor: float = 1.0,
    *,
    single_qubit_error: float = GROVER_SINGLE_QUBIT_ERROR,
    two_qubit_error: float = GROVER_TWO_QUBIT_ERROR,
) -> NoiseModel:
    if scale_factor <= 0:
        raise ValueError("Noise scale factor must be positive")
    model = NoiseModel()
    selected_qubit = targets.get("singleQubit")
    selected_pair = targets.get("twoQubitPair")
    if selected_qubit is not None and single_qubit_error > 0:
        model.add_quantum_error(
            depolarizing_error(min(0.999, single_qubit_error * scale_factor), 1),
            ["u"],
            [int(selected_qubit)],
        )
    if selected_pair is not None and two_qubit_error > 0:
        model.add_quantum_error(
            depolarizing_error(min(0.999, two_qubit_error * scale_factor), 2),
            ["cx"],
            [int(value) for value in selected_pair],
        )
    return model


def readout_matrix(
    zero_to_one: float = YLC_ZERO_TO_ONE_ERROR,
    one_to_zero: float = YLC_ONE_TO_ZERO_ERROR,
) -> tuple[tuple[float, float], tuple[float, float]]:
    return ((1.0 - zero_to_one, zero_to_one), (one_to_zero, 1.0 - one_to_zero))


def build_ylc_readout_noise_model(
    zero_to_one: float = YLC_ZERO_TO_ONE_ERROR,
    one_to_zero: float = YLC_ONE_TO_ZERO_ERROR,
) -> NoiseModel:
    model = NoiseModel()
    model.add_all_qubit_readout_error(ReadoutError(readout_matrix(zero_to_one, one_to_zero)))
    return model

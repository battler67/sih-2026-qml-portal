"""Coherent mismatch search with unknown-M fixed-point amplification.

The two input strings are compiled independently into reversible lookup gates.
No Python-side mismatch list or mismatch count is used to construct the oracle
or choose the amplification schedule.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import acosh, atan2, cosh, pi, sqrt, tan

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import StatePreparation
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

from .base import QuantumRunOptions
from .metrics import gate_count_groups


BASE_BITS = {"A": (0, 0), "C": (1, 0), "G": (0, 1), "T": (1, 1)}
DEFAULT_DELTA = 0.2


@dataclass(frozen=True)
class FixedPointSchedule:
    """Yoder-Low-Chuang phase schedule for a lower-bounded target fraction."""

    delta: float
    lambda_min: float
    sequence_length: int
    width: float
    alpha: tuple[float, ...]
    beta: tuple[float, ...]

    @property
    def generalized_iterations(self) -> int:
        return len(self.alpha)

    @property
    def predicate_queries(self) -> int:
        return self.sequence_length - 1


def _gamma(delta: float, sequence_length: int) -> float:
    return 1.0 / cosh(acosh(1.0 / delta) / sequence_length)


def build_fixed_point_schedule(
    lambda_min: float, *, delta: float = DEFAULT_DELTA
) -> FixedPointSchedule:
    """Choose the shortest odd YLC sequence whose guaranteed width fits lambda_min."""
    if not 0.0 < lambda_min <= 1.0:
        raise ValueError("lambda_min must be in (0, 1]")
    if not 0.0 < delta < 1.0:
        raise ValueError("delta must be in (0, 1)")
    sequence_length = 1
    while True:
        gamma = _gamma(delta, sequence_length)
        width = 1.0 - gamma * gamma
        if width <= lambda_min + 1e-15:
            break
        sequence_length += 2

    iterations = (sequence_length - 1) // 2
    alpha: list[float] = []
    for j in range(1, iterations + 1):
        argument = tan(2.0 * pi * j / sequence_length)
        argument *= sqrt(max(0.0, 1.0 - gamma * gamma))
        alpha.append(2.0 * atan2(1.0, argument))
    beta = [-alpha[iterations - j] for j in range(1, iterations + 1)]
    return FixedPointSchedule(
        delta=delta,
        lambda_min=lambda_min,
        sequence_length=sequence_length,
        width=width,
        alpha=tuple(alpha),
        beta=tuple(beta),
    )


def _condition_on_position(circuit: QuantumCircuit, position: list, value: int) -> None:
    for bit, qubit in enumerate(position):
        if not ((value >> bit) & 1):
            circuit.x(qubit)


def _controlled_x_for_position(
    circuit: QuantumCircuit, position: list, target, value: int
) -> None:
    _condition_on_position(circuit, position, value)
    circuit.mcx(position, target)
    _condition_on_position(circuit, position, value)


def append_sequence_lookup(
    circuit: QuantumCircuit, position: list, value_register: list, sequence: str
) -> None:
    """XOR a two-bit A/C/G/T symbol into value_register for the indexed position."""
    for index, base in enumerate(sequence):
        for bit, enabled in enumerate(BASE_BITS[base]):
            if enabled:
                _controlled_x_for_position(circuit, position, value_register[bit], index)


def append_mismatch_compute(
    circuit: QuantumCircuit, reference: list, query: list, difference: list, flag
) -> None:
    """Compute flag = (reference != query) reversibly, with clean input work bits."""
    for bit in range(2):
        circuit.cx(reference[bit], difference[bit])
        circuit.cx(query[bit], difference[bit])
    circuit.cx(difference[0], flag)
    circuit.cx(difference[1], flag)
    circuit.ccx(difference[0], difference[1], flag)


def append_mismatch_uncompute(
    circuit: QuantumCircuit, reference: list, query: list, difference: list, flag
) -> None:
    circuit.ccx(difference[0], difference[1], flag)
    circuit.cx(difference[1], flag)
    circuit.cx(difference[0], flag)
    for bit in reversed(range(2)):
        circuit.cx(query[bit], difference[bit])
        circuit.cx(reference[bit], difference[bit])


def _append_zero_phase(circuit: QuantumCircuit, angle: float) -> None:
    qubits = list(circuit.qubits)
    for qubit in qubits:
        circuit.x(qubit)
    circuit.mcp(angle, qubits[:-1], qubits[-1])
    for qubit in qubits:
        circuit.x(qubit)


def build_hybrid_fixed_point_circuits(
    reference_sequence: str,
    query_sequence: str,
    *,
    delta: float = DEFAULT_DELTA,
) -> dict[str, QuantumCircuit | FixedPointSchedule]:
    """Build preparation, coherent predicate, fixed-point sequence, and measurement."""
    reference = reference_sequence.strip().upper()
    query = query_sequence.strip().upper()
    if len(reference) != len(query):
        raise ValueError("Hybrid mismatch comparison requires equal-length sequences")
    if not reference or any(base not in BASE_BITS for base in reference + query):
        raise ValueError("Hybrid mismatch comparison accepts non-empty A/C/G/T sequences only")
    length = len(reference)
    width = max(1, (length - 1).bit_length())
    position = QuantumRegister(width, "pos")
    ref_value = QuantumRegister(2, "ref")
    query_value = QuantumRegister(2, "query")
    difference = QuantumRegister(2, "xor")
    mismatch = QuantumRegister(1, "mismatch")

    preparation = QuantumCircuit(
        position, ref_value, query_value, difference, mismatch, name="A_qrom_pair"
    )
    capacity = 1 << width
    amplitude = 1.0 / sqrt(length)
    preparation.append(
        StatePreparation([amplitude if index < length else 0.0 for index in range(capacity)]),
        position,
    )
    append_sequence_lookup(preparation, list(position), list(ref_value), reference)
    append_sequence_lookup(preparation, list(position), list(query_value), query)

    predicate = QuantumCircuit(
        position, ref_value, query_value, difference, mismatch, name="compute_mismatch"
    )
    append_mismatch_compute(
        predicate, list(ref_value), list(query_value), list(difference), mismatch[0]
    )

    schedule = build_fixed_point_schedule(1.0 / length, delta=delta)
    full = preparation.copy(name="hybrid_fixed_point")
    for step, (alpha, beta) in enumerate(zip(schedule.alpha, schedule.beta), start=1):
        # S_t(beta): derive the target flag from loaded symbols, phase it, and
        # uncompute. The circuit never receives mismatch indices.
        append_mismatch_compute(
            full, list(ref_value), list(query_value), list(difference), mismatch[0]
        )
        full.p(beta, mismatch[0])
        append_mismatch_uncompute(
            full, list(ref_value), list(query_value), list(difference), mismatch[0]
        )
        # S_s(alpha) = A S_0(-alpha) A^\dagger in circuit time order.
        full.compose(preparation.inverse(), inplace=True)
        _append_zero_phase(full, -alpha)
        full.compose(preparation, inplace=True)
        full.barrier(label=f"YLC {step}")

    unmeasured = full.copy(name="hybrid_fixed_point_state")
    measured = full.copy(name="hybrid_fixed_point_measured")
    classical = ClassicalRegister(width, "c_pos")
    measured.add_register(classical)
    measured.measure(position, classical)
    return {
        "preparation": preparation,
        "predicate": predicate,
        "unmeasured": unmeasured,
        "measured": measured,
        "schedule": schedule,
    }


def _position_probabilities(circuit: QuantumCircuit, width: int, length: int) -> dict[str, float]:
    values = Statevector.from_instruction(circuit).probabilities(qargs=list(range(width)))
    return {str(index): float(values[index]) for index in range(length)}


class HybridQuantumSearchEngine:
    """Hybrid window scorer backed by coherent fixed-point mismatch localization."""

    algorithm_name = "hybrid"

    def validate_request(self, query_sequence: str, target_sequence: str) -> None:
        if len(query_sequence) != len(target_sequence):
            raise ValueError("Hybrid mismatch comparison requires equal query/window lengths")
        if not query_sequence or any(base not in BASE_BITS for base in query_sequence + target_sequence):
            raise ValueError("Hybrid mismatch comparison accepts A/C/G/T sequences only")

    def estimate_resources(self, query_length: int, target_length: int) -> dict:
        if query_length != target_length or query_length < 1:
            raise ValueError("Hybrid estimation requires equal positive sequence lengths")
        width = max(1, (query_length - 1).bit_length())
        schedule = build_fixed_point_schedule(1.0 / query_length)
        return {
            "estimatedLogicalQubits": width + 7,
            "estimatedGroverIterations": schedule.generalized_iterations,
            "estimatedPredicateQueries": schedule.predicate_queries,
            "fixedPointSequenceLength": schedule.sequence_length,
            "notes": [
                "YLC schedule uses lambda_min=1/N and does not use the actual mismatch count M",
                "Reference/query symbols are independently compiled into reversible lookup gates",
            ],
        }

    def run(self, query_sequence: str, target_sequence: str, options: QuantumRunOptions) -> dict:
        self.validate_request(query_sequence, target_sequence)
        circuits = build_hybrid_fixed_point_circuits(target_sequence, query_sequence)
        unmeasured = circuits["unmeasured"]
        measured = circuits["measured"]
        schedule = circuits["schedule"]
        assert isinstance(unmeasured, QuantumCircuit)
        assert isinstance(measured, QuantumCircuit)
        assert isinstance(schedule, FixedPointSchedule)

        width = max(1, (len(query_sequence) - 1).bit_length())
        exact_probabilities = _position_probabilities(unmeasured, width, len(query_sequence))
        backend = AerSimulator(seed_simulator=12345)
        compiled = transpile(
            measured,
            basis_gates=["u", "cx"],
            optimization_level=1,
            seed_transpiler=12345,
        )
        raw_counts = backend.run(compiled, shots=options.shots).result().get_counts()
        counts = dict(sorted((key.replace(" ", ""), int(value)) for key, value in raw_counts.items()))
        shot_probabilities = {
            str(index): counts.get(format(index, f"0{width}b"), 0) / options.shots
            for index in range(len(query_sequence))
        }
        baseline = 1.0 / len(query_sequence)
        sigma = sqrt(baseline * (1.0 - baseline) / options.shots)
        candidates = [
            index
            for index in range(len(query_sequence))
            if shot_probabilities[str(index)] > baseline + 3.0 * sigma
        ]
        score = sum(max(0.0, probability - baseline) for probability in exact_probabilities.values())
        logical_counts = unmeasured.count_ops()
        transpiled_counts = compiled.count_ops()
        return {
            "algorithm": self.algorithm_name,
            "quantumScore": score,
            "mismatchAmplificationScore": score,
            "counts": counts,
            "indexProbabilities": shot_probabilities,
            "exactIndexProbabilities": exact_probabilities,
            "measuredCandidateIndices": candidates,
            "iterationsExecuted": schedule.generalized_iterations,
            "predicateQueries": schedule.predicate_queries,
            "fixedPointSequenceLength": schedule.sequence_length,
            "fixedPointDelta": schedule.delta,
            "fixedPointFailureProbabilityBound": schedule.delta**2,
            "lambdaLowerBound": schedule.lambda_min,
            "guaranteedWidth": schedule.width,
            "phaseSchedule": {
                "alpha": list(schedule.alpha),
                "beta": list(schedule.beta),
            },
            "oracleConstruction": (
                "Coherent two-bit XOR/OR mismatch predicate over independently compiled "
                "reference and query lookup circuits; no mismatch-position list is supplied"
            ),
            "mismatchPositionsCalculatedClassically": False,
            "mismatchCountUsedForSchedule": False,
            "circuitMetrics": {
                "logical_qubits": unmeasured.num_qubits,
                "depth": unmeasured.depth(),
                "size": unmeasured.size(),
                "operation_counts": {str(key): int(value) for key, value in logical_counts.items()},
                **gate_count_groups(logical_counts),
            },
            "transpiledCircuitMetrics": {
                "logical_qubits": compiled.num_qubits,
                "depth": compiled.depth(),
                "size": compiled.size(),
                "operation_counts": {str(key): int(value) for key, value in transpiled_counts.items()},
                **gate_count_groups(transpiled_counts),
            },
            "warnings": [
                "Input sequences are classical and compiled into QROM-style gates; free QRAM is not assumed",
                "The fixed-point guarantee applies when at least one but not every position is a mismatch",
                "Candidate positions are inferred from shot probabilities, not from a Python mismatch scan",
            ],
            "methodNote": (
                "Yoder-Low-Chuang fixed-point amplification of an in-circuit DNA mismatch predicate"
            ),
        }

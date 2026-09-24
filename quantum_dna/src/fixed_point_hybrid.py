"""Unknown-M fixed-point amplification with an in-circuit DNA comparator."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import acos, acosh, atan2, cos, cosh, pi, sqrt, tan

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Statevector

from .encoding import position_qubit_count, validate_pair
from .frqi_state import position_state_gate


DNA_BITS = {
    "A": (0, 0),
    "C": (0, 1),
    "G": (1, 0),
    "T": (1, 1),
}


@dataclass(frozen=True)
class FixedPointExperiment:
    """Circuit and exact verification data for one fixed-point experiment."""

    circuit: QuantumCircuit
    phases: tuple[tuple[float, float], ...]
    position_probabilities: dict[int, float]
    success_probability: float
    clean_work_probability: float
    guaranteed_success_probability: float
    lambda_min: float
    delta: float


@dataclass(frozen=True)
class FixedPointSchedule:
    """Yoder-Low-Chuang schedule derived without knowing the actual M."""

    sequence_length: int
    delta: float
    lambda_min: float
    odd_length: int
    rounds: int
    gamma: float
    guaranteed_width: float
    guaranteed_success_probability: float
    phases: tuple[tuple[float, float], ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _condition_on_value(
    circuit: QuantumCircuit, position_qubits: list, value: int
) -> None:
    for bit, qubit in enumerate(position_qubits):
        if not ((value >> bit) & 1):
            circuit.x(qubit)


def _controlled_x_for_position(
    circuit: QuantumCircuit, position_qubits: list, target, position: int
) -> None:
    """Toggle target exactly when the little-endian position equals position."""
    _condition_on_value(circuit, position_qubits, position)
    if len(position_qubits) == 1:
        circuit.cx(position_qubits[0], target)
    else:
        circuit.mcx(position_qubits, target)
    _condition_on_value(circuit, position_qubits, position)


def _append_qrom_load(
    circuit: QuantumCircuit, position_qubits: list, data_qubits: list, sequence: str
) -> None:
    """XOR a classically specified DNA table into a two-qubit data register."""
    for position, base in enumerate(sequence):
        for bit, value in enumerate(DNA_BITS[base]):
            if value:
                _controlled_x_for_position(
                    circuit, position_qubits, data_qubits[bit], position
                )


def append_qrom_pair_load(
    circuit: QuantumCircuit,
    position_qubits: list,
    ref_qubits: list,
    qry_qubits: list,
    reference: str,
    query: str,
) -> None:
    """Coherently XOR both classically specified DNA tables into data qubits."""
    _append_qrom_load(circuit, position_qubits, ref_qubits, reference)
    _append_qrom_load(circuit, position_qubits, qry_qubits, query)


def _append_difference_compute(
    circuit: QuantumCircuit, ref_qubits: list, qry_qubits: list, flag
) -> None:
    """Set flag iff the loaded two-bit symbols differ, preserving the query."""
    circuit.cx(qry_qubits[0], ref_qubits[0])
    circuit.cx(qry_qubits[1], ref_qubits[1])
    circuit.x(flag)
    circuit.x(ref_qubits)
    circuit.mcx(ref_qubits, flag)
    circuit.x(ref_qubits)


def _append_difference_uncompute(
    circuit: QuantumCircuit, ref_qubits: list, qry_qubits: list, flag
) -> None:
    circuit.x(ref_qubits)
    circuit.mcx(ref_qubits, flag)
    circuit.x(ref_qubits)
    circuit.x(flag)
    circuit.cx(qry_qubits[1], ref_qubits[1])
    circuit.cx(qry_qubits[0], ref_qubits[0])


def append_coherent_mismatch_phase(
    circuit: QuantumCircuit,
    position_qubits: list,
    ref_qubits: list,
    qry_qubits: list,
    flag,
    reference: str,
    query: str,
    phase: float,
) -> None:
    """Apply exp(i*phase) exactly to positions whose loaded bases differ."""
    append_qrom_pair_load(
        circuit,
        position_qubits,
        ref_qubits,
        qry_qubits,
        reference,
        query,
    )
    _append_difference_compute(circuit, ref_qubits, qry_qubits, flag)
    circuit.p(phase, flag)
    _append_difference_uncompute(circuit, ref_qubits, qry_qubits, flag)
    # Each QROM load is an XOR and is therefore its own inverse. Reverse the
    # two independent tables to make the intended uncomputation explicit.
    _append_qrom_load(circuit, position_qubits, qry_qubits, query)
    _append_qrom_load(circuit, position_qubits, ref_qubits, reference)


def _append_zero_phase(
    circuit: QuantumCircuit, qubits: list, phase: float
) -> None:
    """Apply exp(i*phase) only to the all-zero state of qubits."""
    circuit.x(qubits)
    if len(qubits) == 1:
        circuit.p(phase, qubits[0])
    else:
        circuit.mcp(phase, qubits[:-1], qubits[-1])
    circuit.x(qubits)


def build_fixed_point_schedule(
    length: int, *, delta: float = 0.2, lambda_min: float | None = None
) -> FixedPointSchedule:
    """Build the shortest Yoder-Low-Chuang schedule for a promised lower bound.

    ``lambda_min`` is a promised lower bound on the marked fraction. By
    default, one possible mismatch among ``length`` positions gives 1/length.
    """
    if length < 2:
        raise ValueError("fixed-point amplification needs at least two positions")
    if not 0.0 < delta < 1.0:
        raise ValueError("delta must be strictly between zero and one")
    lower_bound = 1.0 / length if lambda_min is None else lambda_min
    if not 0.0 < lower_bound <= 1.0:
        raise ValueError("lambda_min must be in (0, 1]")

    # For odd L=2l+1, w(L)=1-gamma^2 is the smallest marked fraction
    # guaranteed to reach success >= 1-delta^2. Choose the shortest schedule
    # whose guaranteed width includes lambda_min.
    odd_length = 3
    while True:
        gamma = 1.0 / cosh(acosh(1.0 / delta) / odd_length)
        width = 1.0 - gamma * gamma
        if width <= lower_bound:
            break
        odd_length += 2

    rounds = (odd_length - 1) // 2
    root = sqrt(max(0.0, 1.0 - gamma * gamma))
    alphas = []
    for j in range(1, rounds + 1):
        x = tan(2.0 * pi * j / odd_length) * root
        alphas.append(2.0 * atan2(1.0, x))
    betas = [-alphas[rounds - j] for j in range(1, rounds + 1)]
    phases = tuple(zip(alphas, betas))
    return FixedPointSchedule(
        sequence_length=length,
        delta=delta,
        lambda_min=lower_bound,
        odd_length=odd_length,
        rounds=rounds,
        gamma=gamma,
        guaranteed_width=width,
        guaranteed_success_probability=1.0 - delta * delta,
        phases=phases,
    )


def fixed_point_phases(
    length: int, *, delta: float = 0.2, lambda_min: float | None = None
) -> tuple[tuple[float, float], ...]:
    """Return only the matched phase pairs for compatibility."""
    return build_fixed_point_schedule(
        length, delta=delta, lambda_min=lambda_min
    ).phases


def theoretical_fixed_point_success(
    marked_fraction: float, schedule: FixedPointSchedule
) -> float:
    """Evaluate the ideal Chebyshev success polynomial for this schedule."""
    if not 0.0 <= marked_fraction <= 1.0:
        raise ValueError("marked_fraction must be in [0, 1]")
    argument = sqrt(1.0 - marked_fraction) / schedule.gamma
    if argument <= 1.0:
        chebyshev = cos(schedule.odd_length * acos(argument))
    else:
        chebyshev = cosh(schedule.odd_length * acosh(argument))
    success = 1.0 - schedule.delta * schedule.delta * chebyshev * chebyshev
    return min(1.0, max(0.0, success))


def build_position_preparation(length: int) -> QuantumCircuit:
    """Prepare uniform amplitude on valid positions and zero on padding."""
    width = position_qubit_count(length)
    circuit = QuantumCircuit(width, name="A_valid_pos")
    circuit.append(position_state_gate(length), circuit.qubits)
    return circuit


def build_qrom_pair_loader(reference: str, query: str) -> QuantumCircuit:
    """Build the reversible pair lookup without comparing the loaded bases."""
    ref, qry = validate_pair(reference, query)
    pos = QuantumRegister(position_qubit_count(len(ref)), "pos")
    ref_data = QuantumRegister(2, "ref_data")
    qry_data = QuantumRegister(2, "qry_data")
    circuit = QuantumCircuit(pos, ref_data, qry_data, name="U_DNA_load")
    append_qrom_pair_load(
        circuit, list(pos), list(ref_data), list(qry_data), ref, qry
    )
    return circuit


def build_xor_comparator() -> QuantumCircuit:
    """Build the reversible two-bit inequality computation with a clean flag."""
    ref_data = QuantumRegister(2, "ref_data")
    qry_data = QuantumRegister(2, "qry_data")
    flag = QuantumRegister(1, "different")
    circuit = QuantumCircuit(ref_data, qry_data, flag, name="U_not_equal")
    _append_difference_compute(circuit, list(ref_data), list(qry_data), flag[0])
    return circuit


def build_coherent_mismatch_oracle(
    reference: str, query: str, phase: float
) -> QuantumCircuit:
    """Build load-compute-phase-uncompute without a mismatch-position list."""
    ref, qry = validate_pair(reference, query)
    pos = QuantumRegister(position_qubit_count(len(ref)), "pos")
    ref_data = QuantumRegister(2, "ref_data")
    qry_data = QuantumRegister(2, "qry_data")
    flag = QuantumRegister(1, "different")
    circuit = QuantumCircuit(
        pos, ref_data, qry_data, flag, name="S_mismatch"
    )
    append_coherent_mismatch_phase(
        circuit,
        list(pos),
        list(ref_data),
        list(qry_data),
        flag[0],
        ref,
        qry,
        phase,
    )
    return circuit


def build_source_phase(length: int, alpha: float) -> QuantumCircuit:
    """Build S_s(alpha), restricted to the clean-work invariant subspace."""
    preparation = build_position_preparation(length)
    circuit = QuantumCircuit(preparation.num_qubits, name="S_initial")
    circuit.compose(preparation.inverse(), inplace=True)
    _append_zero_phase(circuit, circuit.qubits, -alpha)
    circuit.compose(preparation, inplace=True)
    return circuit


def build_fixed_point_circuits(
    reference: str,
    query: str,
    *,
    delta: float = 0.2,
    lambda_min: float | None = None,
) -> dict[str, QuantumCircuit | FixedPointSchedule]:
    """Build all inspectable components and measured/unmeasured circuits."""
    ref, qry = validate_pair(reference, query)
    width = position_qubit_count(len(ref))
    schedule = build_fixed_point_schedule(
        len(ref), delta=delta, lambda_min=lambda_min
    )

    pos = QuantumRegister(width, "pos")
    ref_data = QuantumRegister(2, "ref_data")
    qry_data = QuantumRegister(2, "qry_data")
    flag = QuantumRegister(1, "different")
    full = QuantumCircuit(pos, ref_data, qry_data, flag, name="unknown_M_fp")
    preparation = build_position_preparation(len(ref))
    full.compose(preparation, qubits=pos, inplace=True)

    first_oracle = build_coherent_mismatch_oracle(
        ref, qry, schedule.phases[0][1]
    )
    first_source = build_source_phase(len(ref), schedule.phases[0][0])
    first_round = QuantumCircuit(
        pos, ref_data, qry_data, flag, name="fixed_point_round_1"
    )
    first_round.compose(first_oracle, inplace=True)
    first_round.compose(first_source, qubits=pos, inplace=True)

    for alpha, beta in schedule.phases:
        oracle = build_coherent_mismatch_oracle(ref, qry, beta)
        source = build_source_phase(len(ref), alpha)
        full.compose(oracle, inplace=True)
        full.compose(source, qubits=pos, inplace=True)

    unmeasured = full.copy()
    measured = full.copy()
    classical = ClassicalRegister(width, "c_pos")
    measured.add_register(classical)
    measured.measure(pos, classical)
    return {
        "position_preparation": preparation,
        "qrom_pair_loader": build_qrom_pair_loader(ref, qry),
        "xor_comparator": build_xor_comparator(),
        "coherent_mismatch_oracle": first_oracle,
        "source_phase": first_source,
        "first_round": first_round,
        "unmeasured": unmeasured,
        "measured": measured,
        "schedule": schedule,
    }


def build_fixed_point_mismatch_circuit(
    reference: str,
    query: str,
    *,
    delta: float = 0.2,
    lambda_min: float | None = None,
) -> tuple[QuantumCircuit, tuple[tuple[float, float], ...]]:
    """Build coherent mismatch amplification whose schedule is independent of M."""
    circuits = build_fixed_point_circuits(
        reference, query, delta=delta, lambda_min=lambda_min
    )
    schedule = circuits["schedule"]
    assert isinstance(schedule, FixedPointSchedule)
    circuit = circuits["unmeasured"]
    assert isinstance(circuit, QuantumCircuit)
    return circuit, schedule.phases


def run_fixed_point_experiment(
    reference: str,
    query: str,
    *,
    expected_positions: list[int],
    delta: float = 0.2,
    lambda_min: float | None = None,
) -> FixedPointExperiment:
    """Run exact verification; expected positions are not used to build the circuit."""
    circuit, phases = build_fixed_point_mismatch_circuit(
        reference, query, delta=delta, lambda_min=lambda_min
    )
    width = position_qubit_count(len(reference))
    state = Statevector.from_instruction(circuit)
    marginal = state.probabilities(qargs=list(range(width)))
    probabilities = {
        position: float(marginal[position]) for position in range(len(reference))
    }
    success = sum(probabilities[position] for position in expected_positions)
    work = state.probabilities(qargs=list(range(width, circuit.num_qubits)))
    clean_work = float(work[0])
    lower_bound = 1.0 / len(reference) if lambda_min is None else lambda_min
    return FixedPointExperiment(
        circuit=circuit,
        phases=phases,
        position_probabilities=probabilities,
        success_probability=success,
        clean_work_probability=clean_work,
        guaranteed_success_probability=1.0 - delta * delta,
        lambda_min=lower_bound,
        delta=delta,
    )

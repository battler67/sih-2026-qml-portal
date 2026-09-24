"""FRQI-style DNA sequence-state preparation circuits."""

from __future__ import annotations

from math import isclose, sqrt
from typing import Iterable

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from .angle_mapping import qiskit_ry_angle
from .validation import (
    is_power_of_two,
    position_qubit_count,
    position_register_size,
    validate_sequence_pair,
)


def make_registers(sequence_length: int, *, measured: bool = False):
    """Create registers in the paper's logical order.

    Register order:
    strip[0] selects reference (0) or query (1).
    pos[k] is the little-endian binary position bit 2**k.
    dna[0] is the FRQI color/value qubit.
    c[0], when present, stores the measured strip qubit.
    """

    strip = QuantumRegister(1, "strip")
    pos = QuantumRegister(position_qubit_count(sequence_length), "pos")
    dna = QuantumRegister(1, "dna")
    if measured:
        classical = ClassicalRegister(1, "c")
        return strip, pos, dna, classical
    return strip, pos, dna


def build_position_superposition(sequence_length: int) -> QuantumCircuit:
    """Build only the position-register superposition circuit."""

    pos = QuantumRegister(position_qubit_count(sequence_length), "pos")
    qc = QuantumCircuit(pos, name="position_superposition")
    _prepare_position_superposition(qc, list(pos), sequence_length)
    return qc


def _prepare_position_superposition(
    circuit: QuantumCircuit, position_qubits: list, sequence_length: int
) -> None:
    """Prepare uniform amplitude over valid positions.

    For powers of two this is the Hadamard preparation shown in the paper.
    For non-powers of two this uses an exact state-preparation vector over
    valid positions only, so unused basis states do not bias the similarity.
    """

    if is_power_of_two(sequence_length):
        for qubit in position_qubits:
            circuit.h(qubit)
        return

    capacity = position_register_size(sequence_length)
    amplitude = 1.0 / sqrt(sequence_length)
    vector = [amplitude if i < sequence_length else 0.0 for i in range(capacity)]
    circuit.initialize(vector, position_qubits)


def _bits_for_position(position: int, width: int) -> list[int]:
    return [(position >> bit) & 1 for bit in range(width)]


def _with_zero_controls(
    circuit: QuantumCircuit, controls: Iterable, control_state: Iterable[int]
) -> list:
    """Flip zero-controls to reuse Qiskit's all-one multi-control gates."""

    controls = list(controls)
    for qubit, bit in zip(controls, control_state):
        if bit == 0:
            circuit.x(qubit)
    return controls


def _restore_zero_controls(
    circuit: QuantumCircuit, controls: Iterable, control_state: Iterable[int]
) -> None:
    controls = list(controls)
    for qubit, bit in zip(controls, control_state):
        if bit == 0:
            circuit.x(qubit)


def apply_controlled_rotation_for_position(
    circuit: QuantumCircuit,
    *,
    strip_qubit,
    position_qubits: list,
    dna_qubit,
    strip_value: int,
    position: int,
    nucleotide: str,
    angle_mode: str = "paper_state",
) -> float:
    """Apply one strip-and-position controlled nucleotide rotation.

    Controls are strip followed by little-endian position bits. Controls on
    zero states are implemented with X gates before and after the MCRY.
    Returns the Qiskit RY angle used.
    """

    if strip_value not in (0, 1):
        raise ValueError("strip_value must be 0 or 1")
    if position < 0:
        raise ValueError("position must be non-negative")

    theta = qiskit_ry_angle(nucleotide, angle_mode=angle_mode)
    if isclose(theta, 0.0, abs_tol=1e-15):
        return theta

    pos_bits = _bits_for_position(position, len(position_qubits))
    controls = [strip_qubit, *position_qubits]
    control_state = [strip_value, *pos_bits]

    _with_zero_controls(circuit, controls, control_state)
    circuit.mcry(theta, controls, dna_qubit, None, mode="noancilla")
    _restore_zero_controls(circuit, controls, control_state)
    return theta


def prepare_frqi_sequence_pair(
    reference: str, query: str, *, angle_mode: str = "paper_state"
) -> QuantumCircuit:
    """Prepare the complete FRQI-inspired two-sequence state."""

    ref, qry = validate_sequence_pair(reference, query)
    sequence_length = len(ref)
    strip, pos, dna = make_registers(sequence_length, measured=False)
    qc = QuantumCircuit(strip, pos, dna, name="frqi_dna_state")

    qc.h(strip[0])
    _prepare_position_superposition(qc, list(pos), sequence_length)
    qc.barrier(label="FRQI nucleotide rotations")

    for index, nucleotide in enumerate(ref):
        apply_controlled_rotation_for_position(
            qc,
            strip_qubit=strip[0],
            position_qubits=list(pos),
            dna_qubit=dna[0],
            strip_value=0,
            position=index,
            nucleotide=nucleotide,
            angle_mode=angle_mode,
        )

    for index, nucleotide in enumerate(qry):
        apply_controlled_rotation_for_position(
            qc,
            strip_qubit=strip[0],
            position_qubits=list(pos),
            dna_qubit=dna[0],
            strip_value=1,
            position=index,
            nucleotide=nucleotide,
            angle_mode=angle_mode,
        )

    return qc


def build_frqi_dna_state(
    reference: str, query: str, *, angle_mode: str = "paper_state"
) -> QuantumCircuit:
    """Public state-preparation function requested by the task."""

    return prepare_frqi_sequence_pair(reference, query, angle_mode=angle_mode)


def build_single_nucleotide_rotation_circuit(
    *,
    sequence_length: int = 4,
    strip_value: int = 0,
    position: int = 3,
    nucleotide: str = "A",
    angle_mode: str = "paper_state",
) -> QuantumCircuit:
    """Small readable circuit for one controlled nucleotide rotation."""

    strip, pos, dna = make_registers(sequence_length, measured=False)
    qc = QuantumCircuit(strip, pos, dna, name=f"{nucleotide}_controlled_rotation")
    apply_controlled_rotation_for_position(
        qc,
        strip_qubit=strip[0],
        position_qubits=list(pos),
        dna_qubit=dna[0],
        strip_value=strip_value,
        position=position,
        nucleotide=nucleotide,
        angle_mode=angle_mode,
    )
    return qc


def build_sequence_branch_encoding(
    sequence: str,
    *,
    strip_value: int,
    angle_mode: str = "paper_state",
) -> QuantumCircuit:
    """Build a circuit containing one branch's controlled rotations."""

    ref, qry = validate_sequence_pair(sequence, sequence)
    sequence_length = len(ref)
    strip, pos, dna = make_registers(sequence_length, measured=False)
    qc = QuantumCircuit(strip, pos, dna, name=f"strip_{strip_value}_encoding")
    qc.h(strip[0])
    _prepare_position_superposition(qc, list(pos), sequence_length)
    qc.barrier(label=f"strip={strip_value} rotations")
    for index, nucleotide in enumerate(qry):
        apply_controlled_rotation_for_position(
            qc,
            strip_qubit=strip[0],
            position_qubits=list(pos),
            dna_qubit=dna[0],
            strip_value=strip_value,
            position=index,
            nucleotide=nucleotide,
            angle_mode=angle_mode,
        )
    return qc

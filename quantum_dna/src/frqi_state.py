"""FRQI-inspired sequence and paired-state preparation unitaries."""

from __future__ import annotations

from math import sqrt

from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import StatePreparation

from .encoding import angle_for, padded_length, position_qubit_count, validate_pair, validate_sequence


def position_state_gate(length: int) -> StatePreparation:
    """Unitary state preparation uniform only over valid positions."""
    capacity = padded_length(length)
    amplitude = 1 / sqrt(length)
    return StatePreparation([amplitude if i < length else 0.0 for i in range(capacity)])


def _condition(circuit: QuantumCircuit, qubits: list, value: int) -> None:
    for bit, qubit in enumerate(qubits):
        if not ((value >> bit) & 1):
            circuit.x(qubit)


def append_position_controlled_ry(
    circuit: QuantumCircuit, position_qubits: list, value_qubit, position: int, angle: float
) -> None:
    """Apply RY(angle) when the little-endian position register equals position."""
    if abs(angle) < 1e-15:
        return
    _condition(circuit, position_qubits, position)
    circuit.mcry(angle, position_qubits, value_qubit, None, mode="noancilla")
    _condition(circuit, position_qubits, position)


def build_sequence_frqi_state(sequence: str, name: str = "sequence_frqi") -> QuantumCircuit:
    """Prepare 1/sqrt(N) sum_i |i>|base-angle(i)>."""
    seq = validate_sequence(sequence)
    pos = QuantumRegister(position_qubit_count(len(seq)), "pos")
    value = QuantumRegister(1, "value")
    circuit = QuantumCircuit(pos, value, name=name)
    circuit.append(position_state_gate(len(seq)), pos)
    for i, base in enumerate(seq):
        append_position_controlled_ry(circuit, list(pos), value[0], i, angle_for(base))
    return circuit


def build_combined_frqi_state(reference: str, query: str) -> QuantumCircuit:
    """Return A for position plus separate reference/query FRQI color qubits."""
    ref, qry = validate_pair(reference, query)
    pos = QuantumRegister(position_qubit_count(len(ref)), "pos")
    ref_value = QuantumRegister(1, "ref")
    qry_value = QuantumRegister(1, "qry")
    circuit = QuantumCircuit(pos, ref_value, qry_value, name="A_FRQI_pair")
    circuit.append(position_state_gate(len(ref)), pos)
    for i, (ref_base, qry_base) in enumerate(zip(ref, qry)):
        append_position_controlled_ry(circuit, list(pos), ref_value[0], i, angle_for(ref_base))
        append_position_controlled_ry(circuit, list(pos), qry_value[0], i, angle_for(qry_base))
    return circuit

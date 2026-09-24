"""Reliable position-synthesized reversible mutation phase oracle."""

from __future__ import annotations

from qiskit import QuantumCircuit

from .encoding import classical_mutations, position_qubit_count, validate_pair


def apply_phase_on_basis_state(circuit: QuantumCircuit, qubits: list, value: int) -> None:
    """Multiply one computational-basis position by -1."""
    for bit, qubit in enumerate(qubits):
        if not ((value >> bit) & 1):
            circuit.x(qubit)
    if len(qubits) == 1:
        circuit.z(qubits[0])
    else:
        circuit.h(qubits[-1])
        circuit.mcx(qubits[:-1], qubits[-1])
        circuit.h(qubits[-1])
    for bit, qubit in enumerate(qubits):
        if not ((value >> bit) & 1):
            circuit.x(qubit)


def append_mutation_oracle(circuit: QuantumCircuit, position_qubits: list, mutations: list[int]) -> None:
    """Apply O_f|i> = (-1)^f(i)|i> using disclosed classical synthesis."""
    for position in mutations:
        apply_phase_on_basis_state(circuit, position_qubits, position)


def build_mutation_oracle(reference: str, query: str, total_qubits: int | None = None) -> QuantumCircuit:
    """Build an oracle acting on position and optional spectator FRQI qubits."""
    ref, qry = validate_pair(reference, query)
    width = position_qubit_count(len(ref))
    count = total_qubits or width + 2
    if count < width:
        raise ValueError("total_qubits cannot be smaller than the position register")
    circuit = QuantumCircuit(count, name="O_mismatch")
    append_mutation_oracle(circuit, circuit.qubits[:width], classical_mutations(ref, qry))
    return circuit

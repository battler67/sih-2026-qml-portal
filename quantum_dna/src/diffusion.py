"""Prepared-state and position-only diffusion operators."""

from __future__ import annotations

from qiskit import QuantumCircuit

from .mutation_oracle import apply_phase_on_basis_state


def append_zero_reflection(circuit: QuantumCircuit, qubits: list) -> None:
    """Apply I-2|0...0><0...0| (global-sign equivalent reflection)."""
    apply_phase_on_basis_state(circuit, qubits, 0)


def build_generalized_diffuser(state_preparation: QuantumCircuit) -> QuantumCircuit:
    """Build D_A = A S_0 A† on every register prepared by A."""
    # Diagram time is left-to-right, while matrices multiply right-to-left.
    # Therefore A†, S0, A in circuit order implements matrix A S0 A†.
    diffuser = QuantumCircuit(state_preparation.num_qubits, name="D_A")
    diffuser.compose(state_preparation.inverse(), inplace=True)
    append_zero_reflection(diffuser, diffuser.qubits)
    diffuser.compose(state_preparation, inplace=True)
    return diffuser


def build_position_diffuser(position_preparation: QuantumCircuit) -> QuantumCircuit:
    """Position-only A_pos S0 A_pos†, valid after color/work uncomputation."""
    return build_generalized_diffuser(position_preparation)

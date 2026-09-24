"""Exact-match QGSA phase oracle."""

from __future__ import annotations

from qiskit import QuantumCircuit

from .comparator import compute_pattern_mismatch, uncompute_pattern_mismatch
from .cyclic_shift import (
    apply_index_controlled_shift_network,
    apply_inverse_index_controlled_shift_network,
)
from .registers import QGSARegisters


def apply_mcz(circuit: QuantumCircuit, controls) -> None:
    controls = list(controls)
    if not controls:
        circuit.global_phase += 3.141592653589793
    elif len(controls) == 1:
        circuit.z(controls[0])
    else:
        target = controls[-1]
        circuit.h(target)
        circuit.mcx(controls[:-1], target)
        circuit.h(target)


def _condition_index(circuit: QuantumCircuit, index_qubits, value: int) -> None:
    for bit, qubit in enumerate(index_qubits):
        if ((value >> bit) & 1) == 0:
            circuit.x(qubit)


def apply_zero_state_phase_flip(
    circuit: QuantumCircuit,
    mismatch_qubits,
    *,
    index_qubits=None,
    valid_indices: list[int] | None = None,
) -> None:
    mismatch_qubits = list(mismatch_qubits)
    index_qubits = list(index_qubits or [])
    for qubit in mismatch_qubits:
        circuit.x(qubit)
    if valid_indices is None:
        apply_mcz(circuit, mismatch_qubits)
    else:
        for value in valid_indices:
            _condition_index(circuit, index_qubits, value)
            apply_mcz(circuit, [*index_qubits, *mismatch_qubits])
            _condition_index(circuit, index_qubits, value)
    for qubit in mismatch_qubits:
        circuit.x(qubit)


def append_qgsa_oracle(
    circuit: QuantumCircuit,
    regs: QGSARegisters,
    *,
    valid_indices: list[int] | None = None,
) -> None:
    apply_index_controlled_shift_network(circuit, regs)
    compute_pattern_mismatch(circuit, regs)
    apply_zero_state_phase_flip(
        circuit,
        [regs.pattern[i] for i in range(regs.pattern_symbols * regs.bits_per_symbol)],
        index_qubits=regs.index,
        valid_indices=valid_indices,
    )
    uncompute_pattern_mismatch(circuit, regs)
    apply_inverse_index_controlled_shift_network(circuit, regs)


def build_qgsa_oracle(regs: QGSARegisters, *, valid_indices: list[int] | None = None) -> QuantumCircuit:
    circuit = QuantumCircuit(regs.index, regs.target, regs.pattern, name="QGSA_oracle")
    shadow = QGSARegisters(regs.index, regs.target, regs.pattern, None, regs.bits_per_symbol, regs.target_symbols, regs.pattern_symbols)
    append_qgsa_oracle(circuit, shadow, valid_indices=valid_indices)
    return circuit

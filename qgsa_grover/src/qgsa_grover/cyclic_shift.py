"""Index-controlled complete-base cyclic shifts."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.circuit.library import SwapGate

from .encoding import encode_sequence
from .registers import QGSARegisters


def rotate_left_bases(sequence: str, shift: int) -> str:
    if not sequence:
        return sequence
    r = shift % len(sequence)
    return sequence[r:] + sequence[:r]


def rotate_right_bases(sequence: str, shift: int) -> str:
    if not sequence:
        return sequence
    r = shift % len(sequence)
    return sequence[-r:] + sequence[:-r] if r else sequence


def cyclic_shift_truth_table(target: str, bits_per_symbol: int, search_space_size: int) -> dict[int, str]:
    table: dict[int, str] = {}
    for r in range(search_space_size):
        shifted = rotate_left_bases(target, r)
        bits = encode_sequence(shifted, "paper_2bit" if bits_per_symbol == 2 else "terminator_3bit")
        table[r] = "".join(str(bit) for bit in bits)
    return table


def _condition_index_on_value(circuit: QuantumCircuit, index_qubits, value: int) -> None:
    for bit, qubit in enumerate(index_qubits):
        if ((value >> bit) & 1) == 0:
            circuit.x(qubit)


def _controlled_swap(circuit: QuantumCircuit, controls, a, b) -> None:
    if len(controls) == 1:
        circuit.cswap(controls[0], a, b)
    else:
        circuit.append(SwapGate().control(len(controls)), [*controls, a, b])


def _swap_complete_bases(circuit: QuantumCircuit, controls, target, i: int, j: int, bits_per_symbol: int) -> None:
    for offset in range(bits_per_symbol):
        _controlled_swap(
            circuit,
            controls,
            target[i * bits_per_symbol + offset],
            target[j * bits_per_symbol + offset],
        )


def controlled_rotate_left_by_bases(
    circuit: QuantumCircuit,
    controls,
    target,
    *,
    shift: int,
    target_symbols: int,
    bits_per_symbol: int,
) -> None:
    for _ in range(shift % target_symbols):
        for i in range(target_symbols - 1):
            _swap_complete_bases(circuit, controls, target, i, i + 1, bits_per_symbol)


def controlled_rotate_right_by_bases(
    circuit: QuantumCircuit,
    controls,
    target,
    *,
    shift: int,
    target_symbols: int,
    bits_per_symbol: int,
) -> None:
    for _ in range(shift % target_symbols):
        for i in reversed(range(target_symbols - 1)):
            _swap_complete_bases(circuit, controls, target, i, i + 1, bits_per_symbol)


def apply_index_controlled_shift_network(circuit: QuantumCircuit, regs: QGSARegisters) -> None:
    max_states = 2 ** len(regs.index)
    for value in range(1, min(max_states, regs.target_symbols)):
        _condition_index_on_value(circuit, regs.index, value)
        controlled_rotate_left_by_bases(
            circuit,
            list(regs.index),
            regs.target,
            shift=value,
            target_symbols=regs.target_symbols,
            bits_per_symbol=regs.bits_per_symbol,
        )
        _condition_index_on_value(circuit, regs.index, value)


def apply_inverse_index_controlled_shift_network(circuit: QuantumCircuit, regs: QGSARegisters) -> None:
    max_states = 2 ** len(regs.index)
    for value in reversed(range(1, min(max_states, regs.target_symbols))):
        _condition_index_on_value(circuit, regs.index, value)
        controlled_rotate_right_by_bases(
            circuit,
            list(regs.index),
            regs.target,
            shift=value,
            target_symbols=regs.target_symbols,
            bits_per_symbol=regs.bits_per_symbol,
        )
        _condition_index_on_value(circuit, regs.index, value)


def build_cyclic_shift_operator(regs: QGSARegisters) -> QuantumCircuit:
    circuit = QuantumCircuit(regs.index, regs.target, name="U_shift")
    shadow = QGSARegisters(regs.index, regs.target, regs.pattern, None, regs.bits_per_symbol, regs.target_symbols, regs.pattern_symbols)
    apply_index_controlled_shift_network(circuit, shadow)
    return circuit

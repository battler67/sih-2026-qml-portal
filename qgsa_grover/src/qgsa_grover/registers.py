"""QGSA register creation and ordering documentation."""

from __future__ import annotations

from dataclasses import dataclass

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister


@dataclass
class QGSARegisters:
    index: QuantumRegister
    target: QuantumRegister
    pattern: QuantumRegister
    classical_index: ClassicalRegister | None
    bits_per_symbol: int
    target_symbols: int
    pattern_symbols: int


def create_registers(
    *,
    index_qubits: int,
    target_symbols: int,
    pattern_symbols: int,
    bits_per_symbol: int,
    measured: bool = False,
) -> tuple[QuantumCircuit, QGSARegisters]:
    index = QuantumRegister(index_qubits, "idx")
    target = QuantumRegister(target_symbols * bits_per_symbol, "tgt")
    pattern = QuantumRegister(pattern_symbols * bits_per_symbol, "pat")
    classical = ClassicalRegister(index_qubits, "c_idx") if measured else None
    registers = [index, target, pattern]
    if classical is not None:
        registers.append(classical)
    circuit = QuantumCircuit(*registers, name="qgsa")
    return circuit, QGSARegisters(
        index=index,
        target=target,
        pattern=pattern,
        classical_index=classical,
        bits_per_symbol=bits_per_symbol,
        target_symbols=target_symbols,
        pattern_symbols=pattern_symbols,
    )


REGISTER_ORDERING_NOTE = (
    "Circuit registers are ordered idx, tgt, pat, then c_idx when measured. "
    "Within a nucleotide, qubit offset 0 stores the left bit of the paper code "
    "(for example T=11 sets both offsets). Qiskit count strings print classical "
    "bits most-significant first, so idx[0]=1, idx[1]=0 is displayed as '01'. "
    "Decode measured index strings by reversing the displayed bit string before "
    "converting to an integer."
)

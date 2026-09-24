"""Initial state construction."""

from qiskit import QuantumCircuit

from .encoding import encode_sequence
from .registers import QGSARegisters


def initialize_index_superposition(circuit: QuantumCircuit, regs: QGSARegisters) -> None:
    circuit.h(regs.index)


def initialize_basis_sequence(circuit: QuantumCircuit, qubits, sequence: str, encoding_mode: str) -> None:
    bits = encode_sequence(sequence, encoding_mode)
    if len(bits) != len(qubits):
        raise ValueError("encoded sequence length does not match register size")
    for qubit, bit in zip(qubits, bits):
        if bit:
            circuit.x(qubit)


def build_initial_qgsa_state(
    circuit: QuantumCircuit,
    regs: QGSARegisters,
    *,
    target: str,
    pattern: str,
    encoding_mode: str,
) -> QuantumCircuit:
    initialize_index_superposition(circuit, regs)
    initialize_basis_sequence(circuit, regs.target, target, encoding_mode)
    initialize_basis_sequence(circuit, regs.pattern, pattern, encoding_mode)
    return circuit


def build_initialization_circuit(
    *,
    index_qubits: int,
    target: str,
    pattern: str,
    target_symbols: int,
    bits_per_symbol: int,
    encoding_mode: str,
):
    from .registers import create_registers

    circuit, regs = create_registers(
        index_qubits=index_qubits,
        target_symbols=target_symbols,
        pattern_symbols=len(pattern),
        bits_per_symbol=bits_per_symbol,
    )
    return build_initial_qgsa_state(circuit, regs, target=target, pattern=pattern, encoding_mode=encoding_mode)

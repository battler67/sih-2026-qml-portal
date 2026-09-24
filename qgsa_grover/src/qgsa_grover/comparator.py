"""CNOT mismatch computation."""

from qiskit import QuantumCircuit

from .registers import QGSARegisters


def compute_pattern_mismatch(circuit: QuantumCircuit, regs: QGSARegisters) -> None:
    total_bits = regs.pattern_symbols * regs.bits_per_symbol
    for bit in range(total_bits):
        circuit.cx(regs.target[bit], regs.pattern[bit])


def uncompute_pattern_mismatch(circuit: QuantumCircuit, regs: QGSARegisters) -> None:
    compute_pattern_mismatch(circuit, regs)


def build_comparator_circuit(regs: QGSARegisters) -> QuantumCircuit:
    circuit = QuantumCircuit(regs.target, regs.pattern, name="compare")
    shadow = QGSARegisters(regs.index, regs.target, regs.pattern, None, regs.bits_per_symbol, regs.target_symbols, regs.pattern_symbols)
    compute_pattern_mismatch(circuit, shadow)
    return circuit

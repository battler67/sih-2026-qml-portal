"""Manual Grover diffuser on the index register."""

from qiskit import QuantumCircuit

from .oracle import apply_mcz


def append_diffuser(circuit: QuantumCircuit, index_qubits) -> None:
    index_qubits = list(index_qubits)
    circuit.h(index_qubits)
    circuit.x(index_qubits)
    apply_mcz(circuit, index_qubits)
    circuit.x(index_qubits)
    circuit.h(index_qubits)


def build_diffuser_circuit(index_qubits: int) -> QuantumCircuit:
    circuit = QuantumCircuit(index_qubits, name="diffuser")
    append_diffuser(circuit, circuit.qubits)
    return circuit

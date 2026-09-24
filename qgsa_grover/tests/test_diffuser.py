from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from qgsa_grover.diffuser import append_diffuser
from qgsa_grover.oracle import apply_zero_state_phase_flip


def test_diffuser_amplifies_one_marked_state_in_four():
    qc = QuantumCircuit(2)
    qc.h([0, 1])
    apply_zero_state_phase_flip(qc, [qc.qubits[0], qc.qubits[1]], index_qubits=None)
    append_diffuser(qc, qc.qubits)
    probs = Statevector.from_instruction(qc).probabilities_dict(qargs=[0, 1])
    assert float(probs["00"]) > 0.99

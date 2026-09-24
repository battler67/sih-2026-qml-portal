from qiskit.quantum_info import Statevector

from qgsa_grover.qgsa import build_qgsa_circuit


def test_initialization_index_uniform_before_grover():
    circuit, meta = build_qgsa_circuit(target="ACGT", pattern="A", iterations=0)
    probs = Statevector.from_instruction(circuit).probabilities_dict(qargs=[0, 1])
    assert meta["index_qubits"] == 2
    assert set(str(k) for k in probs) == {"00", "01", "10", "11"}
    assert all(abs(float(p) - 0.25) < 1e-9 for p in probs.values())

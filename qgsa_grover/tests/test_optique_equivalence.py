from qiskit.quantum_info import Statevector

from qgsa_grover.optique import build_optique_circuit, compare_original_and_optimized
from qgsa_grover.qgsa import build_qgsa_circuit


def test_optique_paper_example_index_distribution_equivalent():
    original, meta = build_qgsa_circuit(target="ACGT", pattern="A", iterations="auto")
    opt = build_optique_circuit("ACGT", "A", iterations="auto", solution_count=1)
    p_original = Statevector.from_instruction(original).probabilities_dict(qargs=[0, 1])
    p_opt = Statevector.from_instruction(opt).probabilities_dict(qargs=[0, 1])
    for key in p_original:
        assert abs(float(p_original[key]) - float(p_opt[key])) < 1e-9
    metrics = compare_original_and_optimized(original, opt)
    assert metrics["optimized"]["logical_qubits"] == 6

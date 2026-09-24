import numpy as np
import pytest
from qiskit.quantum_info import Operator, Statevector

from quantum_dna.src.diffusion import build_generalized_diffuser
from quantum_dna.src.encoding import position_qubit_count
from quantum_dna.src.frqi_state import build_combined_frqi_state
from quantum_dna.src.grover_amplification import build_localization_circuits, choose_iterations
from quantum_dna.src.simulator import position_probabilities


def test_preparation_inverse_returns_zero():
    prep = build_combined_frqi_state("ACGT", "ACTT")
    state = Statevector.from_instruction(prep).evolve(prep.inverse())
    assert np.isclose(abs(state.data[0]), 1.0)


def test_generalized_diffuser_is_unitary_and_prepared_state_eigenvector():
    prep = build_combined_frqi_state("ACGT", "ACTT")
    diffuser = build_generalized_diffuser(prep)
    matrix = Operator(diffuser).data
    assert np.allclose(matrix.conj().T @ matrix, np.eye(2**prep.num_qubits), atol=1e-10)
    state = Statevector.from_instruction(prep)
    reflected = state.evolve(diffuser)
    assert np.isclose(abs(np.vdot(state.data, reflected.data)), 1.0, atol=1e-10)


@pytest.mark.parametrize(
    ("reference", "query", "expected_total"),
    [
        ("AAAA", "AAAT", 1.0),
        ("ACGTACGT", "ATGTACAT", 1.0),
        ("ACGTA", "ATGTT", 0.784),
    ],
)
def test_exact_marked_probability_matches_grover_theory(reference, query, expected_total):
    circuits = build_localization_circuits(reference, query)
    width = position_qubit_count(len(reference))
    probabilities = position_probabilities(circuits["unmeasured"], width)
    marked = [i for i, pair in enumerate(zip(reference, query)) if pair[0] != pair[1]]
    total = sum(probabilities[format(i, f"0{width}b")] for i in marked)
    padding = sum(probabilities[format(i, f"0{width}b")] for i in range(len(reference), 1 << width))
    assert total == pytest.approx(expected_total, abs=1e-10)
    assert padding == pytest.approx(0.0, abs=1e-10)


def test_iteration_input_validation():
    with pytest.raises(ValueError, match="positive"):
        choose_iterations(0, 0)
    with pytest.raises(ValueError, match="between"):
        choose_iterations(4, 5)

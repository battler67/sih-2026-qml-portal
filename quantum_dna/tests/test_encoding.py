from math import isclose, pi

import pytest
from qiskit.quantum_info import Statevector

from quantum_dna.src.encoding import angle_for, padded_length, position_qubit_count, validate_pair
from quantum_dna.src.baseline_similarity import theoretical_p1
from quantum_dna.src.frqi_state import build_combined_frqi_state


def test_paper_angle_mapping():
    assert isclose(angle_for("A"), pi)
    assert isclose(angle_for("C"), pi / 2)
    assert isclose(angle_for("T"), pi / 6)
    assert isclose(angle_for("G"), 0)
    assert isclose(theoretical_p1("AAAA", "TTTT"), 0.3705904774487395)


@pytest.mark.parametrize(("length", "qubits", "capacity"), [(1, 1, 2), (4, 2, 4), (5, 3, 8), (8, 3, 8)])
def test_position_sizing(length, qubits, capacity):
    assert position_qubit_count(length) == qubits
    assert padded_length(length) == capacity


def test_frqi_state_is_normalized():
    state = Statevector.from_instruction(build_combined_frqi_state("ACGT", "ACTT"))
    assert isclose(float(state.probabilities().sum()), 1.0, abs_tol=1e-12)


def test_validation_errors():
    with pytest.raises(ValueError, match="unsupported"):
        validate_pair("ACNT", "ACGT")
    with pytest.raises(ValueError, match="equal length"):
        validate_pair("ACG", "ACGT")

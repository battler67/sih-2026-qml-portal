import pytest

from qgsa_grover.classical_baseline import classical_exact_matches
from qgsa_grover.validation import index_qubit_count, next_power_of_two, validate_search_inputs


def test_input_validation_and_classical_baseline():
    assert validate_search_inputs("acgt", "cg") == ("ACGT", "CG")
    assert classical_exact_matches("ACGTACGT", "CGT") == [1, 5]
    with pytest.raises(ValueError):
        validate_search_inputs("AC", "ACG")


def test_index_qubits_and_padding():
    assert index_qubit_count(4) == 2
    assert index_qubit_count(5) == 3
    assert next_power_of_two(5) == 8

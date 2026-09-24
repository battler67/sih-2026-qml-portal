import pytest

from frqi_dna.src.validation import (
    position_qubit_count,
    validate_sequence,
    validate_sequence_pair,
)


def test_valid_dna_symbols():
    assert validate_sequence("ACGT") == "ACGT"


def test_lowercase_input_normalization():
    assert validate_sequence("acgt") == "ACGT"


def test_invalid_dna_symbols():
    with pytest.raises(ValueError, match="invalid DNA"):
        validate_sequence("ACNX")


def test_unequal_sequence_lengths():
    with pytest.raises(ValueError, match="equal length"):
        validate_sequence_pair("AAAA", "AAA")


def test_position_qubit_count():
    assert position_qubit_count(4) == 2
    assert position_qubit_count(8) == 3
    assert position_qubit_count(5) == 3

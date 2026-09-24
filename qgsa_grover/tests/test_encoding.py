import pytest

from qgsa_grover.encoding import decode_base, encode_base, encode_sequence, normalize_sequence


def test_table_1_encoding():
    assert encode_base("A") == (0, 0)
    assert encode_base("C") == (0, 1)
    assert encode_base("G") == (1, 0)
    assert encode_base("T") == (1, 1)
    assert encode_sequence("ACGT") == [0, 0, 0, 1, 1, 0, 1, 1]
    assert decode_base("00") == "A"


def test_lowercase_normalization_and_invalid_symbols():
    assert normalize_sequence("acgt") == "ACGT"
    with pytest.raises(ValueError):
        normalize_sequence("ACNX")
    with pytest.raises(ValueError):
        normalize_sequence("")

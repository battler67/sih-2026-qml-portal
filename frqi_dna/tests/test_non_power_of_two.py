from math import isclose

from frqi_dna.src.analysis import compare_dna_frqi


def test_non_power_of_two_sequence_support():
    result = compare_dna_frqi("AAA", "AAT", shots=2048, seed=11)
    assert result.sequence_length == 3
    assert result.position_qubits == 2
    assert result.position_register_states == 4
    assert "valid positions" in result.non_power_of_two_strategy


def test_non_power_identical_not_biased_by_unused_state():
    result = compare_dna_frqi("AAA", "AAA", shots=512, seed=11)
    assert isclose(result.theoretical_p1, 0.0, abs_tol=1e-12)
    assert result.counts["1"] == 0

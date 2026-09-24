from math import isclose

from frqi_dna.src.analysis import compare_dna_frqi


def test_identical_sequences_theoretical_p1_zero():
    result = compare_dna_frqi("AAAA", "AAAA", shots=1024)
    assert isclose(result.theoretical_p1, 0.0, abs_tol=1e-12)
    assert isclose(result.theoretical_similarity, 1.0, abs_tol=1e-12)


def test_identical_sequences_shots_p1_zero_seeded():
    result = compare_dna_frqi("ACGT", "ACGT", shots=1024, seed=7)
    assert result.counts["1"] == 0
    assert result.p1 == 0.0
    assert result.similarity == 1.0

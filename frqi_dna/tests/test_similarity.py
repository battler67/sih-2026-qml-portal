from math import isclose, pi

from frqi_dna.src.analysis import classical_expected_p1, compare_dna_frqi


def test_table_2_a_vs_t_probability():
    expected = (1.0 - __import__("math").cos((pi - pi / 6) / 2.0)) / 2.0
    assert isclose(classical_expected_p1("A", "T"), expected, abs_tol=1e-12)
    assert isclose(expected, 0.37059047744873963, abs_tol=1e-12)


def test_shot_results_agree_with_statevector_within_tolerance():
    result = compare_dna_frqi("ACGT", "ACTT", shots=8000, seed=12345)
    assert result.absolute_error < 0.03


def test_structured_output_fields():
    result = compare_dna_frqi("ACGT", "ACTT", shots=256, seed=9)
    data = result.to_dict()
    for key in [
        "reference",
        "query",
        "counts",
        "p0",
        "p1",
        "similarity",
        "theoretical_p1",
        "circuit_metrics",
    ]:
        assert key in data


def test_reproducible_seeded_simulation():
    first = compare_dna_frqi("AAAA", "TTTT", shots=512, seed=2026)
    second = compare_dna_frqi("AAAA", "TTTT", shots=512, seed=2026)
    assert first.counts == second.counts

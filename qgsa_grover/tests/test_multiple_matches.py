from qgsa_grover import search_dna_qgsa


def test_longer_pattern_multiple_matches():
    result = search_dna_qgsa(
        target="ACGTACGT",
        pattern="CGT",
        shots=1024,
        iterations="auto",
        boundary_mode="boundary_safe",
        seed=13,
    )
    assert result.classical_match_positions == [1, 5]
    assert set(result.quantum_candidate_positions) == {1, 5}
    assert result.success_probability > 0.45

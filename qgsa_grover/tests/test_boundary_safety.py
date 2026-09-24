from qgsa_grover import search_dna_qgsa


def test_prevent_wraparound_false_match():
    result = search_dna_qgsa(target="AT", pattern="TA", shots=1024, iterations="auto", boundary_mode="boundary_safe")
    assert result.classical_match_positions == []
    assert result.matches_found is False
    assert result.quantum_candidate_positions == []

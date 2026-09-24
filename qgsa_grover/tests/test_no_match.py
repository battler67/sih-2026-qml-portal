from qgsa_grover import search_dna_qgsa


def test_no_match_does_not_invent_candidate():
    result = search_dna_qgsa(target="ACGT", pattern="AA", shots=1024, iterations="auto", boundary_mode="boundary_safe")
    assert result.classical_match_positions == []
    assert result.matches_found is False
    assert result.quantum_candidate_positions == []
    assert result.iterations_executed == 0

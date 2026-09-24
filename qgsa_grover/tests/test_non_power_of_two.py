from qgsa_grover import search_dna_qgsa


def test_non_power_of_two_boundary_safe():
    result = search_dna_qgsa(target="ACGTA", pattern="GTA", shots=1024, iterations="auto", boundary_mode="boundary_safe")
    assert result.classical_match_positions == [2]
    assert result.quantum_candidate_positions == [2]
    assert "100" in result.encoding.values()

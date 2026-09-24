from qgsa_grover import search_dna_qgsa


def test_paper_example_acgt_a_seeded():
    result = search_dna_qgsa(target="ACGT", pattern="A", shots=1024, iterations="paper", seed=7)
    assert result.classical_match_positions == [0]
    assert result.quantum_candidate_positions == [0]
    assert result.success_probability > 0.95
    assert result.matches_found is True
    assert result.index_qubits == 2

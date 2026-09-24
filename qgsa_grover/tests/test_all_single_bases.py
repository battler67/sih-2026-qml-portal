from qgsa_grover import search_dna_qgsa


def test_search_every_nucleotide():
    for base, pos in zip("ACGT", [0, 1, 2, 3]):
        result = search_dna_qgsa(target="ACGT", pattern=base, shots=1024, iterations="auto", seed=11)
        assert result.classical_match_positions == [pos]
        assert result.quantum_candidate_positions == [pos]
        assert result.success_probability > 0.95

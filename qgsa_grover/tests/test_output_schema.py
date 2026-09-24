from qgsa_grover import search_dna_qgsa


def test_output_schema_fields():
    result = search_dna_qgsa(target="AAAA", pattern="A", shots=1024, iterations="auto")
    data = result.to_dict()
    for key in [
        "target",
        "pattern",
        "encoding",
        "counts",
        "index_probabilities",
        "circuit_metrics",
        "transpiled_metrics",
        "timings",
    ]:
        assert key in data
    assert result.classical_match_positions == [0, 1, 2, 3]
    assert set(result.quantum_candidate_positions) == {0, 1, 2, 3}

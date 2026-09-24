from qgsa_grover import search_dna_qgsa


def test_seeded_simulation_reproducible():
    a = search_dna_qgsa(target="ACGT", pattern="A", shots=1024, iterations="auto", seed=42)
    b = search_dna_qgsa(target="ACGT", pattern="A", shots=1024, iterations="auto", seed=42)
    assert a.counts == b.counts

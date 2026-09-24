import pytest

from quantum_dna import analyze_sequences


@pytest.mark.parametrize(
    ("reference", "query", "expected"),
    [
        ("AAAA", "AAAA", []),
        ("AAAA", "AAAT", [3]),
        ("ACGT", "ACTT", [2]),
        ("ACGTACGT", "ATGTACAT", [1, 6]),
        ("ACGTA", "ATGTT", [1, 4]),
    ],
)
def test_required_detection_cases(reference, query, expected):
    result = analyze_sequences(reference, query, shots=2048, seed=77)
    assert [m.position_zero_based for m in result.mutations] == expected
    assert result.oracle_marked_positions_zero_based == expected
    assert result.measured_detected_positions_zero_based == expected
    assert result.similarity_percentage == pytest.approx(100 * (len(reference) - len(expected)) / len(reference))
    assert result.invalid_padded_probability < 0.03
    if expected and len(expected) < len(reference):
        assert all(m.probability > m.probability_before for m in result.mutations)
    if not expected:
        assert result.grover_iterations == 0


def test_seeded_simulation_is_deterministic():
    a = analyze_sequences("ACGTACGT", "ATGTACAT", shots=512, seed=9)
    b = analyze_sequences("ACGTACGT", "ATGTACAT", shots=512, seed=9)
    assert a.counts == b.counts


def test_structured_result_format():
    data = analyze_sequences("AAAA", "AAAT", shots=256).to_dict()
    assert data["mutations"][0]["substitution"] == "A->T"
    assert set(data["circuit_metrics"]) == {"logical_qubits", "depth", "size", "operation_counts"}


def test_all_mutated_is_safe():
    result = analyze_sequences("AAAA", "TTTT", shots=256)
    assert result.grover_iterations == 0
    assert "cannot improve" in result.amplification_status
    assert result.measured_detected_positions_zero_based == [0, 1, 2, 3]

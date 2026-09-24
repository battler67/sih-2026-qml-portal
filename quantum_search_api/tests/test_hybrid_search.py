from __future__ import annotations

import inspect

import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from quantum_search_api.services.ncbi.models import SearchRequest
from quantum_search_api.services.quantum.base import QuantumRunOptions
from quantum_search_api.services.quantum.hybrid_search import (
    HybridQuantumSearchEngine,
    append_mismatch_compute,
    build_fixed_point_schedule,
    build_hybrid_fixed_point_circuits,
)


def test_mismatch_predicate_truth_table_is_reversible_logic():
    for reference in range(4):
        for query in range(4):
            circuit = QuantumCircuit(7)
            for bit in range(2):
                if (reference >> bit) & 1:
                    circuit.x(bit)
                if (query >> bit) & 1:
                    circuit.x(2 + bit)
            append_mismatch_compute(
                circuit,
                list(circuit.qubits[0:2]),
                list(circuit.qubits[2:4]),
                list(circuit.qubits[4:6]),
                circuit.qubits[6],
            )
            probabilities = Statevector.from_instruction(circuit).probabilities([6])
            assert probabilities[int(reference != query)] == pytest.approx(1.0)


def test_fixed_point_schedule_depends_on_lower_bound_not_actual_m():
    schedule = build_fixed_point_schedule(1 / 8, delta=0.2)
    assert schedule.sequence_length % 2 == 1
    assert schedule.width <= 1 / 8
    assert schedule.predicate_queries == schedule.sequence_length - 1

    source = inspect.getsource(build_hybrid_fixed_point_circuits)
    assert "classical_mutations" not in source
    assert "mismatch_positions" not in source


def test_hybrid_circuit_and_engine_accept_more_than_thirty_two_bases():
    reference = "ACGT" * 8 + "A"
    query = reference[:-1] + "T"
    engine = HybridQuantumSearchEngine()

    engine.validate_request(query, reference)
    resource = engine.estimate_resources(len(query), len(reference))
    circuits = build_hybrid_fixed_point_circuits(reference, query)

    assert len(reference) == 33
    assert resource["estimatedLogicalQubits"] == 13
    assert circuits["measured"].num_qubits == 13


@pytest.mark.parametrize(
    ("reference", "query", "marked"),
    [
        ("AAAA", "AAAT", {3}),
        ("ACGT", "ACTT", {2}),
        ("ACGTA", "ATGTT", {1, 4}),
    ],
)
def test_fixed_point_amplification_localizes_coherent_mismatches(reference, query, marked):
    circuits = build_hybrid_fixed_point_circuits(reference, query, delta=0.2)
    unmeasured = circuits["unmeasured"]
    assert isinstance(unmeasured, QuantumCircuit)
    width = max(1, (len(reference) - 1).bit_length())
    probabilities = Statevector.from_instruction(unmeasured).probabilities(qargs=list(range(width)))
    marked_probability = sum(float(probabilities[index]) for index in marked)
    assert marked_probability >= 0.96


def test_no_mismatch_remains_uniform_and_does_not_invent_candidates():
    engine = HybridQuantumSearchEngine()
    result = engine.run(
        "ACGT",
        "ACGT",
        QuantumRunOptions(shots=2048, enable_classical_validation=False),
    )
    assert result["mismatchPositionsCalculatedClassically"] is False
    assert result["mismatchCountUsedForSchedule"] is False
    assert result["mismatchAmplificationScore"] == pytest.approx(0.0, abs=1e-10)
    assert result["measuredCandidateIndices"] == []


def test_hybrid_request_is_now_valid_and_engine_reports_unknown_m_metadata():
    request = SearchRequest(
        querySource="pasted",
        querySequence="AAAA",
        referenceSequence="AAAT",
        algorithm="hybrid",
        databaseScope="pasted_sequence",
        maxWindows=1,
        shots=1024,
        strand="forward",
    )
    assert request.algorithm.value == "hybrid"

    result = HybridQuantumSearchEngine().run(
        "AAAA",
        "AAAT",
        QuantumRunOptions(shots=1024, enable_classical_validation=False),
    )
    assert result["measuredCandidateIndices"] == [3]
    assert result["exactIndexProbabilities"]["3"] > 0.99
    assert result["lambdaLowerBound"] == pytest.approx(0.25)

import pytest

from quantum_search_api.services.ncbi.exceptions import NcbiUnavailableError
from quantum_search_api.services.ncbi.models import (
    RecordMetadata,
    SearchRequest,
    SequenceRecord,
)
from quantum_search_api.services.quantum.grover_adapter import GroverSearchEngine
from quantum_search_api.services.search.search_orchestrator import SearchOrchestrator


class DummyDatasetsProvider:
    called = False

    def search_records(self, request):
        self.called = True
        raise AssertionError("Resource estimation must not search NCBI metadata")

    def fetch_sequences(self, accessions, request=None):
        self.called = True
        raise AssertionError("Resource estimation must not download NCBI sequences")


class DummyEntrezProvider:
    def fetch_sequences(self, accessions, request=None):
        return [
            SequenceRecord(
                accession="NC_1",
                title="genomic DNA",
                sequence="ACGTACGT",
                sourceDatabase="NCBI Nucleotide",
            )
        ]


class PartialDatasetsProvider:
    def search_records(self, request):
        return [
            RecordMetadata(
                accession=f"GCF_{index}.1",
                title=f"assembly {index}",
                sourceDatabase="RefSeq",
                assemblyAccession=f"GCF_{index}.1",
            )
            for index in range(1, 4)
        ]

    def fetch_sequences(self, accessions, request=None):
        accession = accessions[0]
        if accession == "GCF_2.1":
            raise NcbiUnavailableError("simulated timeout")
        return [
            SequenceRecord(
                accession=accession,
                title=f"{accession} genomic DNA",
                sequence="A",
                sourceDatabase="NCBI Datasets Genome",
            )
        ]


class FailingDatasetsProvider(PartialDatasetsProvider):
    def fetch_sequences(self, accessions, request=None):
        raise NcbiUnavailableError("simulated timeout")


def test_estimate_local_fixture_has_algorithm_labeling():
    orchestrator = SearchOrchestrator(datasets_provider=DummyDatasetsProvider(), entrez_provider=DummyEntrezProvider())
    request = SearchRequest(
        querySource="pasted",
        querySequence="ACGT",
        algorithm="grover",
        databaseScope="uploaded_fasta",
        uploadedFasta=">demo\nACGTNNACGT\n",
        maxWindows=4,
        shots=16,
    )
    estimate = orchestrator.estimate(request)
    assert estimate.quantum_alphabet == "ACGT"
    assert estimate.accepted_windows == 4
    assert estimate.skipped_windows == 0
    assert estimate.estimate_mode == "metadata_only"
    assert estimate.estimated_simulation_seconds_max >= estimate.estimated_simulation_seconds_min
    assert estimate.estimated_end_to_end_seconds_max >= estimate.estimated_simulation_seconds_max


def test_estimate_accepts_long_fasta_inputs_and_uses_bounded_frqi_window():
    sequence = "ACGT" * 25_000
    orchestrator = SearchOrchestrator(
        datasets_provider=DummyDatasetsProvider(),
        entrez_provider=DummyEntrezProvider(),
    )
    request = SearchRequest(
        querySource="pasted",
        querySequence=f">query length=100000 seed=42\n{sequence}",
        referenceSequence=f">reference_sequence length=100000 seed=42\n{sequence}",
        algorithm="frqi",
        databaseScope="pasted_sequence",
        maxQueryLength=32,
        maxBasesPerRecord=100_000,
        maxTotalBases=100_000,
        maxWindows=1,
        shots=138,
        strand="forward",
    )

    estimate = orchestrator.estimate(request)

    assert estimate.input_query_length == 100_000
    assert estimate.quantum_window_length == 32
    assert estimate.input_truncated_for_quantum is True
    assert estimate.sampling_or_truncation is True
    assert estimate.estimated_logical_qubits == 7
    assert estimate.exceeds_simulator_limits is False
    assert estimate.hardware_eligible is True
    assert estimate.hardware_qubit_capacity == 156
    assert any("not a coherent comparison" in warning for warning in estimate.warnings)


def test_long_input_grover_hardware_button_is_gated_by_bounded_circuit_estimate():
    sequence = "ACGT" * 25_000
    orchestrator = SearchOrchestrator(
        datasets_provider=DummyDatasetsProvider(),
        entrez_provider=DummyEntrezProvider(),
    )
    request = SearchRequest(
        querySource="pasted",
        querySequence=sequence,
        referenceSequence=sequence,
        algorithm="grover",
        databaseScope="pasted_sequence",
        maxQueryLength=32,
        maxBasesPerRecord=100_000,
        maxTotalBases=100_000,
        maxWindows=1,
        shots=138,
        strand="forward",
    )

    estimate = orchestrator.estimate(request)

    assert estimate.input_query_length == 100_000
    assert estimate.quantum_window_length == 32
    assert estimate.estimated_logical_qubits == 197
    assert estimate.exceeds_simulator_limits is True
    assert estimate.hardware_eligible is False


def test_hybrid_direct_pair_over_thirty_two_bases_uses_resource_eligibility():
    sequence = "ACGT" * 8 + "A"
    orchestrator = SearchOrchestrator(
        datasets_provider=DummyDatasetsProvider(),
        entrez_provider=DummyEntrezProvider(),
    )
    request = SearchRequest(
        querySource="pasted",
        querySequence=sequence,
        referenceSequence=sequence,
        algorithm="hybrid",
        databaseScope="pasted_sequence",
        maxQueryLength=32,
        maxWindows=1,
        shots=138,
        strand="forward",
    )

    estimate = orchestrator.estimate(request)

    assert estimate.input_query_length == 33
    assert estimate.quantum_window_length == 33
    assert estimate.estimated_logical_qubits == 13
    assert estimate.exceeds_simulator_limits is False
    assert estimate.hardware_eligible is True
    assert not any("at most 32" in warning for warning in estimate.warnings)


def test_remote_estimate_does_not_call_ncbi_providers():
    datasets = DummyDatasetsProvider()
    orchestrator = SearchOrchestrator(
        datasets_provider=datasets,
        entrez_provider=DummyEntrezProvider(),
    )
    request = SearchRequest(
        querySource="pasted",
        querySequence="ACGT",
        algorithm="frqi",
        databaseScope="taxonomy_assemblies",
        taxId="9606",
        maxRecords=25,
        maxWindows=50,
        shots=512,
    )
    estimate = orchestrator.estimate(request)
    assert datasets.called is False
    assert estimate.record_count == 25
    assert estimate.accepted_windows == 50
    assert "no NCBI records" in estimate.warnings[0]


def test_manual_reference_sequence_remains_distinct_from_query():
    orchestrator = SearchOrchestrator(
        datasets_provider=DummyDatasetsProvider(),
        entrez_provider=DummyEntrezProvider(),
    )
    request = SearchRequest(
        querySource="pasted",
        querySequence="ACGT",
        referenceSequence="TTACGTGG",
        algorithm="frqi",
        databaseScope="pasted_sequence",
        maxWindows=5,
        shots=32,
        strand="forward",
    )
    result = orchestrator.run(request, job_id="manual-reference")
    assert result["query"]["sequence"] == "ACGT"
    assert any(hit["matchedWindow"] == "ACGT" for hit in result["hits"])
    assert result["reference"]["source"] == "User-pasted reference DNA"
    assert result["reference"]["sequencePreview"] == result["hits"][0]["matchedWindow"][:10]


def test_pasted_reference_scope_requires_reference_sequence():
    with pytest.raises(ValueError, match="referenceSequence is required"):
        SearchRequest(
            querySource="pasted",
            querySequence="ACGT",
            algorithm="frqi",
            databaseScope="pasted_sequence",
        )


def test_search_continues_with_records_fetched_before_timeout():
    orchestrator = SearchOrchestrator(
        datasets_provider=PartialDatasetsProvider(),
        entrez_provider=DummyEntrezProvider(),
    )
    request = SearchRequest(
        querySource="pasted",
        querySequence="A",
        algorithm="frqi",
        databaseScope="taxonomy_assemblies",
        taxId="9606",
        maxRecords=3,
        maxWindows=2,
        shots=16,
        strand="forward",
    )
    result = orchestrator.run(request, job_id="partial")
    assert len(result["hits"]) == 2
    assert result["retrieval"]["partial"] is True
    assert result["retrieval"]["failedRecords"] == 1
    assert "Partial NCBI retrieval" in result["warnings"][0]
    assert "GCF_2.1" in result["warnings"][0]


def test_search_fails_only_when_no_usable_ncbi_record_was_fetched():
    orchestrator = SearchOrchestrator(
        datasets_provider=FailingDatasetsProvider(),
        entrez_provider=DummyEntrezProvider(),
    )
    request = SearchRequest(
        querySource="pasted",
        querySequence="A",
        algorithm="frqi",
        databaseScope="taxonomy_assemblies",
        taxId="9606",
        maxRecords=3,
        maxWindows=1,
        shots=16,
        strand="forward",
    )
    with pytest.raises(NcbiUnavailableError, match="none produced usable genomic DNA"):
        orchestrator.run(request, job_id="empty")


def test_grover_result_preserves_quantum_and_defers_validation():
    orchestrator = SearchOrchestrator(datasets_provider=DummyDatasetsProvider(), entrez_provider=DummyEntrezProvider())
    request = SearchRequest(
        querySource="pasted",
        querySequence="A",
        algorithm="grover",
        databaseScope="uploaded_fasta",
        uploadedFasta=">demo\nA\n",
        maxWindows=1,
        shots=32,
        strand="forward",
    )
    progress = []
    result = orchestrator.run(
        request,
        job_id="demo",
        progress_callback=lambda status, message, percent: progress.append(
            (status, message, percent)
        ),
    )
    assert result["algorithm"] == "grover"
    assert result["quantumAlphabet"] == "ACGT"
    assert result["hits"][0]["algorithm"] == "grover"
    assert result["hits"][0]["classicalValidation"] is None
    assert result["pipeline"]["validation"] == "disabled"
    assert [item[0] for item in progress] == [
        "retrieving_records",
        "preprocessing",
        "estimating_resources",
        "building_circuit",
        "simulating",
    ]


def test_frqi_adapter_invocation_through_orchestrator():
    orchestrator = SearchOrchestrator(datasets_provider=DummyDatasetsProvider(), entrez_provider=DummyEntrezProvider())
    request = SearchRequest(
        querySource="pasted",
        querySequence="A",
        algorithm="frqi",
        databaseScope="uploaded_fasta",
        uploadedFasta=">demo\nA\n",
        maxWindows=1,
        shots=32,
        strand="forward",
    )
    result = orchestrator.run(request, job_id="frqi")
    assert result["algorithm"] == "frqi"
    assert "stripQubitProbability" in result["hits"][0]["quantumDetails"]


def test_hybrid_adapter_invocation_through_orchestrator():
    orchestrator = SearchOrchestrator(datasets_provider=DummyDatasetsProvider(), entrez_provider=DummyEntrezProvider())
    request = SearchRequest(
        querySource="pasted",
        querySequence="AAAA",
        referenceSequence="AAAT",
        algorithm="hybrid",
        databaseScope="pasted_sequence",
        maxWindows=8,
        shots=1024,
        strand="forward",
    )
    estimate = orchestrator.estimate(request)
    assert estimate.estimated_grover_iterations == 2
    assert estimate.estimated_quantum_runs == 1
    result = orchestrator.run(request, job_id="hybrid")
    details = result["hits"][0]["quantumDetails"]
    assert result["algorithm"] == "hybrid"
    assert "windowSelection" not in result
    assert result["quantumMetrics"]["windowsProcessed"] == 0
    assert result["quantumMetrics"]["sequenceComparisons"] == 1
    assert details["measuredCandidateIndices"] == [3]
    assert details["mismatchCountUsedForSchedule"] is False


def test_hybrid_request_requires_equal_length_pasted_sequences():
    with pytest.raises(ValueError, match="equal-length"):
        SearchRequest(
            querySource="pasted",
            querySequence="AAAA",
            referenceSequence="AAA",
            algorithm="hybrid",
            databaseScope="pasted_sequence",
        )


def test_grover_rejects_oversized_simulator_request():
    engine = GroverSearchEngine()
    try:
        engine.validate_request("A" * 11, "A" * 11)
    except ValueError as exc:
        assert "exceeds the local Aer simulator limit" in str(exc)
    else:
        raise AssertionError("Expected oversized Grover request to be rejected")


def test_grover_paper_cyclic_uses_two_bit_resource_estimate():
    engine = GroverSearchEngine()
    boundary_safe = engine.estimate_resources(4, 4, boundary_mode="boundary_safe")
    paper_cyclic = engine.estimate_resources(4, 4, boundary_mode="paper_cyclic")

    assert boundary_safe["estimatedLogicalQubits"] == 26
    assert paper_cyclic["estimatedLogicalQubits"] == 18
    assert "2-bit" in paper_cyclic["notes"][1]

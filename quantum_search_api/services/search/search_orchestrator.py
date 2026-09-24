from __future__ import annotations

import time
from math import ceil
from typing import Callable

from quantum_search_api.services.ncbi.datasets_provider import NcbiDatasetsProvider
from quantum_search_api.services.ncbi.entrez_provider import NcbiEntrezProvider
from quantum_search_api.services.ncbi.exceptions import (
    NcbiError,
    NcbiUnavailableError,
    NcbiValidationError,
)
from quantum_search_api.services.ncbi.models import (
    Algorithm,
    DatabaseScope,
    RetrievalSummary,
    SearchEstimate,
    SearchRequest,
    SequenceRecord,
    WindowRecord,
)
from quantum_search_api.services.quantum.base import QuantumRunOptions
from quantum_search_api.services.quantum.frqi_adapter import FrqiSearchEngine
from quantum_search_api.services.quantum.grover_adapter import MAX_AER_QUBITS, GroverSearchEngine
from quantum_search_api.services.quantum.hybrid_search import HybridQuantumSearchEngine
from quantum_search_api.services.quantum.result_mapper import map_hit, result_shell
from quantum_search_api.services.search.local_providers import PastedSequenceProvider, UploadedFastaProvider
from quantum_search_api.services.search.ranking_service import rank_hits
from quantum_search_api.services.search.validation_service import validate_exact, validate_hit_against_records
from quantum_search_api.services.sequence.normalizer import (
    MAX_INPUT_SEQUENCE_LENGTH,
    NormalizedSequence,
    bound_normalized_sequence,
    normalize_query_input,
)
from quantum_search_api.services.sequence.window_generator import generate_windows


LARGE_SCOPE_WARNING = (
    "Large database searches use staged retrieval and bounded quantum processing. "
    "The entire GenBank database is not loaded into the quantum circuit."
)
MAX_CONSECUTIVE_NCBI_FAILURES = 3
HARDWARE_ESTIMATE_QUBIT_CAPACITY = 156


class SearchOrchestrator:
    def __init__(
        self,
        *,
        datasets_provider: NcbiDatasetsProvider | None = None,
        entrez_provider: NcbiEntrezProvider | None = None,
    ) -> None:
        self.datasets_provider = datasets_provider or NcbiDatasetsProvider()
        self.entrez_provider = entrez_provider or NcbiEntrezProvider()
        self.uploaded_provider = UploadedFastaProvider()
        self.pasted_provider = PastedSequenceProvider()
        self.frqi = FrqiSearchEngine()
        self.grover = GroverSearchEngine()
        self.hybrid = HybridQuantumSearchEngine()

    def _engine(self, algorithm: Algorithm):
        if algorithm == Algorithm.grover:
            return self.grover
        if algorithm == Algorithm.hybrid:
            return self.hybrid
        return self.frqi

    def estimate(self, request: SearchRequest) -> SearchEstimate:
        query_length, input_query_length, query_warning = (
            self._estimate_query_length(request)
        )
        engine = self._engine(request.algorithm)
        resource = (
            self.grover.estimate_resources(
                query_length,
                query_length,
                boundary_mode=request.grover_boundary_mode,
            )
            if request.algorithm == Algorithm.grover
            else engine.estimate_resources(query_length, query_length)
        )
        direct_hybrid = request.algorithm == Algorithm.hybrid
        record_cap = 1 if direct_hybrid else request.max_records
        base_cap = (
            query_length
            if direct_hybrid
            else min(
                request.max_total_bases,
                request.max_records * request.max_bases_per_record,
            )
        )
        run_cap = 1 if direct_hybrid else request.max_windows
        warnings = [
            (
                "Hybrid compares the pasted equal-length query and reference directly in one "
                "quantum circuit; sliding windows are not generated."
                if direct_hybrid
                else "Metadata-only estimate: no NCBI records or genomic FASTA files were fetched. "
                "Record, base, window, run, and shot values are configured upper bounds."
            )
        ]
        if query_warning:
            warnings.append(query_warning)
        if request.max_records > 10 or request.max_total_bases > 50000:
            warnings.append(LARGE_SCOPE_WARNING)
        exceeds = (
            request.algorithm in {Algorithm.grover, Algorithm.hybrid}
            and resource["estimatedLogicalQubits"] > MAX_AER_QUBITS
        )
        hardware_eligible = (
            resource["estimatedLogicalQubits"] <= HARDWARE_ESTIMATE_QUBIT_CAPACITY
        )
        if (
            request.algorithm == Algorithm.grover
            and resource["estimatedLogicalQubits"] > MAX_AER_QUBITS
        ):
            warnings.append(
                "Grover/QGSA exact-pattern search exceeds the local Aer simulator qubit limit. "
                "Use a shorter query/window or select FRQI similarity."
            )
        if not hardware_eligible:
            warnings.append(
                "The bounded circuit is not eligible for the 156-qubit hardware "
                "planning capacity. Live device discovery remains authoritative."
            )
        runtime = self._estimate_runtime(
            request,
            query_length=query_length,
            quantum_runs=run_cap,
            grover_iterations=int(resource["estimatedGroverIterations"]),
        )
        return SearchEstimate(
            inputQueryLength=input_query_length,
            quantumWindowLength=query_length,
            inputTruncatedForQuantum=input_query_length > query_length,
            recordCount=record_cap,
            totalBases=base_cap,
            totalWindows=run_cap,
            acceptedWindows=run_cap,
            skippedWindows=0,
            ambiguousBases=0,
            estimatedQuantumRuns=run_cap,
            estimatedShots=run_cap * request.shots,
            estimatedLogicalQubits=resource["estimatedLogicalQubits"],
            estimatedGroverIterations=resource["estimatedGroverIterations"]
            if request.algorithm in {Algorithm.grover, Algorithm.hybrid}
            else 0,
            exceedsSimulatorLimits=exceeds,
            hardwareEligible=hardware_eligible,
            hardwareQubitCapacity=HARDWARE_ESTIMATE_QUBIT_CAPACITY,
            hardwareEligibilityNote=(
                "Eligible by the logical-qubit planning count. "
                "Live provider access, topology, depth, and transpilation remain authoritative."
                if hardware_eligible
                else (
                    "Ineligible by the logical-qubit planning count. "
                    "Reduce the input length or choose another algorithm."
                )
            ),
            samplingOrTruncation=input_query_length > query_length,
            warnings=warnings,
            estimatedSimulationSecondsMin=runtime["simulation_min"],
            estimatedSimulationSecondsMax=runtime["simulation_max"],
            estimatedEndToEndSecondsMin=runtime["end_to_end_min"],
            estimatedEndToEndSecondsMax=runtime["end_to_end_max"],
            runtimeEstimateNote=(
                "Planning range only. Simulation varies by circuit complexity and computer speed; "
                "end-to-end time also includes an allowance for NCBI network and download latency."
            ),
        )

    def _estimate_query_length(
        self,
        request: SearchRequest,
    ) -> tuple[int, int, str | None]:
        if request.query_source.value == "ncbi_accession":
            return (
                request.max_query_length,
                request.max_query_length,
                "The NCBI query accession was not fetched; resource calculations use "
                f"the configured maximum query length of {request.max_query_length}.",
            )
        query, full_query = self._normalize_bounded_query(request)
        warning = self._bounded_query_warning(full_query.length, query.length)
        return query.length, full_query.length, warning

    def _normalize_bounded_query(
        self,
        request: SearchRequest,
    ) -> tuple[NormalizedSequence, NormalizedSequence]:
        full_query = normalize_query_input(
            self._query_text(request),
            is_fasta=request.query_source.value == "uploaded_fasta",
            max_length=MAX_INPUT_SEQUENCE_LENGTH,
        )
        if request.algorithm == Algorithm.hybrid:
            return full_query, full_query
        return (
            bound_normalized_sequence(
                full_query,
                max_length=request.max_query_length,
            ),
            full_query,
        )

    @staticmethod
    def _bounded_query_warning(
        input_length: int,
        quantum_length: int,
    ) -> str | None:
        if input_length <= quantum_length:
            return None
        return (
            f"The input query contains {input_length} bases; only the leading "
            f"{quantum_length}-base bounded window is compiled into each quantum "
            "circuit. This is not a coherent comparison of the complete input query."
        )

    def _estimate_runtime(
        self,
        request: SearchRequest,
        *,
        query_length: int,
        quantum_runs: int,
        grover_iterations: int,
    ) -> dict[str, int]:
        shot_factor = max(0.1, request.shots / 1024.0)
        if request.algorithm == Algorithm.grover:
            seconds_per_run = (
                0.12
                * max(1, grover_iterations + 1)
                * (1.35 ** min(query_length, 24))
                * shot_factor
            )
        elif request.algorithm == Algorithm.hybrid:
            seconds_per_run = (
                0.08
                * max(1, grover_iterations + 1)
                * (1.22 ** min(query_length, 32))
                * shot_factor
            )
        else:
            seconds_per_run = (0.06 + 0.015 * query_length) * shot_factor
        simulation = max(1.0, seconds_per_run * quantum_runs)
        simulation_min = max(1, int(simulation * 0.5))
        simulation_max = max(simulation_min, ceil(simulation * 3.0))

        if request.database_scope in {
            DatabaseScope.uploaded_fasta,
            DatabaseScope.pasted_sequence,
        }:
            retrieval_min, retrieval_max = 0, 1
        elif request.database_scope == DatabaseScope.exact_genomic_nucleotide:
            count = max(1, len(request.nucleotide_accessions))
            retrieval_min, retrieval_max = 2, 10 + 5 * count
        else:
            retrieval_min = 5
            retrieval_max = 30 + 20 * request.max_records
        if request.query_source.value == "ncbi_accession":
            retrieval_min += 2
            retrieval_max += 20
        return {
            "simulation_min": simulation_min,
            "simulation_max": simulation_max,
            "end_to_end_min": simulation_min + retrieval_min,
            "end_to_end_max": simulation_max + retrieval_max,
        }

    def run(
        self,
        request: SearchRequest,
        *,
        job_id: str = "",
        progress_callback: Callable[[str, str, int], None] | None = None,
    ) -> dict:
        def report(status: str, message: str, percent: int) -> None:
            if progress_callback is not None:
                progress_callback(status, message, percent)

        report("retrieving_records", "Discovering genomic records", 10)
        records, retrieval_warnings, retrieval_details = self._retrieve_records_incrementally(
            request,
            progress_callback=report,
        )
        report("preprocessing", "Normalizing query and genomic sequences", 25)
        query, full_query = self._normalize_bounded_query(request)
        direct_hybrid = request.algorithm == Algorithm.hybrid
        report(
            "estimating_resources",
            "Preparing equal-length sequence comparison"
            if direct_hybrid
            else "Generating bounded genomic windows",
            40,
        )
        if direct_hybrid:
            record = records[0]
            engine = self._engine(request.algorithm)
            engine.validate_request(query.sequence, record.sequence)
            windows = [
                WindowRecord(
                    accession=record.accession,
                    recordTitle=record.title,
                    organism=record.organism,
                    taxId=record.tax_id,
                    sourceDatabase=record.source_database,
                    chromosome=record.chromosome,
                    strand="forward",
                    startZeroBased=0,
                    endZeroBased=len(record.sequence),
                    sequence=record.sequence,
                )
            ]
            generated = None
        else:
            generated = generate_windows(
                records,
                query_length=query.length,
                stride=request.window_stride,
                strand=request.strand,
                max_windows=request.max_windows,
                max_bases_per_record=request.max_bases_per_record,
                max_total_bases=request.max_total_bases,
            )
            windows = generated.windows
        if not windows:
            raise NcbiValidationError("No ACGT-compatible genomic windows were available for quantum processing")
        engine = self._engine(request.algorithm)
        resource = (
            self.grover.estimate_resources(query.length, query.length, boundary_mode=request.grover_boundary_mode)
            if request.algorithm == Algorithm.grover
            else engine.estimate_resources(query.length, query.length)
        )
        if request.algorithm == Algorithm.grover and resource["estimatedLogicalQubits"] > MAX_AER_QUBITS:
            raise ValueError(
                "Grover/QGSA exact-pattern circuit requires "
                f"{resource['estimatedLogicalQubits']} logical qubits for this query/window, "
                f"which exceeds the local Aer simulator limit of {MAX_AER_QUBITS}. "
                "Use a shorter query/window or select FRQI similarity."
            )
        report("building_circuit", "Building selected quantum circuits", 60)
        retrieval = RetrievalSummary(
            provider=self._provider_label(request.database_scope),
            recordCount=len(records),
            totalBases=sum(min(len(record.sequence), request.max_bases_per_record) for record in records),
        ).model_dump(by_alias=True)
        retrieval.update(retrieval_details)
        warnings = [*retrieval_warnings]
        if direct_hybrid:
            warnings.append(
                "Hybrid compared the pasted equal-length sequences directly; no sliding windows "
                "or classically supplied mismatch positions were used."
            )
            truncated = False
        else:
            assert generated is not None
            warnings.extend(
                [
                    *generated.summary.warnings,
                    f"Ambiguous bases: {generated.summary.ambiguous_bases}; total windows: {generated.summary.total_windows}; "
                    f"accepted windows: {generated.summary.accepted_windows}; skipped windows: {generated.summary.skipped_windows}",
                ]
            )
            truncated = generated.summary.truncated
        query_warning = self._bounded_query_warning(full_query.length, query.length)
        if query_warning:
            warnings.append(query_warning)
        if request.max_records > 10 or request.max_total_bases > 50000:
            warnings.append(LARGE_SCOPE_WARNING)
        shell = result_shell(
            request,
            query.sequence,
            retrieval,
            warnings,
            {"occurred": truncated, "reason": "configured bounds" if truncated else None},
        )
        shell["jobId"] = job_id
        shell["query"].update(
            {
                "inputLength": full_query.length,
                "quantumWindowLength": query.length,
                "inputTruncatedForQuantum": full_query.length > query.length,
            }
        )
        if not direct_hybrid:
            assert generated is not None
            shell["windowSelection"] = {
                "mode": "first_valid_sliding_windows",
                "description": (
                    "Target sequences are normalized to ACGT-compatible genomic windows, scanned by coordinate order, "
                    "bounded by maxWindows, quantum-scored, then ranked by quantumScore."
                ),
                "requestedMaxWindows": request.max_windows,
                "acceptedWindows": generated.summary.accepted_windows,
                "processedWindows": generated.summary.accepted_windows,
                "windowStride": request.window_stride,
                "strand": request.strand,
                "ranking": "quantumScore descending after bounded window processing",
            }
        options = QuantumRunOptions(
            shots=request.shots,
            simulator=request.simulator,
            enable_classical_validation=request.enable_classical_validation,
            grover_boundary_mode=request.grover_boundary_mode,
        )
        hits: list[dict] = []
        aggregate_counts: dict[str, int] = {}
        quantum_execution_seconds = 0.0
        report("simulating", "Running AerSimulator", 80)
        for window in windows:
            started = time.perf_counter()
            quantum = engine.run(query.sequence, window.sequence, options)
            quantum_execution_seconds += time.perf_counter() - started
            validation = validate_exact(query.sequence, window.sequence) if request.enable_classical_validation else None
            hit = map_hit(0, window, query.sequence, quantum, validation)
            hits.append(hit)
            for key, count in quantum.get("counts", {}).items():
                aggregate_counts[key] = aggregate_counts.get(key, 0) + int(count)
        shell["hits"] = rank_hits(hits)
        top_hit = shell["hits"][0] if shell["hits"] else None
        if top_hit:
            matched_window = str(top_hit.get("matchedWindow") or "")
            shell["reference"] = {
                "source": self._reference_source_label(request.database_scope),
                "scope": request.database_scope.value,
                "sequencePreview": matched_window[:10],
                "windowLength": len(matched_window),
                "accession": top_hit.get("accession"),
                "coordinates": None
                if direct_hybrid
                else f"{top_hit.get('start')}-{top_hit.get('end')}",
                "selectionMethod": (
                    "The backend compared the complete pasted reference directly with the "
                    "equal-length pasted query in one Hybrid circuit."
                    if direct_hybrid
                    else "The backend generated bounded A/C/G/T windows from the selected reference "
                    "source, ran the chosen quantum circuit on accepted windows, and this is the "
                    "top-ranked processed window. It is not the complete genome sequence."
                ),
            }
        shell["quantumMetrics"] = {
            "algorithm": request.algorithm.value,
            "quantumAlphabet": "ACGT",
            "windowsProcessed": 0 if direct_hybrid else len(hits),
            "sequenceComparisons": 1 if direct_hybrid else None,
            "windowSelectionMode": (
                "not_applicable_direct_equal_length_comparison"
                if direct_hybrid
                else "first_valid_sliding_windows_then_quantum_score_ranking"
            ),
            "groverBoundaryMode": request.grover_boundary_mode,
            "quantumExecutionSeconds": quantum_execution_seconds,
            "shotsPerRun": request.shots,
            "aggregateCounts": aggregate_counts,
            "algorithmLabel": f"{request.algorithm.value} quantum simulator",
        }
        return shell

    def _retrieve_records_incrementally(
        self,
        request: SearchRequest,
        *,
        progress_callback: Callable[[str, str, int], None] | None = None,
    ) -> tuple[list[SequenceRecord], list[str], dict[str, int | bool]]:
        if request.database_scope in {
            DatabaseScope.uploaded_fasta,
            DatabaseScope.pasted_sequence,
        }:
            records = self._retrieve_records(request)
            return records, [], {
                "requestedRecords": min(request.max_records, len(records)),
                "failedRecords": 0,
                "partial": False,
            }

        if request.database_scope == DatabaseScope.exact_genomic_nucleotide:
            accessions = request.nucleotide_accessions[: request.max_records]
            provider = self.entrez_provider
        elif request.database_scope == DatabaseScope.gene_on_assembly:
            raise NcbiValidationError(
                "Gene-on-assembly resolution is modeled but external gene-region retrieval is disabled in this pass"
            )
        else:
            metadata = self.datasets_provider.search_records(request)
            accessions = [
                item.assembly_accession or item.accession
                for item in metadata[: request.max_records]
            ]
            provider = self.datasets_provider

        records: list[SequenceRecord] = []
        failures: list[tuple[str, str]] = []
        consecutive_failures = 0
        processed_bases = 0
        attempted = 0
        total = len(accessions)
        for accession in accessions:
            attempted += 1
            try:
                fetched = provider.fetch_sequences([accession], request)
                if not fetched:
                    raise NcbiValidationError("record returned no genomic sequence")
                records.extend(fetched)
                processed_bases += sum(
                    min(len(record.sequence), request.max_bases_per_record)
                    for record in fetched
                )
                consecutive_failures = 0
            except NcbiError as exc:
                failures.append((accession, str(exc)))
                consecutive_failures += 1
            if progress_callback is not None:
                percent = 10 + int(14 * attempted / max(1, total))
                progress_callback(
                    "retrieving_records",
                    f"Retrieved {len(records)} usable record(s); checked {attempted}/{total}",
                    percent,
                )
            if processed_bases >= request.max_total_bases:
                break
            if consecutive_failures >= MAX_CONSECUTIVE_NCBI_FAILURES:
                break

        if not records:
            detail = (
                f"Attempted {attempted} NCBI record download(s), but none produced usable genomic DNA."
            )
            if failures:
                failed_names = ", ".join(accession for accession, _ in failures)
                detail += f" Failed accessions: {failed_names}."
            raise NcbiUnavailableError(detail)

        warnings: list[str] = []
        if failures or attempted < total:
            failed_names = ", ".join(accession for accession, _ in failures)
            warning = (
                f"Partial NCBI retrieval: continued with {len(records)} usable record(s) "
                f"after checking {attempted} of {total} candidate accession(s)."
            )
            if failed_names:
                warning += f" Skipped: {failed_names}."
            if consecutive_failures >= MAX_CONSECUTIVE_NCBI_FAILURES:
                warning += (
                    f" Retrieval stopped after {MAX_CONSECUTIVE_NCBI_FAILURES} consecutive failures."
                )
            elif processed_bases >= request.max_total_bases:
                warning += " Retrieval stopped after satisfying the configured total-base cap."
            warnings.append(warning)
        return records, warnings, {
            "requestedRecords": total,
            "attemptedRecords": attempted,
            "failedRecords": len(failures),
            "partial": bool(failures or attempted < total),
        }

    def validate_result_candidates(self, request: SearchRequest, result: dict) -> dict:
        query, _full_query = self._normalize_bounded_query(request)
        records = self._retrieve_records(request)
        hits = result.get("hits", [])
        for hit in hits:
            validation = validate_hit_against_records(
                query.sequence,
                hit,
                records,
                max_bases_per_record=request.max_bases_per_record,
                max_total_bases=request.max_total_bases,
            )
            original_window = str(hit.get("matchedWindow") or "")
            validated_window = str(validation.get("validatedWindow") or "")
            if validated_window:
                hit["matchedWindow"] = validated_window
            if original_window and original_window != validated_window:
                hit["quantumProcessedWindow"] = original_window
            hit["querySequence"] = query.sequence
            hit["classicalValidation"] = validation
        result.setdefault("query", {})["sequence"] = query.sequence
        result.setdefault("pipeline", {})["validation"] = "classical_exact_match_on_source_sequence"
        result.setdefault("quantumMetrics", {})["validatedCandidates"] = len(hits)
        result.setdefault("quantumMetrics", {})["validationMode"] = "source_sequence_coordinate_accuracy_checker"
        return result

    def _query_text(self, request: SearchRequest) -> str:
        if request.query_source.value == "uploaded_fasta":
            return request.uploaded_fasta or ""
        if request.query_source.value == "ncbi_accession":
            query_request = request.model_copy(
                update={
                    "database_scope": DatabaseScope.exact_genomic_nucleotide,
                    "nucleotide_accessions": [request.query_accession] if request.query_accession else [],
                }
            )
            records = self.entrez_provider.fetch_sequences([request.query_accession or ""], query_request)
            if not records:
                raise NcbiValidationError("Query accession did not return genomic DNA")
            return records[0].sequence
        return request.query_sequence or ""

    def _retrieve_records(self, request: SearchRequest) -> list[SequenceRecord]:
        if request.database_scope == DatabaseScope.uploaded_fasta:
            return self.uploaded_provider.fetch_sequences([], request)[: request.max_records]
        if request.database_scope == DatabaseScope.pasted_sequence:
            return self.pasted_provider.fetch_sequences([], request)[: request.max_records]
        if request.database_scope == DatabaseScope.exact_genomic_nucleotide:
            return self.entrez_provider.fetch_sequences(request.nucleotide_accessions, request)[: request.max_records]
        if request.database_scope == DatabaseScope.gene_on_assembly:
            raise NcbiValidationError("Gene-on-assembly resolution is modeled but external gene-region retrieval is disabled in this pass")
        metadata = self.datasets_provider.search_records(request)
        accessions = [item.assembly_accession or item.accession for item in metadata]
        return self.datasets_provider.fetch_sequences(accessions[: request.max_records], request)

    def _provider_label(self, scope: DatabaseScope) -> str:
        if scope in {DatabaseScope.uploaded_fasta, DatabaseScope.pasted_sequence}:
            return "Local genomic DNA"
        if scope == DatabaseScope.exact_genomic_nucleotide:
            return "NCBI Entrez Nucleotide genomic DNA"
        return "NCBI Datasets Genome"

    def _reference_source_label(self, scope: DatabaseScope) -> str:
        if scope == DatabaseScope.pasted_sequence:
            return "User-pasted reference DNA"
        if scope == DatabaseScope.uploaded_fasta:
            return "Uploaded reference FASTA"
        if scope == DatabaseScope.taxonomy_assemblies:
            return "NCBI assemblies selected by taxonomy ID"
        if scope == DatabaseScope.organism_assemblies:
            return "NCBI assemblies selected by organism"
        if scope == DatabaseScope.exact_genomic_nucleotide:
            return "Exact NCBI genomic nucleotide accession"
        if scope == DatabaseScope.exact_assembly:
            return "Exact NCBI genome assembly"
        return "NCBI genomic assembly reference set"

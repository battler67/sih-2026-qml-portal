from __future__ import annotations

from typing import Any

from frqi_dna.src.comparison_circuit import build_measured_comparison_circuit
from qgsa_grover.qgsa import build_qgsa_circuit
from qiskit import QuantumCircuit

from quantum_search_api.services.hardware.models import PreparedHardwareCircuit
from quantum_search_api.services.ncbi.models import Algorithm, RetrievalSummary, SearchRequest
from quantum_search_api.services.quantum.hybrid_search import (
    build_hybrid_fixed_point_circuits,
)
from quantum_search_api.services.search.search_orchestrator import SearchOrchestrator
from quantum_search_api.services.sequence.window_generator import generate_windows


class HardwareCircuitService:
    """Prepare one representative circuit without running the Aer pipeline."""

    def __init__(self, orchestrator: SearchOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or SearchOrchestrator()

    def prepare(self, request: SearchRequest) -> PreparedHardwareCircuit:
        records, retrieval_warnings, retrieval_details = (
            self.orchestrator._retrieve_records_incrementally(request)
        )
        query, full_query = self.orchestrator._normalize_bounded_query(request)
        generated = generate_windows(
            records,
            query_length=query.length,
            stride=request.window_stride,
            strand=request.strand,
            max_windows=1,
            max_bases_per_record=request.max_bases_per_record,
            max_total_bases=request.max_total_bases,
        )
        if not generated.windows:
            raise ValueError(
                "No A/C/G/T-compatible genomic window was available for hardware execution"
            )

        window = generated.windows[0]
        circuit, classical_register, builder_warnings = self._build_circuit(
            request=request,
            query=query.sequence,
            window=window.sequence,
        )
        retrieval = RetrievalSummary(
            provider=self.orchestrator._provider_label(request.database_scope),
            recordCount=len(records),
            totalBases=sum(
                min(len(record.sequence), request.max_bases_per_record)
                for record in records
            ),
        ).model_dump(by_alias=True)
        retrieval.update(retrieval_details)
        window_metadata: dict[str, Any] = {
            "accession": window.accession,
            "recordTitle": window.record_title,
            "organism": window.organism,
            "taxId": window.tax_id,
            "sourceDatabase": window.source_database,
            "chromosome": window.chromosome,
            "strand": window.strand,
            "start": window.start_zero_based,
            "end": window.end_zero_based,
            "sequence": window.sequence,
            "selectionMethod": (
                "First accepted A/C/G/T-only bounded window after the configured "
                "retrieval, strand, stride, and sequence limits; no Aer pre-ranking."
            ),
        }
        warnings = [
            *retrieval_warnings,
            *generated.summary.warnings,
            *builder_warnings,
        ]
        query_warning = self.orchestrator._bounded_query_warning(
            full_query.length,
            query.length,
        )
        if query_warning:
            warnings.append(query_warning)
        warnings.append(
            "Real-hardware mode submits one representative bounded window "
            "per click to protect provider quotas."
        )
        return PreparedHardwareCircuit(
            circuit=circuit,
            algorithm=request.algorithm.value,
            classical_register=classical_register,
            query_sequence=query.sequence,
            window_sequence=window.sequence,
            window_metadata=window_metadata,
            retrieval_metadata=retrieval,
            warnings=tuple(warnings),
        )

    def _build_circuit(
        self,
        *,
        request: SearchRequest,
        query: str,
        window: str,
    ) -> tuple[QuantumCircuit, str, list[str]]:
        if request.algorithm == Algorithm.frqi:
            return (
                build_measured_comparison_circuit(window, query),
                "c",
                [
                    "FRQI hardware counts measure the strip qubit; P(1) indicates "
                    "encoded branch difference rather than an alignment position."
                ],
            )
        if request.algorithm == Algorithm.hybrid:
            circuits = build_hybrid_fixed_point_circuits(window, query)
            measured = circuits["measured"]
            if not isinstance(measured, QuantumCircuit):
                raise TypeError("Hybrid circuit builder did not return a measured circuit")
            return (
                measured,
                "c_pos",
                [
                    "Hybrid hardware counts are raw position-register samples from "
                    "fixed-point mismatch amplification."
                ],
            )

        measured, metadata = build_qgsa_circuit(
            target=window,
            pattern=query,
            iterations="auto",
            boundary_mode=request.grover_boundary_mode,
            measured=True,
        )
        warnings = [str(item) for item in metadata.get("warnings", [])]
        warnings.append(
            "Grover auto iteration selection uses a classical exact-match count K "
            "for this bounded validation circuit."
        )
        return measured, "c_idx", warnings

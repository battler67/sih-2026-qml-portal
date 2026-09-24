from __future__ import annotations

from quantum_search_api.services.ncbi.models import SearchRequest, WindowRecord


def map_hit(rank: int, window: WindowRecord, query_sequence: str, quantum: dict, validation: dict | None) -> dict:
    return {
        "rank": rank,
        "accession": window.accession,
        "recordTitle": window.record_title,
        "organism": window.organism,
        "taxId": window.tax_id,
        "sourceDatabase": window.source_database,
        "chromosome": window.chromosome,
        "strand": window.strand,
        "start": window.display_start,
        "end": window.display_end,
        "coordinateSystem": "one-based inclusive display; zero-based half-open internally",
        "matchedWindow": window.sequence,
        "querySequence": query_sequence,
        "quantumScore": quantum.get("quantumScore"),
        "algorithm": quantum.get("algorithm"),
        "classicalValidation": validation,
        "ncbiRecordReference": {
            "accession": window.accession,
            "assemblyOrSequence": window.source_database,
        },
        "quantumDetails": quantum,
    }


def result_shell(request: SearchRequest, query_sequence: str, retrieval: dict, warnings: list[str], truncation: dict) -> dict:
    validation = "classical_exact_match" if request.enable_classical_validation else "disabled"
    return {
        "jobId": "",
        "algorithm": request.algorithm.value,
        "executionType": "quantum_simulator",
        "databaseScope": request.database_scope.value,
        "quantumAlphabet": "ACGT",
        "query": {
            "length": len(query_sequence),
            "sequence": query_sequence,
            "sequencePreview": query_sequence[:24] + ("..." if len(query_sequence) > 24 else ""),
        },
        "retrieval": retrieval,
        "pipeline": {
            "retrieval": "NCBI genomic metadata filtering" if "NCBI" in retrieval.get("provider", "") else "local genomic FASTA",
            "prefilter": "none",
            "quantumStage": request.algorithm.value,
            "validation": validation,
        },
        "hits": [],
        "quantumMetrics": {},
        "warnings": warnings,
        "truncation": truncation,
    }

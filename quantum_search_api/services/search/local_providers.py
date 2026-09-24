from __future__ import annotations

from quantum_search_api.services.ncbi.models import RecordMetadata, SearchRequest, SequenceRecord
from quantum_search_api.services.ncbi.provider_base import SequenceProvider
from quantum_search_api.services.sequence.fasta_parser import parse_fasta
from quantum_search_api.services.sequence.normalizer import normalize_query_input


class UploadedFastaProvider(SequenceProvider):
    def search_records(self, request: SearchRequest) -> list[RecordMetadata]:
        records = self.fetch_sequences([], request)
        return [
            RecordMetadata(
                accession=item.accession,
                title=item.title,
                organism=item.organism,
                taxId=item.tax_id,
                sourceDatabase="Uploaded FASTA",
                moleculeType="genomic DNA",
            )
            for item in records
        ]

    def get_record_metadata(self, accessions: list[str]) -> list[RecordMetadata]:
        return []

    def fetch_sequences(self, accessions: list[str], request: SearchRequest | None = None) -> list[SequenceRecord]:
        if request is None or not request.uploaded_fasta:
            return []
        records = []
        for parsed in parse_fasta(request.uploaded_fasta):
            records.append(
                SequenceRecord(
                    accession=parsed.accession,
                    title=parsed.title or parsed.accession,
                    sequence=parsed.sequence,
                    sourceDatabase="Uploaded FASTA",
                    moleculeType="genomic DNA",
                )
            )
        return records


class PastedSequenceProvider(SequenceProvider):
    def search_records(self, request: SearchRequest) -> list[RecordMetadata]:
        return [
            RecordMetadata(
                accession="pasted_target",
                title="Pasted genomic DNA target",
                sourceDatabase="Pasted DNA",
                moleculeType="genomic DNA",
            )
        ]

    def get_record_metadata(self, accessions: list[str]) -> list[RecordMetadata]:
        return self.search_records(
            SearchRequest(
                querySource="pasted",
                querySequence="ACGT",
                referenceSequence="ACGT",
                databaseScope="pasted_sequence",
            )
        )

    def fetch_sequences(self, accessions: list[str], request: SearchRequest | None = None) -> list[SequenceRecord]:
        if request is None or not request.reference_sequence:
            return []
        normalized = normalize_query_input(
            request.reference_sequence,
            max_length=request.max_total_bases,
        )
        return [
            SequenceRecord(
                accession="pasted_target",
                title="Pasted genomic DNA target",
                sequence=normalized.sequence,
                sourceDatabase="Pasted DNA",
                moleculeType="genomic DNA",
            )
        ]

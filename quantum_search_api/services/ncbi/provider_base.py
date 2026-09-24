from __future__ import annotations

from typing import Protocol

from .models import RecordMetadata, SearchRequest, SequenceRecord


class SequenceProvider(Protocol):
    def search_records(self, request: SearchRequest) -> list[RecordMetadata]:
        ...

    def get_record_metadata(self, accessions: list[str]) -> list[RecordMetadata]:
        ...

    def fetch_sequences(self, accessions: list[str], request: SearchRequest | None = None) -> list[SequenceRecord]:
        ...

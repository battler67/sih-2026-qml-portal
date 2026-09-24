from __future__ import annotations

from typing import Any

from quantum_search_api.services.ncbi.models import SequenceRecord
from quantum_search_api.services.sequence.reverse_complement import reverse_complement
from quantum_search_api.services.sequence.validator import validate_target_iupac


def validate_exact(query: str, window: str, *, source: str = "candidate_window") -> dict:
    positions: list[int] = []
    start = window.find(query)
    while start != -1:
        positions.append(start)
        start = window.find(query, start + 1)
    return {
        "type": "classical_exact_match",
        "matches": bool(positions),
        "positionsWithinWindow": positions,
        "validatedWindow": window,
        "validationSource": source,
        "doesNotReplaceQuantumResult": True,
    }


def validate_hit_against_records(
    query: str,
    hit: dict[str, Any],
    records: list[SequenceRecord],
    *,
    max_bases_per_record: int,
    max_total_bases: int,
) -> dict:
    """Validate a hit by re-extracting its coordinate range from the real target sequence."""
    record_sequences = _processed_sequences(records, max_bases_per_record, max_total_bases)
    accession = str(hit.get("accession") or "")
    sequence = record_sequences.get(accession)
    if sequence is None:
        fallback = validate_exact(query, str(hit.get("matchedWindow") or ""), source="stored_candidate_window")
        fallback["warning"] = f"Source sequence for accession {accession or 'unknown'} was not available during validation"
        return fallback

    try:
        start = int(hit.get("start")) - 1
        end = int(hit.get("end"))
    except (TypeError, ValueError):
        fallback = validate_exact(query, str(hit.get("matchedWindow") or ""), source="stored_candidate_window")
        fallback["warning"] = "Hit coordinates were not parseable during source-sequence validation"
        return fallback

    if start < 0 or end < start or end > len(sequence):
        return {
            "type": "classical_exact_match",
            "matches": False,
            "positionsWithinWindow": [],
            "validatedWindow": "",
            "validationSource": "source_sequence_coordinate_range",
            "coordinateSystem": "one-based inclusive display; zero-based half-open internally",
            "warning": f"Hit coordinates {start + 1}-{end} are outside accession {accession} length {len(sequence)}",
            "doesNotReplaceQuantumResult": True,
        }

    window = sequence[start:end]
    if hit.get("strand") == "reverse":
        window = reverse_complement(window)

    validation = validate_exact(query, window, source="source_sequence_coordinate_range")
    validation["coordinateSystem"] = "one-based inclusive display; zero-based half-open internally"
    validation["accession"] = accession
    validation["start"] = start + 1
    validation["end"] = end
    validation["storedWindow"] = str(hit.get("matchedWindow") or "")
    validation["storedWindowMatchesCoordinate"] = validation["storedWindow"] == window
    return validation


def _processed_sequences(
    records: list[SequenceRecord],
    max_bases_per_record: int,
    max_total_bases: int,
) -> dict[str, str]:
    processed: dict[str, str] = {}
    total_bases = 0
    for record in records:
        sequence, _ = validate_target_iupac(record.sequence)
        if len(sequence) > max_bases_per_record:
            sequence = sequence[:max_bases_per_record]
        if total_bases + len(sequence) > max_total_bases:
            sequence = sequence[: max(0, max_total_bases - total_bases)]
        processed.setdefault(record.accession, sequence)
        total_bases += len(sequence)
        if total_bases >= max_total_bases:
            break
    return processed

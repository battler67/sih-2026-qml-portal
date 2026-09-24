from __future__ import annotations

from dataclasses import dataclass

from .fasta_parser import parse_fasta
from .validator import validate_query_acgt, validate_target_iupac


MAX_INPUT_SEQUENCE_LENGTH = 100_000


@dataclass(frozen=True)
class NormalizedSequence:
    original: str
    sequence: str
    length: int
    ambiguous_bases: int
    has_ambiguity: bool
    sequence_preview: str


def normalize_query_input(
    text: str,
    *,
    is_fasta: bool = False,
    max_length: int = MAX_INPUT_SEQUENCE_LENGTH,
) -> NormalizedSequence:
    sequence = parse_fasta(text)[0].sequence if is_fasta or text.lstrip().startswith(">") else text
    normalized = validate_query_acgt(sequence)
    if len(normalized) > max_length:
        raise ValueError(f"Query length {len(normalized)} exceeds configured maximum {max_length}")
    return NormalizedSequence(
        original=text,
        sequence=normalized,
        length=len(normalized),
        ambiguous_bases=0,
        has_ambiguity=False,
        sequence_preview=preview_sequence(normalized),
    )


def bound_normalized_sequence(
    normalized: NormalizedSequence,
    *,
    max_length: int,
) -> NormalizedSequence:
    if normalized.length <= max_length:
        return normalized
    sequence = normalized.sequence[:max_length]
    return NormalizedSequence(
        original=normalized.original,
        sequence=sequence,
        length=len(sequence),
        ambiguous_bases=0,
        has_ambiguity=False,
        sequence_preview=preview_sequence(sequence),
    )


def normalize_target_sequence(text: str) -> NormalizedSequence:
    normalized, ambiguous = validate_target_iupac(text)
    return NormalizedSequence(
        original=text,
        sequence=normalized,
        length=len(normalized),
        ambiguous_bases=ambiguous,
        has_ambiguity=ambiguous > 0,
        sequence_preview=preview_sequence(normalized),
    )


def preview_sequence(sequence: str, width: int = 24) -> str:
    if len(sequence) <= width:
        return sequence
    return f"{sequence[:width]}..."

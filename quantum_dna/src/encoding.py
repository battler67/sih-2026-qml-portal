"""Input validation, position sizing, and classical mismatch helpers."""

from __future__ import annotations

from math import ceil, log2

from .config import NUCLEOTIDE_STATE_ANGLES, VALID_BASES


def validate_sequence(sequence: str, name: str = "sequence") -> str:
    """Normalize and validate a non-empty DNA sequence."""
    if not isinstance(sequence, str):
        raise TypeError(f"{name} must be a string")
    normalized = sequence.strip().upper()
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    invalid = sorted(set(normalized) - VALID_BASES)
    if invalid:
        raise ValueError(f"{name} contains unsupported DNA symbols: {', '.join(invalid)}")
    return normalized


def validate_pair(reference: str, query: str) -> tuple[str, str]:
    """Validate the initially supported equal-length substitution use case."""
    ref = validate_sequence(reference, "reference")
    qry = validate_sequence(query, "query")
    if len(ref) != len(qry):
        raise ValueError("reference and query must have equal length; indels are future work")
    return ref, qry


def position_qubit_count(length: int) -> int:
    """Return at least one position qubit and enough capacity for length."""
    if length < 1:
        raise ValueError("sequence length must be positive")
    return max(1, ceil(log2(length)))


def padded_length(length: int) -> int:
    """Return the position-register capacity."""
    return 1 << position_qubit_count(length)


def angle_for(base: str) -> float:
    """Return the paper state angle passed directly to Qiskit RY."""
    normalized = validate_sequence(base, "base")
    if len(normalized) != 1:
        raise ValueError("base must contain exactly one nucleotide")
    return NUCLEOTIDE_STATE_ANGLES[normalized]


def classical_mutations(reference: str, query: str) -> list[int]:
    """Return zero-based mismatch positions."""
    ref, qry = validate_pair(reference, query)
    return [i for i, (a, b) in enumerate(zip(ref, qry)) if a != b]

"""Input validation and position-register sizing."""

from __future__ import annotations

from math import ceil, log2

from .config import VALID_BASES


def validate_sequence(sequence: str, *, name: str = "sequence") -> str:
    """Return an uppercase DNA sequence or raise ValueError."""

    if not isinstance(sequence, str):
        raise TypeError(f"{name} must be a string")
    normalized = sequence.strip().upper()
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    invalid = sorted(set(normalized) - VALID_BASES)
    if invalid:
        joined = ", ".join(invalid)
        raise ValueError(f"{name} contains invalid DNA symbol(s): {joined}")
    return normalized


def validate_sequence_pair(reference: str, query: str) -> tuple[str, str]:
    """Validate and normalize two equal-length DNA sequences."""

    ref = validate_sequence(reference, name="reference")
    qry = validate_sequence(query, name="query")
    if len(ref) != len(qry):
        raise ValueError(
            f"reference and query must have equal length; got {len(ref)} and {len(qry)}"
        )
    return ref, qry


def position_qubit_count(sequence_length: int) -> int:
    """Return the number of qubits needed to address sequence positions."""

    if sequence_length < 1:
        raise ValueError("sequence_length must be positive")
    return max(1, ceil(log2(sequence_length)))


def position_register_size(sequence_length: int) -> int:
    """Return the computational-basis capacity of the position register."""

    return 2 ** position_qubit_count(sequence_length)


def is_power_of_two(value: int) -> bool:
    """Return True when value is a positive power of two."""

    return value > 0 and (value & (value - 1)) == 0

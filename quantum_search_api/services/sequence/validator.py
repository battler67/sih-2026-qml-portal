from __future__ import annotations

from dataclasses import dataclass


ACGT = set("ACGT")
IUPAC_DNA = set("ACGTRYSWKMBDHVN")


@dataclass(frozen=True)
class InvalidSymbol:
    symbol: str
    position: int


class SequenceValidationError(ValueError):
    def __init__(self, message: str, invalid_symbols: list[InvalidSymbol] | None = None) -> None:
        super().__init__(message)
        self.invalid_symbols = invalid_symbols or []


def validate_query_acgt(sequence: str) -> str:
    normalized = "".join(sequence.split()).upper()
    invalid = [InvalidSymbol(symbol=base, position=index) for index, base in enumerate(normalized) if base not in ACGT]
    if invalid:
        first = invalid[0]
        raise SequenceValidationError(
            f"Query contains unsupported symbol {first.symbol!r} at zero-based position {first.position}; only A, C, G and T are supported",
            invalid,
        )
    if not normalized:
        raise SequenceValidationError("Query sequence must not be empty")
    return normalized


def validate_target_iupac(sequence: str) -> tuple[str, int]:
    normalized = "".join(sequence.split()).upper()
    invalid = [InvalidSymbol(symbol=base, position=index) for index, base in enumerate(normalized) if base not in IUPAC_DNA]
    if invalid:
        first = invalid[0]
        raise SequenceValidationError(
            f"Target contains unsupported symbol {first.symbol!r} at zero-based position {first.position}",
            invalid,
        )
    ambiguous = sum(1 for base in normalized if base not in ACGT)
    return normalized, ambiguous

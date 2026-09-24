"""DNA base encoding helpers for the QGSA paper."""

from .config import DNA_2BIT_ENCODING, DNA_3BIT_TERMINATOR_ENCODING


def encoding_table(encoding_mode: str = "paper_2bit") -> dict[str, str]:
    if encoding_mode == "paper_2bit":
        return DNA_2BIT_ENCODING
    if encoding_mode in {"terminator_3bit", "boundary_safe_3bit"}:
        return DNA_3BIT_TERMINATOR_ENCODING
    raise ValueError(f"unknown encoding_mode: {encoding_mode}")


def bits_per_symbol(encoding_mode: str = "paper_2bit") -> int:
    return len(next(iter(encoding_table(encoding_mode).values())))


def normalize_sequence(sequence: str, *, allow_terminator: bool = False) -> str:
    if sequence is None:
        raise ValueError("sequence must not be None")
    seq = sequence.upper()
    if not seq:
        raise ValueError("sequence must not be empty")
    allowed = set("ACGT$" if allow_terminator else "ACGT")
    bad = sorted(set(seq) - allowed)
    if bad:
        raise ValueError(f"invalid DNA symbols: {bad}")
    return seq


def encode_base(base: str, encoding_mode: str = "paper_2bit") -> tuple[int, ...]:
    table = encoding_table(encoding_mode)
    b = base.upper()
    if b not in table:
        raise ValueError(f"base {base!r} is not valid for {encoding_mode}")
    return tuple(int(bit) for bit in table[b])


def encode_sequence(sequence: str, encoding_mode: str = "paper_2bit") -> list[int]:
    seq = normalize_sequence(
        sequence, allow_terminator=encoding_mode in {"terminator_3bit", "boundary_safe_3bit"}
    )
    bits: list[int] = []
    for base in seq:
        bits.extend(encode_base(base, encoding_mode))
    return bits


def decode_base(bits: str, encoding_mode: str = "paper_2bit") -> str:
    table = encoding_table(encoding_mode)
    reverse = {v: k for k, v in table.items()}
    if bits not in reverse:
        raise ValueError(f"bits {bits!r} are not a valid {encoding_mode} symbol")
    return reverse[bits]

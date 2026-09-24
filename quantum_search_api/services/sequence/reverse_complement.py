from __future__ import annotations


COMPLEMENT = str.maketrans("ACGTRYSWKMBDHVN", "TGCAYRSWMKVHDBN")


def reverse_complement(sequence: str) -> str:
    return sequence.upper().translate(COMPLEMENT)[::-1]

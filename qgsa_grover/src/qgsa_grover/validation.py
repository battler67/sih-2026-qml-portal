"""Input validation and search-space utilities."""

from __future__ import annotations

import math

from .encoding import normalize_sequence


def next_power_of_two(value: int) -> int:
    if value <= 1:
        return 1
    return 1 << (value - 1).bit_length()


def index_qubit_count(search_space_size: int) -> int:
    if search_space_size < 1:
        raise ValueError("search_space_size must be positive")
    return max(1, math.ceil(math.log2(search_space_size)))


def validate_search_inputs(
    target: str,
    pattern: str,
    *,
    boundary_mode: str = "paper_cyclic",
) -> tuple[str, str]:
    target_n = normalize_sequence(target)
    pattern_n = normalize_sequence(pattern)
    if len(pattern_n) > len(target_n):
        raise ValueError("pattern length must not exceed target length")
    if boundary_mode not in {"paper_cyclic", "boundary_safe"}:
        raise ValueError(f"unknown boundary_mode: {boundary_mode}")
    return target_n, pattern_n


def search_space_for(target_length: int, boundary_mode: str) -> int:
    if boundary_mode == "paper_cyclic":
        return target_length
    if boundary_mode == "boundary_safe":
        return next_power_of_two(target_length)
    raise ValueError(f"unknown boundary_mode: {boundary_mode}")


def valid_positions_for(target_length: int, pattern_length: int, boundary_mode: str) -> list[int]:
    if boundary_mode == "paper_cyclic":
        return list(range(target_length))
    return list(range(target_length - pattern_length + 1))

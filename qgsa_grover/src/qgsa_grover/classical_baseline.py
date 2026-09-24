"""Classical exact matching used only for validation and iteration selection."""

from .validation import validate_search_inputs


def classical_exact_matches(target: str, pattern: str) -> list[int]:
    target_n, pattern_n = validate_search_inputs(target, pattern, boundary_mode="boundary_safe")
    m = len(pattern_n)
    return [i for i in range(len(target_n) - m + 1) if target_n[i : i + m] == pattern_n]

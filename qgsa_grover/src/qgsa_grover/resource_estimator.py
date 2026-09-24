"""Simple logical resource estimates."""

from .encoding import bits_per_symbol
from .validation import index_qubit_count, search_space_for


def estimate_logical_resources(target_length: int, pattern_length: int, *, boundary_mode: str, encoding_mode: str) -> dict:
    b = bits_per_symbol(encoding_mode)
    search_space = search_space_for(target_length, boundary_mode)
    index = index_qubit_count(search_space)
    return {
        "index_qubits": index,
        "target_register_qubits": target_length * b,
        "pattern_register_qubits": pattern_length * b,
        "logical_qubits_unoptimized": index + (target_length + pattern_length) * b,
        "logical_qubits_optique_style": index + 2 * pattern_length * b,
        "search_space_size": 2**index,
        "statevector_dimension": 2 ** (index + (target_length + pattern_length) * b),
    }

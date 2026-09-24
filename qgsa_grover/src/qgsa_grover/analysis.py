"""Statevector and measurement analysis helpers."""

from __future__ import annotations

from qiskit.quantum_info import Statevector


def decode_count_key(key: str) -> int:
    clean = key.replace(" ", "")
    return int(clean, 2) if clean else 0


def encode_index_key(index: int, width: int) -> str:
    return format(index, f"0{width}b")


def counts_to_probabilities(counts: dict[str, int], shots: int, width: int) -> dict[str, float]:
    probs = {str(i): 0.0 for i in range(2**width)}
    for key, count in counts.items():
        probs[str(decode_count_key(key))] = count / shots
    return probs


def index_probabilities_from_statevector(circuit, index_width: int) -> dict[str, float]:
    sv = Statevector.from_instruction(circuit)
    raw = sv.probabilities_dict(qargs=list(range(index_width)))
    probs = {str(i): 0.0 for i in range(2**index_width)}
    for key, value in raw.items():
        probs[str(int(str(key), 2))] = float(value)
    return probs


def most_probable_positions(
    probabilities: dict[str, float],
    *,
    valid_positions: list[int],
    matches_exist: bool,
    tolerance: float = 0.06,
) -> list[int]:
    if not matches_exist:
        return []
    filtered = {p: probabilities.get(str(p), 0.0) for p in valid_positions}
    if not filtered:
        return []
    max_prob = max(filtered.values())
    return sorted([p for p, prob in filtered.items() if prob >= max_prob - tolerance])


def success_and_false_positive(probabilities: dict[str, float], matches: list[int], valid_positions: list[int]) -> tuple[float, float]:
    success = sum(probabilities.get(str(pos), 0.0) for pos in matches)
    valid = set(valid_positions)
    false_positive = sum(
        prob for key, prob in probabilities.items() if int(key) in valid and int(key) not in set(matches)
    )
    return success, false_positive

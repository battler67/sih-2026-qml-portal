"""Typed result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CircuitMetrics:
    logical_qubits: int
    depth: int
    size: int
    operation_counts: dict[str, int]


@dataclass(frozen=True)
class ComparisonResult:
    reference: str
    query: str
    sequence_length: int
    position_qubits: int
    position_register_states: int
    non_power_of_two_strategy: str
    shots: int
    seed: int
    angle_mode: str
    angle_mapping: dict[str, dict[str, str | float]]
    counts: dict[str, int]
    p0: float
    p1: float
    similarity: float
    similarity_percentage: float
    clipped_similarity: float
    clipped_similarity_percentage: float
    theoretical_p0: float
    theoretical_p1: float
    theoretical_similarity: float
    theoretical_similarity_percentage: float
    classical_overlap: float
    classical_p1: float
    absolute_error: float
    circuit_metrics: CircuitMetrics
    transpiled_circuit_metrics: CircuitMetrics
    execution_time_seconds: float
    output_paths: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        return asdict(self)

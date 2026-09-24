"""Structured result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CircuitMetrics:
    logical_qubits: int
    ancilla_qubits: int
    depth: int
    size: int
    operation_counts: dict[str, int]


@dataclass
class QGSAResult:
    target: str
    pattern: str
    target_length: int
    pattern_length: int
    encoding: dict[str, str]
    search_space_size: int
    valid_position_count: int
    index_qubits: int
    iterations_requested: str | int
    iterations_executed: int
    paper_iteration_formula_value: int
    classical_match_positions: list[int]
    counts: dict[str, int]
    index_probabilities: dict[str, float]
    quantum_candidate_positions: list[int]
    success_probability: float
    false_positive_probability: float
    matches_found: bool
    circuit_metrics: dict[str, Any]
    transpiled_metrics: dict[str, Any]
    timings: dict[str, float]
    warnings: list[str] = field(default_factory=list)
    output_paths: dict[str, str] = field(default_factory=dict)
    statevector_analysis: dict[str, Any] = field(default_factory=dict)
    optique: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

"""Typed machine-readable result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CircuitMetrics:
    logical_qubits: int
    depth: int
    size: int
    operation_counts: dict[str, int]


@dataclass
class MutationResult:
    position_zero_based: int
    position_one_based: int
    reference_base: str
    query_base: str
    substitution: str
    counts: int
    probability: float
    probability_before: float


@dataclass
class AnalysisResult:
    reference: str
    query: str
    sequence_length: int
    padded_length: int
    position_indexing: str
    mutations: list[MutationResult]
    similarity_percentage: float
    baseline_frqi: dict[str, Any]
    grover_iterations: int
    amplification_status: str
    shots: int
    counts: dict[str, int]
    probabilities: dict[str, float]
    probabilities_before: dict[str, float]
    oracle_marked_positions_zero_based: list[int]
    measured_detected_positions_zero_based: list[int]
    invalid_padded_probability: float
    circuit_metrics: CircuitMetrics
    transpiled_metrics: CircuitMetrics
    register_layout: dict[str, Any]
    oracle_construction: str
    diffuser: str
    backend: str
    seed: int
    artifact_paths: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert nested dataclasses to JSON-compatible dictionaries."""
        return asdict(self)


@dataclass
class FixedPointAnalysisResult:
    """Machine-readable result for coherent unknown-M mismatch amplification."""

    reference: str
    query: str
    sequence_length: int
    padded_length: int
    position_indexing: str
    verification_positions_zero_based: list[int]
    verification_truth_role: str
    measurement_inferred_positions_zero_based: list[int]
    delta: float
    lambda_min: float
    schedule: dict[str, Any]
    fixed_point_rounds: int
    shots: int
    counts: dict[str, int]
    probabilities_before: dict[str, float]
    exact_probabilities_after: dict[str, float]
    shot_probabilities_after: dict[str, float]
    exact_verified_target_probability: float
    shot_verified_target_probability: float
    guaranteed_success_probability: float
    guarantee_applicable: bool
    guarantee_satisfied_exactly: bool | None
    clean_work_probability: float
    invalid_padded_probability_exact: float
    invalid_padded_probability_shots: float
    circuit_metrics: CircuitMetrics
    transpiled_metrics: CircuitMetrics
    register_layout: dict[str, Any]
    oracle_construction: str
    amplification_construction: str
    backend: str
    seed: int
    artifact_paths: dict[str, str] = field(default_factory=dict)
    supported_claims: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

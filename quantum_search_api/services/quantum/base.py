from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class QuantumRunOptions:
    shots: int
    simulator: str = "aer"
    enable_classical_validation: bool = True
    grover_boundary_mode: Literal["boundary_safe", "paper_cyclic"] = "boundary_safe"


class QuantumSearchEngine(Protocol):
    algorithm_name: str

    def validate_request(self, query_sequence: str, target_sequence: str) -> None:
        ...

    def estimate_resources(self, query_length: int, target_length: int) -> dict:
        ...

    def run(self, query_sequence: str, target_sequence: str, options: QuantumRunOptions) -> dict:
        ...

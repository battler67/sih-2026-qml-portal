from __future__ import annotations

import sys
from pathlib import Path

from .base import QuantumRunOptions
from .metrics import gate_count_groups


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frqi_dna.src.analysis import compare_dna_frqi  # noqa: E402


class FrqiSearchEngine:
    algorithm_name = "frqi"

    def validate_request(self, query_sequence: str, target_sequence: str) -> None:
        if len(query_sequence) != len(target_sequence):
            raise ValueError("FRQI window comparison requires equal query and target-window lengths")

    def estimate_resources(self, query_length: int, target_length: int) -> dict:
        position_qubits = max(1, (query_length - 1).bit_length())
        return {
            "estimatedLogicalQubits": 2 + position_qubits,
            "estimatedGroverIterations": 0,
            "notes": ["FRQI compares one bounded target window per circuit run"],
        }

    def run(self, query_sequence: str, target_sequence: str, options: QuantumRunOptions) -> dict:
        self.validate_request(query_sequence, target_sequence)
        raw = compare_dna_frqi(
            reference=target_sequence,
            query=query_sequence,
            shots=options.shots,
            simulator_type=options.simulator,
        )
        result = raw.to_dict()
        logical_counts = result["circuit_metrics"]["operation_counts"]
        transpiled_counts = result["transpiled_circuit_metrics"]["operation_counts"]
        return {
            "algorithm": self.algorithm_name,
            "quantumScore": result["similarity"],
            "stripQubitProbability": result["p1"],
            "frqiSimilarity": result["similarity"],
            "shots": result["shots"],
            "counts": result["counts"],
            "angleMapping": result["angle_mapping"],
            "circuitMetrics": {
                **result["circuit_metrics"],
                **gate_count_groups(logical_counts),
            },
            "transpiledCircuitMetrics": {
                **result["transpiled_circuit_metrics"],
                **gate_count_groups(transpiled_counts),
            },
            "executionTimeSeconds": result["execution_time_seconds"],
            "methodNote": "FRQI window-ranking similarity method; not BLAST alignment",
        }

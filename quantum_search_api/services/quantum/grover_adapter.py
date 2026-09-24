from __future__ import annotations

from .base import QuantumRunOptions
from .metrics import gate_count_groups
from qgsa_grover.qgsa import search_dna_qgsa

MAX_AER_QUBITS = 63


class GroverSearchEngine:
    algorithm_name = "grover"

    def validate_request(self, query_sequence: str, target_sequence: str, *, boundary_mode: str = "boundary_safe") -> None:
        if len(query_sequence) > len(target_sequence):
            raise ValueError("Grover pattern length must not exceed target-window length")
        resource = self.estimate_resources(len(query_sequence), len(target_sequence), boundary_mode=boundary_mode)
        if resource["estimatedLogicalQubits"] > MAX_AER_QUBITS:
            raise ValueError(
                "Grover/QGSA exact-pattern circuit requires "
                f"{resource['estimatedLogicalQubits']} logical qubits for this window, "
                f"which exceeds the local Aer simulator limit of {MAX_AER_QUBITS}. "
                "Use a shorter query/window, reduce maximum query length, or select FRQI similarity."
            )

    def estimate_resources(self, query_length: int, target_length: int, *, boundary_mode: str = "boundary_safe") -> dict:
        target_symbols = (
            1 << max(0, (target_length - 1).bit_length())
            if boundary_mode == "boundary_safe"
            else target_length
        )
        bits_per_symbol = 3 if boundary_mode == "boundary_safe" else 2
        index_qubits = max(1, (target_symbols - 1).bit_length())
        iterations = int(3.14159 / 4 * (2**index_qubits) ** 0.5)
        logical = index_qubits + target_symbols * bits_per_symbol + query_length * bits_per_symbol
        return {
            "estimatedLogicalQubits": logical,
            "estimatedGroverIterations": iterations,
            "notes": [
                "Grover runs exact-pattern search over bounded ACGT windows",
                (
                    "boundary_safe mode pads the target register and uses terminator_3bit encoding"
                    if boundary_mode == "boundary_safe"
                    else "paper_cyclic mode uses the paper-style 2-bit cyclic model"
                ),
            ],
        }

    def run(self, query_sequence: str, target_sequence: str, options: QuantumRunOptions) -> dict:
        self.validate_request(query_sequence, target_sequence, boundary_mode=options.grover_boundary_mode)
        raw = search_dna_qgsa(
            target=target_sequence,
            pattern=query_sequence,
            shots=options.shots,
            iterations="auto",
            boundary_mode=options.grover_boundary_mode,
            simulator_type=options.simulator,
            simulation_method="matrix_product_state",
            compute_statevector=False,
            save_circuits=False,
        )
        result = raw.to_dict()
        logical_counts = result["circuit_metrics"]["operation_counts"]
        transpiled_counts = result["transpiled_metrics"]["operation_counts"]
        invalid_indices = [
            int(index)
            for index in result["index_probabilities"].keys()
            if int(index) >= result["valid_position_count"]
        ]
        return {
            "algorithm": self.algorithm_name,
            "quantumScore": result["success_probability"],
            "successProbability": result["success_probability"],
            "falsePositiveProbability": result["false_positive_probability"],
            "counts": result["counts"],
            "indexProbabilities": result["index_probabilities"],
            "measuredCandidateIndices": result["quantum_candidate_positions"],
            "invalidPaddedIndices": invalid_indices,
            "iterationsExecuted": result["iterations_executed"],
            "iterationFormula": "auto: floor(pi/4 * sqrt(S/K)) when K > 0; zero iterations when no exact match exists",
            "encodingMode": "terminator_3bit" if options.grover_boundary_mode == "boundary_safe" else "paper_2bit",
            "boundaryMode": options.grover_boundary_mode,
            "classicalMatchPositions": result["classical_match_positions"],
            "classicalValidation": {
                "enabled": options.enable_classical_validation,
                "exactMatchPositions": result["classical_match_positions"],
                "matchesFound": result["matches_found"],
            },
            "circuitMetrics": {
                **result["circuit_metrics"],
                **gate_count_groups(logical_counts),
            },
            "transpiledCircuitMetrics": {
                **result["transpiled_metrics"],
                **gate_count_groups(transpiled_counts),
            },
            "executionTimeSeconds": sum(float(value) for value in result.get("timings", {}).values()),
            "executionTimings": result.get("timings", {}),
            "warnings": result["warnings"],
            "methodNote": "Grover/QGSA exact-pattern search over bounded genomic windows",
        }

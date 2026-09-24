"""Generate all required proof-of-concept experiment artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from quantum_dna import analyze_sequences

CASES = {
    "no_mutation": ("AAAA", "AAAA"),
    "single_mutation": ("AAAA", "AAAT"),
    "mixed_single_mutation": ("ACGT", "ACTT"),
    "multiple_mutations": ("ACGTACGT", "ATGTACAT"),
    "non_power_of_two": ("ACGTA", "ATGTT"),
}

summary = {}
for name, (reference, query) in CASES.items():
    result = analyze_sequences(
        reference, query, shots=8192, seed=12345,
        save_circuits=True, output_dir=Path("quantum_dna/outputs") / name,
    )
    summary[name] = {
        "reference": reference,
        "query": query,
        "mutations": [m.position_zero_based for m in result.mutations],
        "measurement_detected_positions": result.measured_detected_positions_zero_based,
        "mutation_probabilities": {str(m.position_zero_based): m.probability for m in result.mutations},
        "before_probabilities": {str(m.position_zero_based): m.probability_before for m in result.mutations},
        "similarity_percentage": result.similarity_percentage,
        "iterations": result.grover_iterations,
        "logical_metrics": result.circuit_metrics.__dict__,
        "transpiled_metrics": result.transpiled_metrics.__dict__,
        "invalid_padded_probability": result.invalid_padded_probability,
    }

path = Path("quantum_dna/outputs/required_experiments_summary.json")
path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(summary, indent=2))

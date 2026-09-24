"""Run the required mixed-base single-substitution demonstration."""

from quantum_dna import analyze_sequences

result = analyze_sequences(
    "ACGT", "ACTT", shots=8192, seed=12345,
    save_circuits=True, output_dir="quantum_dna/outputs/single_mutation",
)
print(result.to_dict())

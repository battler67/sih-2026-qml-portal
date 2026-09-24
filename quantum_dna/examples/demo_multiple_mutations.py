"""Run an eight-base multiple-substitution demonstration."""

from quantum_dna import analyze_sequences

result = analyze_sequences(
    "ACGTACGT", "ATGTACAT", shots=8192, seed=12345,
    save_circuits=True, output_dir="quantum_dna/outputs/multiple_mutations",
)
print(result.to_dict())

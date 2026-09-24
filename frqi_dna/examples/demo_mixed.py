from frqi_dna.src.analysis import compare_dna_frqi


if __name__ == "__main__":
    result = compare_dna_frqi(
        reference="ACGT",
        query="ACTT",
        shots=8000,
        output_dir="frqi_dna/outputs/demo_mixed",
        save_circuits=True,
    )
    print(result.to_dict())

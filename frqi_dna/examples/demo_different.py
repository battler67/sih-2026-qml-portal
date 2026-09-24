from frqi_dna.src.analysis import compare_dna_frqi


if __name__ == "__main__":
    result = compare_dna_frqi(
        reference="AAAA",
        query="TTTT",
        shots=8000,
        output_dir="frqi_dna/outputs/demo_different",
        save_circuits=True,
    )
    print(result.to_dict())

from qgsa_grover import search_dna_qgsa

if __name__ == "__main__":
    result = search_dna_qgsa(
        target="ACGT",
        pattern="AA",
        shots=4096,
        iterations="auto",
        boundary_mode="boundary_safe",
        output_dir="outputs/no_match_acgt_aa",
        save_circuits=True,
    )
    print(result.to_dict())

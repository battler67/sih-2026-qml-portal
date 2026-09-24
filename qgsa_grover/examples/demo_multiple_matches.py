from qgsa_grover import search_dna_qgsa

if __name__ == "__main__":
    result = search_dna_qgsa(
        target="ACGTACGT",
        pattern="CGT",
        shots=8192,
        iterations="auto",
        boundary_mode="boundary_safe",
        output_dir="outputs/acgtacgt_cgt",
        save_circuits=True,
    )
    print(result.to_dict())

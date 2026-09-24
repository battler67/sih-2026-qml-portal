from qgsa_grover import search_dna_qgsa

if __name__ == "__main__":
    result = search_dna_qgsa(
        target="ACGT",
        pattern="A",
        shots=8192,
        iterations="paper",
        boundary_mode="paper_cyclic",
        output_dir="outputs/paper_acgt_a",
        save_circuits=True,
        optimize=True,
    )
    print(result.to_dict())

from qgsa_grover import search_dna_qgsa

if __name__ == "__main__":
    for base in "ACGT":
        result = search_dna_qgsa(
            target="ACGT",
            pattern=base,
            shots=4096,
            iterations="auto",
            output_dir=f"outputs/all_bases_{base}",
            save_circuits=True,
        )
        print(base, result.classical_match_positions, result.quantum_candidate_positions, result.success_probability)

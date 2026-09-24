import numpy as np
from qiskit.quantum_info import Statevector

from quantum_dna.src.mutation_oracle import build_mutation_oracle


def test_oracle_phase_marks_only_mismatch_position():
    oracle = build_mutation_oracle("ACGT", "ACTT", total_qubits=4)
    for position in range(4):
        initial = Statevector.from_int(position, dims=2**4)
        final = initial.evolve(oracle)
        expected = -1 if position == 2 else 1
        assert np.allclose(final.data, expected * initial.data)

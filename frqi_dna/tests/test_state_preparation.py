from math import isclose

from qiskit.quantum_info import Statevector

from frqi_dna.src.frqi_encoding import (
    build_frqi_dna_state,
    build_single_nucleotide_rotation_circuit,
)


def test_four_letter_register_count():
    qc = build_frqi_dna_state("ACGT", "ACGT")
    assert qc.num_qubits == 4
    assert len(qc.qregs[0]) == 1
    assert len(qc.qregs[1]) == 2
    assert len(qc.qregs[2]) == 1


def test_position_control_logic_uses_x_for_zero_controls():
    qc = build_single_nucleotide_rotation_circuit(
        sequence_length=4, strip_value=0, position=0, nucleotide="A"
    )
    assert qc.count_ops().get("x", 0) >= 6


def test_statevector_is_normalized():
    qc = build_frqi_dna_state("ACGT", "ACTT")
    state = Statevector.from_instruction(qc)
    norm = sum(abs(amplitude) ** 2 for amplitude in state.data)
    assert isclose(norm, 1.0, abs_tol=1e-12)

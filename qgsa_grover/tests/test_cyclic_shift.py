from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Statevector

from qgsa_grover.cyclic_shift import (
    apply_index_controlled_shift_network,
    cyclic_shift_truth_table,
)
from qgsa_grover.encoding import encode_sequence
from qgsa_grover.initialization import initialize_basis_sequence
from qgsa_grover.registers import QGSARegisters


def _target_bits_for_index(index: int) -> str:
    idx = QuantumRegister(2, "idx")
    tgt = QuantumRegister(8, "tgt")
    pat = QuantumRegister(2, "pat")
    qc = QuantumCircuit(idx, tgt, pat)
    for bit in range(2):
        if (index >> bit) & 1:
            qc.x(idx[bit])
    initialize_basis_sequence(qc, tgt, "ACGT", "paper_2bit")
    regs = QGSARegisters(idx, tgt, pat, None, 2, 4, 1)
    apply_index_controlled_shift_network(qc, regs)
    probs = Statevector.from_instruction(qc).probabilities_dict(qargs=list(range(2, 10)))
    return next(str(k) for k, v in probs.items() if abs(float(v) - 1.0) < 1e-9)[::-1]


def test_complete_base_shift_truth_table():
    expected = cyclic_shift_truth_table("ACGT", 2, 4)
    for index in range(4):
        assert _target_bits_for_index(index) == expected[index]


def test_no_single_bit_shift_corruption():
    assert cyclic_shift_truth_table("AT", 2, 2)[1] == "".join(map(str, encode_sequence("TA")))

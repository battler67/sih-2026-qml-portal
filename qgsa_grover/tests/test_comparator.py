from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Statevector

from qgsa_grover.comparator import compute_pattern_mismatch
from qgsa_grover.initialization import initialize_basis_sequence
from qgsa_grover.registers import QGSARegisters


def _mismatch_bits(target_prefix: str, pattern: str) -> str:
    tgt = QuantumRegister(2 * len(pattern), "tgt")
    pat = QuantumRegister(2 * len(pattern), "pat")
    idx = QuantumRegister(1, "idx")
    qc = QuantumCircuit(idx, tgt, pat)
    initialize_basis_sequence(qc, tgt, target_prefix, "paper_2bit")
    initialize_basis_sequence(qc, pat, pattern, "paper_2bit")
    regs = QGSARegisters(idx, tgt, pat, None, 2, len(pattern), len(pattern))
    compute_pattern_mismatch(qc, regs)
    start = 1 + len(tgt)
    probs = Statevector.from_instruction(qc).probabilities_dict(qargs=list(range(start, start + len(pat))))
    return next(str(k) for k, v in probs.items() if abs(float(v) - 1.0) < 1e-9)[::-1]


def test_exact_match_mismatch_register_is_zero():
    assert _mismatch_bits("AC", "AC") == "0000"
    assert _mismatch_bits("AG", "AC") != "0000"

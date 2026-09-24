from qiskit.quantum_info import Statevector

from qgsa_grover.oracle import append_qgsa_oracle
from qgsa_grover.qgsa import build_qgsa_circuit


def test_oracle_phase_inverts_only_marked_index_for_paper_example():
    init, meta = build_qgsa_circuit(target="ACGT", pattern="A", iterations=0)
    oracle_circuit, _ = build_qgsa_circuit(target="ACGT", pattern="A", iterations=0)
    # Registers are idx, tgt, pat.
    regs = oracle_circuit.qregs
    from qgsa_grover.registers import QGSARegisters

    shadow = QGSARegisters(regs[0], regs[1], regs[2], None, 2, 4, 1)
    append_qgsa_oracle(oracle_circuit, shadow)
    sv0 = Statevector.from_instruction(init).data
    sv1 = Statevector.from_instruction(oracle_circuit).data
    ratios = []
    for a, b in zip(sv0, sv1):
        if abs(a) > 1e-9:
            ratios.append(round((b / a).real))
    assert ratios.count(-1) == 1
    assert ratios.count(1) == 3

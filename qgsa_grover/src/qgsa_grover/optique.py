"""Supported OPTIQUE-style truth-table reconstruction.

The paper describes OPTIQUE but refers to supplementary material for the
clearest worked subroutine. This module implements the supported core idea:
remove target qubits that never participate in comparison and reconstruct only
the shifted target prefix as functions of the index register.
"""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from .comparator import compute_pattern_mismatch, uncompute_pattern_mismatch
from .diffuser import append_diffuser
from .encoding import encode_sequence
from .grover_iteration import resolve_iterations
from .initialization import initialize_basis_sequence, initialize_index_superposition
from .oracle import apply_mcz, apply_zero_state_phase_flip
from .registers import QGSARegisters
from .validation import index_qubit_count


def optimize_qgsa_truth_table(target: str, pattern_length: int, *, bits_per_symbol: int, encoding_mode: str) -> dict[int, str]:
    width = len(target)
    prefix_bits = pattern_length * bits_per_symbol
    table: dict[int, str] = {}
    for index in range(width):
        shifted = target[index:] + target[:index]
        bits = encode_sequence(shifted, encoding_mode)[:prefix_bits]
        table[index] = "".join(str(bit) for bit in bits)
    return table


def _condition_index(circuit, index_qubits, value: int):
    for bit, qubit in enumerate(index_qubits):
        if ((value >> bit) & 1) == 0:
            circuit.x(qubit)


def _controlled_x_on_value(circuit, index_qubits, target_qubit, value: int):
    _condition_index(circuit, index_qubits, value)
    if len(index_qubits) == 1:
        circuit.cx(index_qubits[0], target_qubit)
    else:
        circuit.mcx(list(index_qubits), target_qubit)
    _condition_index(circuit, index_qubits, value)


def _compute_prefix_from_truth_table(circuit, index, work, table):
    for value, bits in table.items():
        for bit_index, bit in enumerate(bits):
            if bit == "1":
                _controlled_x_on_value(circuit, index, work[bit_index], value)


def build_optique_circuit(
    target: str,
    pattern: str,
    *,
    iterations="auto",
    valid_indices: list[int] | None = None,
    solution_count: int = 1,
    measured: bool = False,
) -> QuantumCircuit:
    bits_per = 2
    idx_n = index_qubit_count(len(target))
    idx = QuantumRegister(idx_n, "idx")
    work = QuantumRegister(len(pattern) * bits_per, "opt_tgt")
    pat = QuantumRegister(len(pattern) * bits_per, "pat")
    creg = ClassicalRegister(idx_n, "c_idx") if measured else None
    qc = QuantumCircuit(idx, work, pat, creg, name="qgsa_optique") if creg else QuantumCircuit(idx, work, pat, name="qgsa_optique")
    regs = QGSARegisters(idx, work, pat, creg, bits_per, len(pattern), len(pattern))
    warnings: list[str] = []
    executed, _ = resolve_iterations(
        iterations,
        target_length=len(target),
        pattern_length=len(pattern),
        search_space_size=2**idx_n,
        solution_count=solution_count,
        warnings=warnings,
    )
    table = optimize_qgsa_truth_table(target, len(pattern), bits_per_symbol=bits_per, encoding_mode="paper_2bit")
    initialize_index_superposition(qc, regs)
    initialize_basis_sequence(qc, pat, pattern, "paper_2bit")
    for _ in range(executed):
        _compute_prefix_from_truth_table(qc, idx, work, table)
        compute_pattern_mismatch(qc, regs)
        apply_zero_state_phase_flip(qc, pat, index_qubits=idx, valid_indices=valid_indices)
        uncompute_pattern_mismatch(qc, regs)
        _compute_prefix_from_truth_table(qc, idx, work, table)
        append_diffuser(qc, idx)
    if measured and creg is not None:
        qc.measure(idx, creg)
    return qc


def compare_original_and_optimized(original, optimized) -> dict:
    return {
        "paper_reported": {"original_logical_qubits": 12, "original_gates": 42, "optimized_logical_qubits": 6, "optimized_gates": 22},
        "original": {
            "logical_qubits": original.num_qubits,
            "depth": original.depth(),
            "size": original.size(),
            "operation_counts": {str(k): int(v) for k, v in original.count_ops().items()},
        },
        "optimized": {
            "logical_qubits": optimized.num_qubits,
            "depth": optimized.depth(),
            "size": optimized.size(),
            "operation_counts": {str(k): int(v) for k, v in optimized.count_ops().items()},
        },
        "status": "partial_supported_core_truth_table_reconstruction",
    }

"""Grover iteration count and circuit composition."""

from __future__ import annotations

import math

from qiskit import QuantumCircuit

from .diffuser import append_diffuser
from .oracle import append_qgsa_oracle
from .registers import QGSARegisters


def paper_iteration_formula(target_length: int, pattern_length: int) -> int:
    return max(1, math.floor((math.pi / 4.0) * math.sqrt(target_length / pattern_length) + 1.0))


def standard_validation_iterations(search_space_size: int, solution_count: int) -> int:
    if solution_count <= 0:
        return 0
    if solution_count >= search_space_size:
        return 0
    return max(1, math.floor((math.pi / 4.0) * math.sqrt(search_space_size / solution_count)))


def resolve_iterations(
    requested,
    *,
    target_length: int,
    pattern_length: int,
    search_space_size: int,
    solution_count: int,
    warnings: list[str],
) -> tuple[int, int]:
    paper_value = paper_iteration_formula(target_length, pattern_length)
    standard = standard_validation_iterations(search_space_size, solution_count)
    if isinstance(requested, int):
        return max(0, requested), paper_value
    if requested == "known_solution_validation" or requested == "auto":
        return standard, paper_value
    if requested == "paper":
        if solution_count == 0:
            warnings.append("paper iteration mode requested, but classical validation found K=0; executed 0 iterations.")
            return 0, paper_value
        if standard and paper_value != standard:
            warnings.append(
                f"paper formula gives {paper_value}, but the small-example Grover optimum is {standard}; "
                "executed the validation count and reported the paper formula separately."
            )
            return standard, paper_value
        return paper_value, paper_value
    raise ValueError(f"unknown iterations mode: {requested}")


def append_grover_iteration(
    circuit: QuantumCircuit,
    regs: QGSARegisters,
    *,
    valid_indices: list[int] | None = None,
) -> None:
    append_qgsa_oracle(circuit, regs, valid_indices=valid_indices)
    append_diffuser(circuit, regs.index)

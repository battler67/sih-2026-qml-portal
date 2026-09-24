"""Grover iteration selection and circuit assembly."""

from __future__ import annotations

from math import asin, pi, sqrt

from qiskit import ClassicalRegister, QuantumCircuit

from .diffusion import build_generalized_diffuser
from .encoding import classical_mutations, position_qubit_count, validate_pair
from .frqi_state import build_combined_frqi_state
from .mutation_oracle import build_mutation_oracle


def choose_iterations(valid_positions: int, marked_positions: int) -> int:
    """Choose the nearest useful integer to pi/(4 theta)-1/2."""
    if valid_positions < 1:
        raise ValueError("valid_positions must be positive")
    if not 0 <= marked_positions <= valid_positions:
        raise ValueError("marked_positions must be between zero and valid_positions")
    if marked_positions == 0 or marked_positions == valid_positions:
        return 0
    theta = asin(sqrt(marked_positions / valid_positions))
    return max(0, round(pi / (4 * theta) - 0.5))


def build_localization_circuits(reference: str, query: str) -> dict[str, QuantumCircuit | int]:
    """Build A, O_f, D_A, one iterate, and full measured/unmeasured circuits."""
    ref, qry = validate_pair(reference, query)
    mutations = classical_mutations(ref, qry)
    preparation = build_combined_frqi_state(ref, qry)
    oracle = build_mutation_oracle(ref, qry, preparation.num_qubits)
    diffuser = build_generalized_diffuser(preparation)
    iteration = QuantumCircuit(preparation.num_qubits, name="Q")
    iteration.compose(oracle, inplace=True)
    iteration.compose(diffuser  , inplace=True)
    rounds = choose_iterations(len(ref), len(mutations))
    full = QuantumCircuit(*preparation.qregs, name="frqi_grover")
    full.compose(preparation, inplace=True)
    for _ in range(rounds):
        full.compose(iteration, inplace=True)
    unmeasured = full.copy()
    classical = ClassicalRegister(position_qubit_count(len(ref)), "c_pos")
    full.add_register(classical)
    full.measure(full.qregs[0], classical)
    return {
        "preparation": preparation,
        "oracle": oracle,
        "diffuser": diffuser,
        "iteration": iteration,
        "unmeasured": unmeasured,
        "measured": full,
        "iterations": rounds,
    }

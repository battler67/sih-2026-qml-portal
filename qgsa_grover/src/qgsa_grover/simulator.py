"""Aer-based simulation helpers."""

from __future__ import annotations

import time

from qiskit import transpile
from qiskit_aer import AerSimulator


def run_shot_simulation(circuit, *, shots: int, seed: int, method: str | None = None):
    method = method or ("matrix_product_state" if circuit.num_qubits > 28 else "automatic")
    backend = AerSimulator(seed_simulator=seed, method=method)
    t0 = time.perf_counter()
    transpiled = transpile(circuit, backend, seed_transpiler=seed, optimization_level=1)
    transpile_seconds = time.perf_counter() - t0
    t1 = time.perf_counter()
    result = backend.run(transpiled, shots=shots).result()
    simulation_seconds = time.perf_counter() - t1
    counts = {str(k): int(v) for k, v in result.get_counts().items()}
    return counts, transpiled, transpile_seconds, simulation_seconds


def circuit_metrics(circuit, *, ancilla_qubits: int = 0) -> dict:
    return {
        "logical_qubits": circuit.num_qubits,
        "ancilla_qubits": ancilla_qubits,
        "depth": circuit.depth(),
        "size": circuit.size(),
        "operation_counts": {str(k): int(v) for k, v in circuit.count_ops().items()},
    }


def hardware_ready_transpile(circuit, backend, *, seed: int = 42, optimization_level: int = 1):
    return transpile(circuit, backend, seed_transpiler=seed, optimization_level=optimization_level)

"""Aer and statevector simulation utilities."""

from __future__ import annotations

import time

from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

from .config import DEFAULT_SEED
from .models import CircuitMetrics


def circuit_metrics(circuit: QuantumCircuit) -> CircuitMetrics:
    """Collect basic circuit metrics."""

    return CircuitMetrics(
        logical_qubits=circuit.num_qubits,
        depth=circuit.depth(),
        size=circuit.size(),
        operation_counts={key: int(value) for key, value in circuit.count_ops().items()},
    )


def strip_probabilities_from_statevector(
    circuit: QuantumCircuit, *, strip_qubit_index: int = 0
) -> tuple[float, float]:
    """Return P(strip=0), P(strip=1) from an unmeasured circuit."""

    state = Statevector.from_instruction(circuit)
    p0 = 0.0
    p1 = 0.0
    for basis_index, amplitude in enumerate(state.data):
        probability = float(abs(amplitude) ** 2)
        if (basis_index >> strip_qubit_index) & 1:
            p1 += probability
        else:
            p0 += probability
    return p0, p1


def run_shot_simulation(
    circuit: QuantumCircuit,
    *,
    shots: int,
    seed: int = DEFAULT_SEED,
) -> tuple[dict[str, int], QuantumCircuit, float]:
    """Run the measured circuit on AerSimulator."""

    simulator = AerSimulator(seed_simulator=seed)
    transpiled = transpile(circuit, simulator, seed_transpiler=seed)
    start = time.perf_counter()
    result = simulator.run(transpiled, shots=shots, seed_simulator=seed).result()
    elapsed = time.perf_counter() - start
    raw_counts = result.get_counts()
    counts = {"0": int(raw_counts.get("0", 0)), "1": int(raw_counts.get("1", 0))}
    return counts, transpiled, elapsed

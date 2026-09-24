"""Modern Aer simulation and circuit metric utilities."""

from __future__ import annotations

from collections import Counter

from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

from .models import CircuitMetrics


def circuit_metrics(circuit: QuantumCircuit) -> CircuitMetrics:
    """Return stable logical or transpiled circuit metrics."""
    return CircuitMetrics(
        logical_qubits=circuit.num_qubits,
        depth=circuit.depth(),
        size=circuit.size(),
        operation_counts={str(k): int(v) for k, v in circuit.count_ops().items()},
    )


def position_probabilities(circuit: QuantumCircuit, width: int) -> dict[str, float]:
    """Return exact position-register marginal probabilities."""
    probabilities = Statevector.from_instruction(circuit).probabilities(qargs=list(range(width)))
    return {format(i, f"0{width}b"): float(p) for i, p in enumerate(probabilities)}


def run_aer(
    circuit: QuantumCircuit, *, shots: int, seed: int
) -> tuple[dict[str, int], QuantumCircuit, CircuitMetrics]:
    """Transpile and run a measured circuit without deprecated execute()."""
    if shots < 1:
        raise ValueError("shots must be positive")
    backend = AerSimulator(seed_simulator=seed)
    # Explicitly lower StatePreparation multiplexers and controlled-unitary
    # instructions. Aer 0.17.2 on Python 3.13 can crash in its assembler when a
    # high-level multiplexer survives target-based transpilation.
    compiled = transpile(
        circuit,
        basis_gates=["u", "cx"],
        optimization_level=1,
        seed_transpiler=seed,
    )
    raw = backend.run(compiled, shots=shots).result().get_counts()
    counts = dict(sorted(Counter(raw).items()))
    return counts, compiled, circuit_metrics(compiled)

"""Reproduction of the FRQI paper's strip-qubit similarity experiment."""

from __future__ import annotations

from math import cos

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit_aer import AerSimulator

from .encoding import angle_for, position_qubit_count, validate_pair
from .frqi_state import append_position_controlled_ry, position_state_gate


def build_baseline_circuit(reference: str, query: str, measured: bool = False) -> QuantumCircuit:
    """Build the paper-inspired strip/position/color comparison circuit."""
    ref, qry = validate_pair(reference, query)
    strip = QuantumRegister(1, "strip")
    pos = QuantumRegister(position_qubit_count(len(ref)), "pos")
    color = QuantumRegister(1, "dna")
    classical = ClassicalRegister(1, "c_strip") if measured else None
    circuit = QuantumCircuit(strip, pos, color, classical, name="baseline_frqi") if classical else QuantumCircuit(strip, pos, color, name="baseline_frqi")
    circuit.h(strip)
    circuit.append(position_state_gate(len(ref)), pos)
    for branch, sequence in enumerate((ref, qry)):
        for i, base in enumerate(sequence):
            controls = [strip[0], *list(pos)]
            control_value = branch | (i << 1)
            for bit, qubit in enumerate(controls):
                if not ((control_value >> bit) & 1):
                    circuit.x(qubit)
            angle = angle_for(base)
            if abs(angle) > 1e-15:
                circuit.mcry(angle, controls, color[0], None, mode="noancilla")
            for bit, qubit in enumerate(controls):
                if not ((control_value >> bit) & 1):
                    circuit.x(qubit)
    circuit.h(strip)
    if measured:
        circuit.measure(strip, classical)
    return circuit


def theoretical_p1(reference: str, query: str) -> float:
    """Paper overlap probability under the documented Qiskit convention."""
    ref, qry = validate_pair(reference, query)
    return sum((1 - cos((angle_for(a) - angle_for(b)) / 2)) / 2 for a, b in zip(ref, qry)) / len(ref)


def run_baseline(reference: str, query: str, shots: int, seed: int) -> tuple[dict, QuantumCircuit]:
    """Simulate baseline and return paper similarity plus circuit."""
    circuit = build_baseline_circuit(reference, query, measured=True)
    backend = AerSimulator(seed_simulator=seed)
    compiled = transpile(circuit, backend, seed_transpiler=seed)
    counts = backend.run(compiled, shots=shots).result().get_counts()
    observed = counts.get("1", 0) / shots
    expected = theoretical_p1(reference, query)
    return {
        "counts": dict(counts),
        "p1_observed": observed,
        "p1_theoretical": expected,
        "similarity_observed": 1 - 2 * observed,
        "similarity_theoretical": 1 - 2 * expected,
        "formula": "similarity = 1 - 2*P(strip=1)",
    }, circuit

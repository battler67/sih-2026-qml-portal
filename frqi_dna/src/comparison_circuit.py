"""Sequence-comparison circuit built from the FRQI DNA state."""

from __future__ import annotations

from qiskit import QuantumCircuit

from .frqi_encoding import build_frqi_dna_state


def build_comparison_circuit(
    reference: str, query: str, *, angle_mode: str = "paper_state"
) -> QuantumCircuit:
    """Return the unmeasured comparison circuit.

    The final Hadamard on strip[0] converts the overlap between the reference
    and query branches into the probability of measuring strip=1.
    """

    qc = build_frqi_dna_state(reference, query, angle_mode=angle_mode)
    strip = qc.qregs[0]
    qc.barrier(label="strip interference")
    qc.h(strip[0])
    return qc


def build_measured_comparison_circuit(
    reference: str, query: str, *, angle_mode: str = "paper_state"
) -> QuantumCircuit:
    """Return the comparison circuit with a classical strip measurement."""

    qc = build_comparison_circuit(reference, query, angle_mode=angle_mode)
    measured = qc.copy(name="frqi_dna_comparison_measured")
    classical = measured.cregs[0] if measured.cregs else None
    if classical is None:
        from qiskit import ClassicalRegister

        classical = ClassicalRegister(1, "c")
        measured.add_register(classical)
    strip = measured.qregs[0]
    measured.measure(strip[0], classical[0])
    return measured


def circuits_for_external_transpilation(
    reference: str, query: str, *, angle_mode: str = "paper_state"
) -> tuple[QuantumCircuit, QuantumCircuit]:
    """Return unmeasured and measured circuits for later hardware execution."""

    return (
        build_comparison_circuit(reference, query, angle_mode=angle_mode),
        build_measured_comparison_circuit(reference, query, angle_mode=angle_mode),
    )

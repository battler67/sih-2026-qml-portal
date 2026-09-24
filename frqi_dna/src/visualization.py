"""Circuit, histogram, and report output helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
from qiskit import QuantumCircuit

from .frqi_encoding import (
    build_position_superposition,
    build_sequence_branch_encoding,
    build_single_nucleotide_rotation_circuit,
)

if TYPE_CHECKING:
    from .models import ComparisonResult


def _try_qasm(circuit: QuantumCircuit) -> str | None:
    try:
        from qiskit import qasm2

        return qasm2.dumps(circuit)
    except Exception:
        return None


def save_circuit(circuit: QuantumCircuit, output_base: Path, *, fold: int = 120) -> dict[str, str]:
    """Save one circuit as text, PNG, and QASM when available."""

    output_base.parent.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}

    text_path = output_base.with_suffix(".txt")
    text_path.write_text(str(circuit.draw(output="text", fold=fold)), encoding="utf-8")
    paths["text"] = str(text_path)

    try:
        figure = circuit.draw(output="mpl", fold=fold, idle_wires=False)
        png_path = output_base.with_suffix(".png")
        figure.savefig(png_path, bbox_inches="tight", dpi=180)
        plt.close(figure)
        paths["png"] = str(png_path)
    except Exception as exc:
        error_path = output_base.with_suffix(".png.error.txt")
        error_path.write_text(str(exc), encoding="utf-8")
        paths["png_error"] = str(error_path)

    qasm = _try_qasm(circuit)
    if qasm is not None:
        qasm_path = output_base.with_suffix(".qasm")
        qasm_path.write_text(qasm, encoding="utf-8")
        paths["qasm"] = str(qasm_path)
    return paths


def save_histogram(counts: dict[str, int], path: Path) -> str:
    """Save a strip-qubit measurement histogram."""

    path.parent.mkdir(parents=True, exist_ok=True)
    labels = ["0", "1"]
    values = [counts.get("0", 0), counts.get("1", 0)]
    total = max(1, sum(values))

    fig, ax = plt.subplots(figsize=(5, 3.4))
    bars = ax.bar(labels, values, color=["#4477aa", "#cc6677"])
    ax.set_xlabel("Measured strip bit")
    ax.set_ylabel("Counts")
    ax.set_title("FRQI DNA strip measurement")
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value}\n{value / total:.4f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return str(path)


def write_report(path: Path, result: "ComparisonResult") -> str:
    """Write a human-readable experiment report."""

    lines = [
        "FRQI DNA sequence comparison report",
        "",
        f"Reference: {result.reference}",
        f"Query:     {result.query}",
        f"Length: {result.sequence_length}",
        f"Shots: {result.shots}",
        f"Angle mode: {result.angle_mode}",
        f"Non-power-of-two strategy: {result.non_power_of_two_strategy}",
        "",
        "Probabilities",
        f"  theoretical P(0): {result.theoretical_p0:.12f}",
        f"  theoretical P(1): {result.theoretical_p1:.12f}",
        f"  shot P(0):        {result.p0:.12f}",
        f"  shot P(1):        {result.p1:.12f}",
        f"  absolute P1 error:{result.absolute_error:.12f}",
        "",
        "Similarity",
        f"  theoretical: {result.theoretical_similarity:.12f}",
        f"  shot raw:    {result.similarity:.12f}",
        f"  shot raw %:  {result.similarity_percentage:.6f}",
        f"  clipped %:   {result.clipped_similarity_percentage:.6f}",
        "",
        "Classical FRQI-angle validation",
        f"  branch overlap: {result.classical_overlap:.12f}",
        f"  expected P(1):  {result.classical_p1:.12f}",
        "",
        "Measured counts",
        json.dumps(result.counts, indent=2),
        "",
        "Circuit metrics",
        json.dumps(result.circuit_metrics.__dict__, indent=2),
        "",
        "Transpiled circuit metrics",
        json.dumps(result.transpiled_circuit_metrics.__dict__, indent=2),
        f"Execution time seconds: {result.execution_time_seconds:.6f}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def save_experiment_artifacts(
    *,
    output_dir: Path,
    reference: str,
    query: str,
    encoding_circuit: QuantumCircuit,
    unmeasured_circuit: QuantumCircuit,
    measured_circuit: QuantumCircuit,
    transpiled_circuit: QuantumCircuit,
    result: "ComparisonResult",
    save_circuits: bool,
) -> dict[str, str]:
    """Save all requested outputs for one experiment."""

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    paths["histogram_png"] = save_histogram(result.counts, output_dir / "histogram.png")
    paths["report_txt"] = write_report(output_dir / "report.txt", result)
    probabilities = {
        "theoretical_p0": result.theoretical_p0,
        "theoretical_p1": result.theoretical_p1,
        "classical_overlap": result.classical_overlap,
        "classical_p1": result.classical_p1,
    }
    prob_path = output_dir / "statevector_probabilities.json"
    prob_path.write_text(json.dumps(probabilities, indent=2), encoding="utf-8")
    paths["statevector_probabilities_json"] = str(prob_path)

    if save_circuits:
        circuit_paths = {
            "position_superposition": save_circuit(
                build_position_superposition(len(reference)),
                output_dir / "position_superposition",
            ),
            "single_nucleotide_controlled_rotation": save_circuit(
                build_single_nucleotide_rotation_circuit(
                    sequence_length=len(reference),
                    strip_value=0,
                    position=min(len(reference) - 1, 3),
                    nucleotide=reference[min(len(reference) - 1, 0)],
                ),
                output_dir / "single_nucleotide_controlled_rotation",
            ),
            "reference_sequence_encoding": save_circuit(
                build_sequence_branch_encoding(reference, strip_value=0),
                output_dir / "reference_sequence_encoding",
            ),
            "query_sequence_encoding": save_circuit(
                build_sequence_branch_encoding(query, strip_value=1),
                output_dir / "query_sequence_encoding",
            ),
            "frqi_encoding": save_circuit(
                encoding_circuit,
                output_dir / "frqi_encoding",
            ),
            "comparison_circuit": save_circuit(
                unmeasured_circuit,
                output_dir / "comparison_circuit",
            ),
            "measured_circuit": save_circuit(
                measured_circuit,
                output_dir / "measured_circuit",
            ),
            "transpiled_circuit": save_circuit(
                transpiled_circuit,
                output_dir / "transpiled_circuit",
            ),
        }
        circuit_path = output_dir / "circuit_paths.json"
        circuit_path.write_text(json.dumps(circuit_paths, indent=2), encoding="utf-8")
        paths["circuit_paths_json"] = str(circuit_path)

    return paths

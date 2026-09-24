"""Circuit, histogram, alignment, and report artifact generation."""

from __future__ import annotations

import json
from math import acos, acosh, cos, cosh, sqrt
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, qasm2, qasm3, transpile

from .config import IBM_BASIS_GATES
from .models import CircuitMetrics
from .simulator import circuit_metrics


def save_json(path: Path, data: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return str(path)


def save_circuit(circuit: QuantumCircuit, directory: Path, stem: str) -> dict[str, str]:
    """Save readable text, PNG, and QASM2 when exportable."""
    directory.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    text_path = directory / f"{stem}.txt"
    text_path.write_text(str(circuit.draw("text", fold=120)), encoding="utf-8")
    paths[f"{stem}_text"] = str(text_path)
    png_path = directory / f"{stem}.png"
    try:
        circuit.draw("mpl", fold=100, scale=0.65, filename=str(png_path), idle_wires=False)
        plt.close("all")
        paths[f"{stem}_png"] = str(png_path)
    except Exception as exc:
        note = directory / f"{stem}.png.skipped.txt"
        note.write_text(str(exc), encoding="utf-8")
        paths[f"{stem}_png_note"] = str(note)
    try:
        qasm_path = directory / f"{stem}.qasm"
        # QASM2's qelib1.inc defines u1/u2/u3 but not modern Qiskit `u` or
        # IBM-native `sx`. Lower first so every saved artifact round-trips with
        # Qiskit's strict QASM2 parser.
        qasm_ready = transpile(
            circuit,
            basis_gates=["u1", "u2", "u3", "cx"],
            optimization_level=0,
        )
        qasm_path.write_text(qasm2.dumps(qasm_ready), encoding="utf-8")
        paths[f"{stem}_qasm"] = str(qasm_path)
    except Exception as exc:
        note = directory / f"{stem}.qasm.skipped.txt"
        note.write_text(str(exc), encoding="utf-8")
        paths[f"{stem}_qasm_note"] = str(note)
    return paths


def save_histogram(probabilities: dict[str, float], path: Path, title: str, marked: list[int]) -> str:
    labels = list(probabilities)
    values = [probabilities[x] for x in labels]
    colors = ["#d62728" if int(label, 2) in marked else "#4c78a8" for label in labels]
    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.65), 4))
    ax.bar(labels, values, color=colors)
    ax.set(title=title, xlabel="Position (binary; zero-based)", ylabel="Probability", ylim=(0, max(values + [0.01]) * 1.18))
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return str(path)


def save_alignment(reference: str, query: str, path: Path) -> str:
    fig, ax = plt.subplots(figsize=(max(7, len(reference) * 0.7), 2.5))
    ax.axis("off")
    for i, (a, b) in enumerate(zip(reference, query)):
        color = "#d62728" if a != b else "#2ca02c"
        ax.text(i, 1.0, a, ha="center", fontsize=16, color=color, weight="bold")
        ax.text(i, 0.45, "|" if a == b else "×", ha="center", fontsize=13, color=color)
        ax.text(i, 0.0, b, ha="center", fontsize=16, color=color, weight="bold")
        ax.text(i, -0.42, str(i), ha="center", fontsize=9)
    ax.set_xlim(-0.7, len(reference) - 0.3)
    ax.set_ylim(-0.7, 1.3)
    ax.set_title("Reference / query alignment (indices are zero-based)")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return str(path)


def save_metrics_plot(logical: CircuitMetrics, compiled: CircuitMetrics, path: Path) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    axes[0].bar(["logical", "Aer transpiled"], [logical.depth, compiled.depth], color=["#4c78a8", "#f58518"])
    axes[0].set_title("Circuit depth")
    operations = sorted(set(logical.operation_counts) | set(compiled.operation_counts))
    axes[1].barh(operations, [compiled.operation_counts.get(x, 0) for x in operations], color="#54a24b")
    axes[1].set_title("Aer-transpiled gate counts")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return str(path)


def ibm_basis_example(circuit: QuantumCircuit) -> tuple[QuantumCircuit, CircuitMetrics]:
    """Transpile against a representative IBM-compatible basis, not a device."""
    compiled = transpile(circuit, basis_gates=IBM_BASIS_GATES, optimization_level=1)
    return compiled, circuit_metrics(compiled)


def save_qasm3(circuit: QuantumCircuit, path: Path) -> str:
    """Export portable OpenQASM 3 after lowering custom Qiskit instructions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lowered = transpile(
        circuit,
        basis_gates=["u", "cx"],
        optimization_level=0,
    )
    path.write_text(qasm3.dumps(lowered), encoding="utf-8")
    return str(path)


def save_phase_schedule(phases: list[tuple[float, float]], path: Path) -> str:
    """Plot matched fixed-point alpha/beta phase pairs."""
    rounds = list(range(1, len(phases) + 1))
    alphas = [pair[0] for pair in phases]
    betas = [pair[1] for pair in phases]
    fig, ax = plt.subplots(figsize=(max(7, len(rounds) * 0.9), 4))
    width = 0.38
    ax.bar([x - width / 2 for x in rounds], alphas, width, label="alpha", color="#4c78a8")
    ax.bar([x + width / 2 for x in rounds], betas, width, label="beta", color="#f58518")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set(
        title="Unknown-M fixed-point phase schedule",
        xlabel="Fixed-point round",
        ylabel="Phase (radians)",
        xticks=rounds,
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return str(path)


def _chebyshev(order: int, x: float) -> float:
    if -1.0 <= x <= 1.0:
        return cos(order * acos(x))
    if x > 1.0:
        return cosh(order * acosh(x))
    return ((-1) ** order) * cosh(order * acosh(-x))


def save_fixed_point_success_curve(
    schedule: dict[str, Any],
    path: Path,
    *,
    verified_lambda: float | None,
) -> str:
    """Plot the ideal Yoder-Low-Chuang success polynomial and guarantee."""
    delta = float(schedule["delta"])
    odd_length = int(schedule["odd_length"])
    gamma_inverse = 1.0 / float(schedule["gamma"])
    xs = [i / 500 for i in range(501)]
    ys = [
        1.0
        - delta * delta
        * _chebyshev(
            odd_length,
            gamma_inverse * sqrt(max(0.0, 1.0 - value)),
        )
        ** 2
        for value in xs
    ]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(xs, ys, color="#4c78a8", linewidth=2, label="ideal fixed-point success")
    ax.axhline(
        float(schedule["guaranteed_success_probability"]),
        color="#d62728",
        linestyle="--",
        label="guaranteed success",
    )
    ax.axvline(
        float(schedule["lambda_min"]),
        color="#54a24b",
        linestyle=":",
        label="promised lambda_min",
    )
    if verified_lambda is not None:
        ax.axvline(
            verified_lambda,
            color="#b279a2",
            linestyle="-.",
            label="verification case M/N",
        )
    ax.set(
        title="Fixed-point success versus marked fraction",
        xlabel="Marked fraction lambda = M/N",
        ylabel="Ideal success probability",
        xlim=(0, 1),
        ylim=(-0.03, 1.03),
    )
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return str(path)

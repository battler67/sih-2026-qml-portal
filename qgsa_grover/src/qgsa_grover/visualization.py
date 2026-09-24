"""Circuit, histogram, JSON, and report writers."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import qasm2
from qiskit.qasm2 import QASM2ExportError


PNG_RENDER_QUBIT_LIMIT = 28
PNG_RENDER_SIZE_LIMIT = 2500


def ensure_dir(path: str | Path) -> Path:
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    return out


def save_json(path: str | Path, data) -> str:
    p = Path(path)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return str(p)


def save_circuit_artifacts(circuit, output_dir: str | Path, stem: str) -> dict[str, str]:
    out = ensure_dir(output_dir)
    paths: dict[str, str] = {}
    txt = out / f"{stem}.txt"
    txt.write_text(str(circuit.draw(output="text", fold=160)), encoding="utf-8")
    paths["txt"] = str(txt)
    if circuit.num_qubits > PNG_RENDER_QUBIT_LIMIT or circuit.size() > PNG_RENDER_SIZE_LIMIT:
        skip = out / f"{stem}.png.skipped.txt"
        skip.write_text(
            "PNG rendering skipped because this circuit is too large for reliable "
            "Matplotlib rendering in the local environment. The readable text "
            "diagram and QASM artifact were saved instead. Thresholds: "
            f"num_qubits <= {PNG_RENDER_QUBIT_LIMIT} and size <= {PNG_RENDER_SIZE_LIMIT}.\n",
            encoding="utf-8",
        )
        paths["png_skipped"] = str(skip)
    else:
        png = out / f"{stem}.png"
        fig = circuit.draw(output="mpl", fold=80, idle_wires=False)
        fig.savefig(png, dpi=180, bbox_inches="tight")
        plt.close(fig)
        paths["png"] = str(png)
    try:
        qasm = out / f"{stem}.qasm"
        qasm.write_text(qasm2.dumps(circuit), encoding="utf-8")
        paths["qasm"] = str(qasm)
    except QASM2ExportError as exc:
        paths["qasm_error"] = str(exc)
    return paths


def save_histogram(probabilities: dict[str, float], output_dir: str | Path, stem: str = "histogram") -> str:
    out = ensure_dir(output_dir)
    items = sorted(((int(k), v) for k, v in probabilities.items()), key=lambda item: item[0])
    labels = [str(k) for k, _ in items]
    values = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, values, color="#4477AA")
    ax.set_xlabel("Decoded index position")
    ax.set_ylabel("Probability")
    ax.set_ylim(0, max(1.0, max(values, default=0) * 1.1))
    fig.tight_layout()
    path = out / f"{stem}.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return str(path)


def write_report(path: str | Path, lines: list[str]) -> str:
    p = Path(path)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)

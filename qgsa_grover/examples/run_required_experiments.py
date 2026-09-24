"""Run the required QGSA reproduction experiments."""

from __future__ import annotations

import json
from pathlib import Path

from qgsa_grover import search_dna_qgsa
from qgsa_grover.resource_estimator import estimate_logical_resources
from qgsa_grover.visualization import save_histogram, save_json


EXPERIMENTS = [
    ("paper_acgt_a", "ACGT", "A", "paper_cyclic", "paper", True),
    ("all_base_A", "ACGT", "A", "paper_cyclic", "auto", False),
    ("all_base_C", "ACGT", "C", "paper_cyclic", "auto", False),
    ("all_base_G", "ACGT", "G", "paper_cyclic", "auto", False),
    ("all_base_T", "ACGT", "T", "paper_cyclic", "auto", False),
    ("longer_pattern_acgtacgt_cgt", "ACGTACGT", "CGT", "boundary_safe", "auto", False),
    ("repeated_aaaa_a", "AAAA", "A", "paper_cyclic", "auto", False),
    ("no_match_acgt_aa", "ACGT", "AA", "boundary_safe", "auto", False),
    ("non_power_acgta_gta", "ACGTA", "GTA", "boundary_safe", "auto", False),
    ("prevent_wrap_at_ta", "AT", "TA", "boundary_safe", "auto", False),
    ("one_mismatch_acgt_ag", "ACGT", "AG", "boundary_safe", "auto", False),
]


REQUIRED_RESULT_FILES = [
    "config.json",
    "result.json",
    "counts.json",
    "probabilities.json",
    "statevector_analysis.json",
    "report.txt",
    "histogram.png",
]

REQUIRED_CIRCUIT_STEMS = [
    "initialization",
    "cyclic_shift",
    "comparator",
    "oracle_logical",
    "diffuser",
    "one_iteration",
    "full_circuit",
    "measured_circuit",
    "transpiled_circuit",
]


def _load_valid_result(directory: Path, *, target: str, pattern: str) -> dict | None:
    result_path = directory / "result.json"
    if not result_path.exists():
        return None
    try:
        data = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if data.get("target") != target or data.get("pattern") != pattern:
        return None
    if sum(int(v) for v in data.get("counts", {}).values()) != 8192:
        return None
    if "success_probability" not in data or "classical_match_positions" not in data:
        return None
    return data


def _has_core_artifacts(directory: Path) -> bool:
    for name in REQUIRED_RESULT_FILES:
        if not (directory / name).exists():
            return False
    return _has_circuit_artifacts(directory)


def _has_circuit_artifacts(directory: Path) -> bool:
    for stem in REQUIRED_CIRCUIT_STEMS:
        if not (directory / f"{stem}.txt").exists() and not (directory / f"{stem}.txt.skipped.txt").exists():
            return False
        if not (directory / f"{stem}.qasm").exists() and not (directory / f"{stem}.qasm.skipped.txt").exists():
            return False
        if not (directory / f"{stem}.png").exists() and not (directory / f"{stem}.png.skipped.txt").exists():
            return False
    return True


def _has_logical_artifacts_without_transpiled(directory: Path) -> bool:
    for stem in [s for s in REQUIRED_CIRCUIT_STEMS if s != "transpiled_circuit"]:
        if not (directory / f"{stem}.txt").exists():
            return False
        if not (directory / f"{stem}.qasm").exists():
            return False
        if not (directory / f"{stem}.png").exists() and not (directory / f"{stem}.png.skipped.txt").exists():
            return False
    return True


def _write_result_sidecars(directory: Path, data: dict) -> None:
    if not (directory / "config.json").exists():
        save_json(
            directory / "config.json",
            {
                "target": data["target"],
                "pattern": data["pattern"],
                "target_length": data["target_length"],
                "pattern_length": data["pattern_length"],
                "search_space_size": data["search_space_size"],
                "valid_position_count": data["valid_position_count"],
                "index_qubits": data["index_qubits"],
                "iterations_requested": data["iterations_requested"],
                "iterations_executed": data["iterations_executed"],
                "encoding": data["encoding"],
            },
        )
    save_json(directory / "probabilities.json", data["index_probabilities"])
    save_json(directory / "counts.json", {key: int(value) for key, value in data["counts"].items()})
    save_json(directory / "statevector_analysis.json", data.get("statevector_analysis", {}))
    save_histogram(data["index_probabilities"], directory)
    if data["circuit_metrics"]["logical_qubits"] > 28 and not (directory / "transpiled_circuit.txt").exists():
        for suffix in ["txt", "qasm", "png"]:
            skip = directory / f"transpiled_circuit.{suffix}.skipped.txt"
            skip.write_text(
                "Transpiled circuit artifact generation skipped for this large circuit. "
                "The logical circuit text/QASM, result JSON, counts JSON, probabilities JSON, "
                "histogram, and metrics are present. Transpilation metrics are stored in result.json.\n",
                encoding="utf-8",
            )
    if not (directory / "report.txt").exists():
        lines = [
            "QGSA Experiment Report",
            f"Target: {data['target']}",
            f"Pattern: {data['pattern']}",
            f"Classical expected positions: {data['classical_match_positions']}",
            f"Quantum candidates: {data['quantum_candidate_positions']}",
            f"Success probability: {data['success_probability']:.6f}",
            f"Counts: {data['counts']}",
            f"Warnings: {data.get('warnings', [])}",
        ]
        (directory / "report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _png_status(directory: Path) -> dict[str, str]:
    status = {}
    for stem in REQUIRED_CIRCUIT_STEMS:
        if (directory / f"{stem}.png").exists() and not (directory / f"{stem}.png.skipped.txt").exists():
            status[stem] = "rendered"
        elif (directory / f"{stem}.png.skipped.txt").exists():
            status[stem] = "skipped_large_circuit"
        elif (directory / f"{stem}.png").exists():
            status[stem] = "rendered_previous_run_and_current_skip_note_present"
        else:
            status[stem] = "missing"
    return status


def _top_counts(data: dict, limit: int = 4) -> list[dict]:
    counts = data.get("counts", {})
    total = max(1, sum(int(v) for v in counts.values()))
    return [
        {"bitstring": key, "decoded_index": int(key, 2), "count": int(count), "probability": int(count) / total}
        for key, count in sorted(counts.items(), key=lambda item: int(item[1]), reverse=True)[:limit]
    ]


def _summary_entry(name: str, data: dict, *, boundary_mode: str, directory: Path) -> dict:
    search_space = int(data["search_space_size"])
    valid_positions = set(range(int(data["valid_position_count"])))
    if boundary_mode == "boundary_safe":
        valid_positions = set(range(data["target_length"] - data["pattern_length"] + 1))
    invalid = [i for i in range(search_space) if i not in valid_positions]
    return {
        "experiment_name": name,
        "target": data["target"],
        "pattern": data["pattern"],
        "target_length": data["target_length"],
        "pattern_length": data["pattern_length"],
        "search_space_size": search_space,
        "valid_position_count": data["valid_position_count"],
        "index_qubits": data["index_qubits"],
        "grover_iterations_executed": data["iterations_executed"],
        "paper_iteration_formula_value": data["paper_iteration_formula_value"],
        "expected_matching_indices": data["classical_match_positions"],
        "quantum_candidate_positions": data["quantum_candidate_positions"],
        "top_measured_states": _top_counts(data),
        "success_probability": data["success_probability"],
        "false_positive_probability": data["false_positive_probability"],
        "shot_count": sum(int(v) for v in data.get("counts", {}).values()),
        "boundary_mode": boundary_mode,
        "boundary_safe": boundary_mode == "boundary_safe",
        "invalid_or_padded_index_states": invalid,
        "artifact_directory": str(directory),
        "png_status": _png_status(directory),
        "qiskit_measurement_note": (
            "idx[i] is measured into c_idx[i]; Qiskit count strings are read as normal binary "
            "for this register layout. Index bitstrings are not DNA base encodings."
        ),
        "warnings": data.get("warnings", []),
    }


def main() -> int:
    base = Path("qgsa_grover/outputs")
    base.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, target, pattern, boundary_mode, iterations, optimize in EXPERIMENTS:
        directory = base / name
        existing = _load_valid_result(directory, target=target, pattern=pattern)
        if existing and _has_circuit_artifacts(directory):
            print(f"REUSE {name}", flush=True)
            data = existing
            _write_result_sidecars(directory, data)
        else:
            needs_circuit_artifacts = not (
                _has_circuit_artifacts(directory) or _has_logical_artifacts_without_transpiled(directory)
            )
            print(f"RUN {name} save_circuits={needs_circuit_artifacts}", flush=True)
            result = search_dna_qgsa(
                target=target,
                pattern=pattern,
                shots=8192,
                iterations=iterations,
                boundary_mode=boundary_mode,
                output_dir=directory,
                save_circuits=needs_circuit_artifacts,
                optimize=optimize,
                seed=42,
            )
            data = result.to_dict()
            _write_result_sidecars(directory, data)
        summary[name] = _summary_entry(name, data, boundary_mode=boundary_mode, directory=directory)
        print(
            f"{name}: expected={data['classical_match_positions']} "
            f"quantum={data['quantum_candidate_positions']} "
            f"success={data['success_probability']:.6f}",
            flush=True,
        )
    summary["optional_resource_estimate_paper_longer_case"] = estimate_logical_resources(
        target_length=65,
        pattern_length=9,
        boundary_mode="boundary_safe",
        encoding_mode="terminator_3bit",
    )
    (base / "required_experiments_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"WROTE {base / 'required_experiments_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

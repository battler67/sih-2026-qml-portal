"""Validate generated required-experiment output directories."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REQUIRED_RESULT_FILES = [
    "config.json",
    "result.json",
    "counts.json",
    "probabilities.json",
    "statevector_analysis.json",
    "report.txt",
    "histogram.png",
]


def _load_runner():
    spec = importlib.util.spec_from_file_location("runner", "qgsa_grover/examples/run_required_experiments.py")
    runner = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(runner)
    return runner


def main() -> int:
    runner = _load_runner()
    base = Path("qgsa_grover/outputs")
    summary_path = base / "required_experiments_summary.json"
    if not summary_path.exists():
        raise SystemExit("missing required_experiments_summary.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    missing: list[str] = []
    rows = []
    skips: dict[str, list[str]] = {}
    for name, target, pattern, boundary_mode, _iterations, _optimize in runner.EXPERIMENTS:
        directory = base / name
        if name not in summary:
            missing.append(f"{name}/summary_entry")
        if not directory.exists():
            missing.append(f"{name}/directory")
            continue
        result_path = directory / "result.json"
        if not result_path.exists():
            missing.append(f"{name}/result.json")
            continue
        data = json.loads(result_path.read_text(encoding="utf-8"))
        if data.get("target") != target or data.get("pattern") != pattern:
            missing.append(f"{name}/target_pattern_mismatch")
        if sum(int(v) for v in data.get("counts", {}).values()) != 8192:
            missing.append(f"{name}/shot_count")
        for filename in REQUIRED_RESULT_FILES:
            if not (directory / filename).exists():
                missing.append(f"{name}/{filename}")
        for stem in runner.REQUIRED_CIRCUIT_STEMS:
            if not ((directory / f"{stem}.txt").exists() or (directory / f"{stem}.txt.skipped.txt").exists()):
                missing.append(f"{name}/{stem}.txt")
            if not ((directory / f"{stem}.qasm").exists() or (directory / f"{stem}.qasm.skipped.txt").exists()):
                missing.append(f"{name}/{stem}.qasm")
            if not ((directory / f"{stem}.png").exists() or (directory / f"{stem}.png.skipped.txt").exists()):
                missing.append(f"{name}/{stem}.png")
            if (
                (directory / f"{stem}.txt.skipped.txt").exists()
                or (directory / f"{stem}.qasm.skipped.txt").exists()
                or (directory / f"{stem}.png.skipped.txt").exists()
            ):
                skips.setdefault(name, []).append(stem)
        rows.append(
            {
                "name": name,
                "boundary_mode": boundary_mode,
                "expected": data["classical_match_positions"],
                "quantum": data["quantum_candidate_positions"],
                "success": round(float(data["success_probability"]), 6),
                "iterations": data["iterations_executed"],
                "logical_qubits": data["circuit_metrics"]["logical_qubits"],
                "transpiled_depth": data["transpiled_metrics"]["depth"],
            }
        )
    if missing:
        print("MISSING_OR_INVALID")
        for item in missing:
            print(item)
        return 1
    print("OUTPUT_CHECK_OK")
    for row in rows:
        print(
            "ROW "
            f"{row['name']} mode={row['boundary_mode']} expected={row['expected']} "
            f"quantum={row['quantum']} success={row['success']} iterations={row['iterations']} "
            f"logical_qubits={row['logical_qubits']} transpiled_depth={row['transpiled_depth']}"
        )
    print("SKIPPED", skips)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate every generated fixed-point JSON, PNG, QASM, and artifact path."""

from __future__ import annotations

import json
from pathlib import Path

from qiskit import qasm2


CASES = {
    "no_mismatch",
    "single_mismatch",
    "multiple_mismatches",
    "non_power_of_two",
    "all_mismatch",
}


def main() -> None:
    root = Path("quantum_dna/outputs/fixed_point_hybrid")
    missing_cases = sorted(CASES - {path.name for path in root.iterdir() if path.is_dir()})
    if missing_cases:
        raise RuntimeError(f"missing experiment directories: {missing_cases}")

    json_files = sorted(root.rglob("*.json"))
    png_files = sorted(root.rglob("*.png"))
    qasm2_files = sorted(root.rglob("*.qasm"))
    qasm3_files = sorted(root.rglob("*.qasm3"))
    report_files = sorted(root.rglob("report.txt"))

    for path in json_files:
        json.loads(path.read_text(encoding="utf-8"))
    for path in png_files:
        data = path.read_bytes()
        if len(data) < 100 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError(f"invalid PNG: {path}")
    for path in qasm2_files:
        qasm2.load(path)
    for path in qasm3_files:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("OPENQASM 3") or "measure" not in text:
            raise RuntimeError(f"invalid QASM3 preparation artifact: {path}")
    for path in report_files:
        if "Limitations" not in path.read_text(encoding="utf-8"):
            raise RuntimeError(f"report lacks limitations: {path}")

    result_files = sorted(root.rglob("result.json"))
    recorded_paths = 0
    for result_path in result_files:
        result = json.loads(result_path.read_text(encoding="utf-8"))
        for artifact in result["artifact_paths"].values():
            recorded_paths += 1
            if not Path(artifact).is_file():
                raise RuntimeError(f"recorded artifact does not exist: {artifact}")

    summary = {
        "cases": sorted(CASES),
        "case_count": len(CASES),
        "json_files_valid": len(json_files),
        "png_files_valid": len(png_files),
        "qasm2_files_valid": len(qasm2_files),
        "qasm3_files_valid": len(qasm3_files),
        "result_files_checked": len(result_files),
        "reports_with_limitations": len(report_files),
        "recorded_artifact_paths_existing": recorded_paths,
        "status": "passed",
    }
    path = root / "artifact_audit_summary.json"
    path.write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

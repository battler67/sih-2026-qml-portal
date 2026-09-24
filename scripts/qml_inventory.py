"""Inventory local QML research outputs without copying patient-level artifacts.

Usage: python scripts/qml_inventory.py ../qml-research --output docs/qml-model-inventory.json
The output contains only relative paths, hashes, sizes and aggregate run metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SERIALIZED_EXTENSIONS = {".joblib", ".pkl", ".pickle", ".pt", ".pth", ".npz", ".npy", ".onnx"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_role(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".kernel.npz") or "kernel_cache" in name:
        return "research_kernel_cache"
    if name in {"training_states.npz", "parameters.npz"}:
        return "inference_state"
    if "pipeline" in name or "preprocessing" in name:
        return "preprocessing"
    if "calibrator" in name or "platt" in name:
        return "calibrator"
    if name == "checkpoint.pt" or name.startswith("weights") or name.endswith(".pt"):
        return "model_weights"
    return "fitted_estimator"


def runs(root: Path) -> list[dict]:
    output: list[dict] = []
    framingham = root / "results/framingham"
    for path in sorted(framingham.glob("*/seed-*/**/metrics.json")):
        metric = read_json(path)
        output.append({
            "track": "framingham",
            "run_id": path.parts[-4],
            "seed": metric.get("seed"),
            "model": metric.get("model"),
            "family": metric.get("family"),
            "status": "completed",
            "metrics_path": path.relative_to(root).as_posix(),
            "metrics": {key: metric.get(key) for key in (
                "auroc", "auprc", "balanced_accuracy", "recall_sensitivity", "specificity",
                "f1", "mcc", "selected_threshold", "training_time_seconds",
                "inference_time_seconds", "qubits", "circuit_executions", "state_preparations",
            ) if key in metric},
        })
    for directory in sorted((root / "results/ehr_ihd_qml").glob("*/")):
        summary = directory / "summary.json"
        if not summary.exists():
            continue
        data = read_json(summary)
        output.append({
            "track": "ehr_ihd_qml",
            "run_id": data.get("run_id", directory.name),
            "status": data.get("status"),
            "models": data.get("models", []),
            "selected_features": data.get("selected_features", []),
            "summary_path": summary.relative_to(root).as_posix(),
        })
    for path in sorted((root / "results/qcnn_breast_cancer/runs").glob("*/record.json")):
        record = read_json(path)
        metrics = record.get("metrics", {})
        output.append({
            "track": "qcnn_breast_cancer",
            "run_id": record.get("run_id", path.parent.name),
            "dataset": record.get("dataset"),
            "model": record.get("model"),
            "seed": record.get("seed"),
            "fold": record.get("fold"),
            "profile": record.get("profile"),
            "status": record.get("status"),
            "checkpoint_present": (path.parent / "checkpoint.pt").is_file(),
            "record_path": path.relative_to(root).as_posix(),
            "metrics": {key: metrics.get(key) for key in (
                "auroc", "auprc", "balanced_accuracy", "sensitivity", "specificity",
                "f1", "mcc", "threshold", "training_time_seconds", "prediction_time_seconds",
            ) if key in metrics},
        })
    return output


def make_inventory(root: Path) -> dict:
    results = root / "results"
    if not results.is_dir():
        raise FileNotFoundError(f"Research results directory is missing: {results}")
    artifacts = []
    for path in sorted(results.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SERIALIZED_EXTENSIONS:
            continue
        artifacts.append({
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "role": artifact_role(path),
            "track": path.relative_to(results).parts[0],
        })
    return {
        "schema_version": 1,
        "source_repository": "qml-research",
        "scope": "local serialized files; branch-tracked kernel caches are included",
        "artifact_count": len(artifacts),
        "artifact_bytes": sum(item["bytes"] for item in artifacts),
        "artifacts": artifacts,
        "runs": runs(root),
        "notes": [
            "An inventory entry is not a claim that the artifact is deployable or clinically valid.",
            "Local ignored artifacts need explicit promotion; Git branches alone cannot restore them.",
            "No participant-level predictions, raw datasets or split manifests are copied here.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("research_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.research_root.resolve(strict=True)
    inventory = make_inventory(root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Recorded {inventory['artifact_count']} artifacts and {len(inventory['runs'])} runs")


if __name__ == "__main__":
    main()

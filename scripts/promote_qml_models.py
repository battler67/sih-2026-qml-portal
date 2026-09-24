"""Promote a bounded set of verified local QML research artifacts.

This copies no raw dataset, participant IDs, split manifest, or row-level predictions.
Run after `qml_inventory.py` from a trusted local `qml-research` checkout.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import statistics
import sys
from pathlib import Path

import joblib


FRAMINGHAM_RUN = "framingham-audited-20260909"
UCI_RUN = "uci-smoke-20260829T194302Z-3b55c98a85f0"
SEED = 11  # Selected before comparing test-seed outcomes; no best-test-seed picking.
FILES = {
    "framingham/pca2_pipeline.joblib": f"results/framingham/{FRAMINGHAM_RUN}/seed-{SEED}/pca2_pipeline.joblib",
    "framingham/angle_qksvm_pca2/svm.joblib": f"results/framingham/{FRAMINGHAM_RUN}/seed-{SEED}/angle_qksvm_pca2/svm.joblib",
    "framingham/angle_qksvm_pca2/training_states.npz": f"results/framingham/{FRAMINGHAM_RUN}/seed-{SEED}/angle_qksvm_pca2/training_states.npz",
    "framingham/angle_qksvm_pca2/calibrator.joblib": f"results/framingham/{FRAMINGHAM_RUN}/seed-{SEED}/angle_qksvm_pca2/calibrator.joblib",
    "framingham/logistic_pca2/model.joblib": f"results/framingham/{FRAMINGHAM_RUN}/seed-{SEED}/logistic_pca2/model.joblib",
    "framingham/logistic_pca2/calibrator.joblib": f"results/framingham/{FRAMINGHAM_RUN}/seed-{SEED}/logistic_pca2/calibrator.joblib",
    "uci/selected_pipeline.joblib": f"results/ehr_ihd_qml/{UCI_RUN}/preprocessing/selected_pipeline.joblib",
    "uci/rbf_svm.joblib": f"results/ehr_ihd_qml/{UCI_RUN}/models/rbf_svm.joblib",
    "uci/rbf_svm_platt.joblib": f"results/ehr_ihd_qml/{UCI_RUN}/calibration/rbf_svm_platt.joblib",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def compact_metrics(record: dict) -> dict:
    fields = (
        "model", "family", "seed", "representation", "patient_count", "positive_count",
        "accuracy", "balanced_accuracy", "auroc", "auprc", "recall_sensitivity",
        "sensitivity", "specificity", "f1", "mcc", "selected_threshold", "threshold",
        "training_time_seconds", "inference_time_seconds", "prediction_time_seconds",
        "qubits", "circuit_executions", "state_preparations", "kernel_method",
        "confusion_matrix", "confidence_intervals", "roc_curve", "precision_recall_curve",
    )
    return {field: record[field] for field in fields if field in record}


def framingham_summary(path: Path, run_root: Path) -> list[dict]:
    """Three-seed descriptive means and spreads, never a selected test seed."""
    rows = []
    with path.open(newline="", encoding="utf-8") as stream:
        for source in csv.DictReader(stream):
            row = {"model": source["model"], "seedCount": 3}
            for field in ("auroc", "auprc", "balanced_accuracy", "recall_sensitivity",
                          "specificity", "fit_seconds"):
                for suffix in ("mean", "std"):
                    key = f"{field}_{suffix}"
                    if source.get(key):
                        row[("training_time_seconds" if field == "fit_seconds" else field)
                            + ("Std" if suffix == "std" else "")] = float(source[key])
            per_seed = [read_json(run_root / f"seed-{seed}" / source["model"] / "metrics.json")
                        for seed in (11, 42, 73)]
            for field in ("accuracy", "f1", "mcc", "inference_time_seconds"):
                values = [float(record[field]) for record in per_seed]
                row[field] = statistics.mean(values)
                row[field + "Std"] = statistics.stdev(values)
            if "qubits" in per_seed[0]:
                row["qubits"] = per_seed[0]["qubits"]
            rows.append(row)
    return rows


def promote(root: Path, target: Path) -> None:
    inventory = read_json(Path("docs/qml-model-inventory.json"))
    known = {a["path"]: a["sha256"] for a in inventory["artifacts"]}
    manifest_files: dict[str, dict] = {}
    for destination, source in FILES.items():
        src = root / source
        if not src.is_file() or digest(src) != known.get(source):
            raise ValueError(f"Missing or changed inventory artifact: {source}")
        dst = target / destination
        dst.parent.mkdir(parents=True, exist_ok=True)
        if destination == "uci/selected_pipeline.joblib":
            # The research object is a small custom dataclass. Export only its fitted
            # sklearn objects so deployment does not depend on the research package.
            sys.path.insert(0, str(root / "src"))
            try:
                pipeline = joblib.load(src)
            finally:
                sys.path.pop(0)
            portable = {
                "schemaVersion": 1,
                "featureOrder": list(pipeline.feature_order),
                "imputer": pipeline.imputer,
                "standardScaler": pipeline.standard_scaler,
            }
            joblib.dump(portable, dst, compress=0, protocol=4)
        else:
            shutil.copyfile(src, dst)
        manifest_files[destination] = {
            "source": source,
            "sourceSha256": digest(src),
            "sha256": digest(dst),
            "bytes": dst.stat().st_size,
        }

    froot = root / "results/framingham" / FRAMINGHAM_RUN
    uroot = root / "results/ehr_ihd_qml" / UCI_RUN
    status = read_json(froot / "status.json")
    verification = read_json(root / "experiments/framingham/evidence/verification.json")
    if status.get("status") != "completed" or not verification.get("metrics_recomputed_from_saved_predictions"):
        raise ValueError("Framingham run is not verified as complete")
    evidence = {
        "schemaVersion": 1,
        "framingham": {
            "runId": FRAMINGHAM_RUN,
            "status": status,
            "verification": verification,
            "teachingDataOnly": True,
            "summary": framingham_summary(root / "experiments/framingham/evidence/summary.csv", froot),
            "perSeed": [
                compact_metrics(read_json(froot / f"seed-{seed}" / model / "metrics.json"))
                for seed in (11, 42, 73)
                for model in ("angle_qksvm_pca2", "logistic_pca2", "rbf_svm_full")
            ],
            "limitation": "Overlapping repeated splits; no independent clinical validation or quantum advantage.",
        },
        "uci": {
            "runId": UCI_RUN,
            "status": read_json(uroot / "summary.json").get("status"),
            "profile": "smoke",
            "models": [compact_metrics(row) for row in read_json(uroot / "metrics/model_metrics.json")],
            "limitation": "One small diagnostic test split; not a future-event model or clinical validation.",
        },
        "qcnn": {
            "profile": "smoke",
            "runs": [
                {
                    "runId": r["run_id"], "dataset": r["dataset"], "model": r["model"],
                    "seed": r["seed"], "fold": r["fold"], "status": r["status"],
                    "checkpointPresent": r["checkpoint_present"], "metrics": r["metrics"],
                }
                for r in inventory["runs"] if r["track"] == "qcnn_breast_cancer"
            ],
            "limitation": "Smoke experiments only. WDBC is a diagnostic dataset; no early detection claim.",
        },
    }
    target.mkdir(parents=True, exist_ok=True)
    (target / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schemaVersion": 1,
        "version": "2026-09-21-2",
        "sourceRepository": "qml-research",
        "framinghamRun": FRAMINGHAM_RUN,
        "framinghamSeed": SEED,
        "uciRun": UCI_RUN,
        "python": "3.12",
        "researchEnvironment": read_json(froot / "environment.json"),
        "files": manifest_files,
        "selection": {
            "framinghamQuantum": "angle_qksvm_pca2",
            "framinghamMatchedClassical": "logistic_pca2",
            "uciClassical": "rbf_svm",
            "uciReason": "Highest saved smoke-run AUPRC among UCI classical models; evidence is descriptive only.",
        },
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Promoted {len(FILES)} files ({sum(item['bytes'] for item in manifest_files.values())} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("research_root", type=Path)
    parser.add_argument("--output", type=Path, default=Path("qml_inference/artifacts/v1"))
    args = parser.parse_args()
    promote(args.research_root.resolve(strict=True), args.output)


if __name__ == "__main__":
    main()

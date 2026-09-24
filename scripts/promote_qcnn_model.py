"""Promote and replay-verify the existing BreastMNIST QCNN checkpoint.

No raw image, split manifest, or row-level prediction is copied into the portal.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np

RUN_ID = "e77cc845e586cfdd"
SOURCE_CHECKPOINT = f"results/qcnn_breast_cancer/runs/{RUN_ID}/checkpoint.pt"
SOURCE_RECORD = f"results/qcnn_breast_cancer/runs/{RUN_ID}/record.json"
SOURCE_CONFIG = f"results/qcnn_breast_cancer/runs/{RUN_ID}/resolved_config.json"
SOURCE_PREDICTIONS = f"results/qcnn_breast_cancer/runs/{RUN_ID}/predictions.csv"
SOURCE_DATA = "data/raw/medmnist/breastmnist.npz"


def digest(path: Path, algorithm: str = "sha256") -> str:
    checksum = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def add_manifest_file(
    manifest: dict,
    target: Path,
    relative: str,
    *,
    source: str,
    source_hash: str | None = None,
) -> None:
    path = target / relative
    manifest["files"][relative] = {
        "source": source,
        "sourceSha256": source_hash or digest(path),
        "sha256": digest(path),
        "bytes": path.stat().st_size,
    }


def promote(research_root: Path, target: Path) -> dict:
    inventory = read_json(Path("docs/qml-model-inventory.json"))
    known = {item["path"]: item["sha256"] for item in inventory["artifacts"]}
    checkpoint = research_root / SOURCE_CHECKPOINT
    if not checkpoint.is_file() or digest(checkpoint) != known.get(SOURCE_CHECKPOINT):
        raise ValueError("QCNN checkpoint is missing or differs from the audited inventory")
    record = read_json(research_root / SOURCE_RECORD)
    config = read_json(research_root / SOURCE_CONFIG)
    if record.get("status") != "completed" or record.get("model") != "qcnn":
        raise ValueError("QCNN source run is not completed")
    expected = {
        "dataset": "breastmnist",
        "image_size": 28,
        "reducer": "spatial_pool",
        "reduced_features": 4,
        "qubits": 4,
        "encoding": "angle_ry",
        "stages": 2,
    }
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"QCNN source configuration mismatch: {key}")

    destination = target / "qcnn/breastmnist/checkpoint.pt"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(checkpoint, destination)
    serving = {
        "schemaVersion": 1,
        "modelId": "breastmnist-qcnn",
        "runId": RUN_ID,
        "architecture": {
            "identifier": "hierarchical_qcnn_su4_ising_unitary_controlled_v1",
            "qubits": 4,
            "stages": 2,
            "encoding": "angle_ry",
            "convolution": "su4_ising",
            "pooling": "unitary_controlled",
        },
        "input": {
            "formats": ["image/png", "image/jpeg"],
            "shape": [28, 28, 1],
            "channels": "grayscale",
            "resize": "bilinear",
            "maxBytes": 5242880,
        },
        "preprocessing": {
            "reducer": "spatial_pool",
            "grid": [2, 2],
            "regionShape": [14, 14],
            "reducedFeatures": 4,
            "pixelDivisor": 255.0,
            "angleFormula": "pi * (2 * pooled_intensity/255 - 1)",
            "angleRange": [-3.141592653589793, 3.141592653589793],
            "fittedStateRequired": False,
        },
        "output": {
            "positiveClass": 1,
            "positiveLabel": "malignant",
            "negativeClass": 0,
            "negativeLabel": "normal_or_benign",
            "score": "sigmoid(logit)",
            "threshold": float(record["metrics"]["threshold"]),
            "calibrated": False,
        },
        "quantum": {
            "qubits": 4,
            "stages": 2,
            "activeQubits": "4 → 2 → 1",
            "circuitDepth": int(record["resources"]["depth"]),
            "totalGates": int(record["resources"]["total_gates"]),
            "twoQubitGates": int(record["resources"]["two_qubit_gates"]),
            "shots": None,
            "measurement": "PauliZ expectation on the final active qubit",
        },
        "research": {
            "seed": int(record["seed"]),
            "profile": record["profile"],
            "trainSize": int(config["train_size"]),
            "validationSize": int(config["validation_size"]),
            "testSize": int(config["test_size"]),
            "epochs": int(config["epochs"]),
            "datasetVersion": config["dataset_version"],
            "sourceCommit": record["system"]["git"]["commit"],
            "metrics": {
                key: record["metrics"][key]
                for key in (
                    "accuracy",
                    "balanced_accuracy",
                    "sensitivity",
                    "specificity",
                    "f1",
                    "auroc",
                    "auprc",
                    "mcc",
                )
            },
            "evidenceWarning": "Smoke run trained on 32 images for two epochs with weak held-out discrimination; not clinically validated.",
        },
    }
    serving_path = target / "qcnn/breastmnist/serving.json"
    serving_path.write_text(json.dumps(serving, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest_path = target / "manifest.json"
    manifest = read_json(manifest_path)
    evidence_path = target / "evidence.json"
    evidence = read_json(evidence_path)
    evidence["qcnn"]["liveModel"] = "breastmnist-qcnn"
    evidence["qcnn"]["limitation"] = (
        "The BreastMNIST QCNN smoke checkpoint is runnable for research demonstration. "
        "It was trained on 32 images for two epochs, has weak held-out discrimination, "
        "and is not clinically validated."
    )
    evidence_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    add_manifest_file(
        manifest,
        target,
        "evidence.json",
        source="existing deidentified evidence plus QCNN live-serving status",
    )
    manifest["version"] = "2026-09-22-qcnn-1"
    manifest["selection"]["qcnn"] = "breastmnist-qcnn"
    manifest["qcnnRun"] = RUN_ID
    add_manifest_file(
        manifest,
        target,
        "qcnn/breastmnist/checkpoint.pt",
        source=SOURCE_CHECKPOINT,
        source_hash=digest(checkpoint),
    )
    add_manifest_file(
        manifest,
        target,
        "qcnn/breastmnist/serving.json",
        source=f"derived from {SOURCE_RECORD} and {SOURCE_CONFIG}",
    )

    sys.path.insert(0, str(Path.cwd()))
    try:
        from qml_inference.qcnn import ProcessedImage, QcnnBundle, spatial_pool_angles

        bundle = QcnnBundle(target, manifest)
        with np.load(research_root / SOURCE_DATA, allow_pickle=False) as data:
            test_images = np.asarray(data["test_images"], dtype=np.uint8)
        expected_scores: dict[int, float] = {}
        with (research_root / SOURCE_PREDICTIONS).open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                if row["split"] == "test":
                    expected_scores[int(row["dataset_index"])] = float(row["malignant_score"])
        deltas = []
        for index in sorted(expected_scores)[:5]:
            pixels = test_images[index]
            processed = ProcessedImage(
                [28, 28, 1],
                "L",
                pixels,
                spatial_pool_angles(pixels[None, ...])[0],
            )
            actual = bundle.predict_processed(processed)["malignantScore"]
            deltas.append(abs(actual - expected_scores[index]))
    finally:
        sys.path.pop(0)
    # default.qubit and the original lightning.qubit backend differ only at
    # floating-point rounding scale for this replay.
    tolerance = 1e-7
    maximum_delta = max(deltas)
    verification = {
        "schemaVersion": 1,
        "runId": RUN_ID,
        "dataset": "BreastMNIST 3.0.2 official test split",
        "datasetMd5": digest(research_root / SOURCE_DATA, "md5"),
        "replayedSamples": len(deltas),
        "maxAbsoluteScoreError": maximum_delta,
        "tolerance": tolerance,
        "passed": maximum_delta <= tolerance,
        "participantLevelOutputsStored": False,
    }
    if not verification["passed"]:
        raise ValueError(f"QCNN replay exceeded tolerance: {maximum_delta}")
    verification_path = target / "qcnn/breastmnist/verification.json"
    verification_path.write_text(
        json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    add_manifest_file(
        manifest,
        target,
        "qcnn/breastmnist/verification.json",
        source=f"replay of {SOURCE_PREDICTIONS} against {SOURCE_DATA}",
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return verification


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("research_root", type=Path)
    parser.add_argument("--output", type=Path, default=Path("qml_inference/artifacts/v1"))
    args = parser.parse_args()
    result = promote(args.research_root.resolve(strict=True), args.output.resolve())
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

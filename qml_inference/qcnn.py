"""Training-free BreastMNIST QCNN serving from a verified checkpoint."""

from __future__ import annotations

import io
import json
import math
from time import perf_counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pennylane as qml
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    import torch
except ImportError:  # Vercel uses the NumPy-only inference path.
    torch = None

QCNN_MODEL_ID = "breastmnist-qcnn"
QCNN_DISCLAIMER = (
    "Research demonstration only — not intended for clinical diagnosis or treatment decisions."
)
SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_DECODED_PIXELS = 16_000_000
IMAGE_SIZE = 28


class QcnnArtifactError(RuntimeError):
    pass


class QcnnInputError(ValueError):
    pass


def convolution_block(weights: np.ndarray, wires: tuple[int, int]) -> None:
    qml.U3(weights[0], weights[1], weights[2], wires=wires[0])
    qml.U3(weights[3], weights[4], weights[5], wires=wires[1])
    qml.IsingXX(weights[6], wires=wires)
    qml.IsingYY(weights[7], wires=wires)
    qml.IsingZZ(weights[8], wires=wires)
    qml.U3(weights[9], weights[10], weights[11], wires=wires[0])
    qml.U3(weights[12], weights[13], weights[14], wires=wires[1])


def pooling_block(weights: np.ndarray, source: int, sink: int) -> None:
    qml.CRZ(weights[0], wires=(source, sink))
    qml.PauliX(wires=source)
    qml.CRX(weights[1], wires=(source, sink))
    qml.PauliX(wires=source)
    qml.CRY(weights[2], wires=(source, sink))


def convolution_pairs(active: list[int]) -> list[tuple[int, int]]:
    pairs = [(active[index], active[index + 1]) for index in range(0, len(active), 2)]
    if len(active) > 2:
        pairs.extend(
            (active[index], active[(index + 1) % len(active)])
            for index in range(1, len(active), 2)
        )
    return pairs


class ServingQCNN:
    """Exact four-qubit architecture used by the saved research run."""

    def __init__(self, qubits: int) -> None:
        if qubits != 4:
            raise QcnnArtifactError("Serving bundle requires the verified four-qubit architecture")
        self.conv_weights = np.zeros((2, 15), dtype=np.float64)
        self.pool_weights = np.zeros((2, 3), dtype=np.float64)
        self.output_scale = 1.0
        self.output_bias = 0.0
        device = qml.device("default.qubit", wires=qubits)

        @qml.qnode(device, interface="torch" if torch is not None else None, diff_method=None)
        def circuit(
            features: np.ndarray,
            conv_weights: np.ndarray,
            pool_weights: np.ndarray,
        ) -> float:
            for wire in range(qubits):
                qml.RY(features[wire], wires=wire)
            active = list(range(qubits))
            for stage in range(2):
                for pair in convolution_pairs(active):
                    convolution_block(conv_weights[stage], pair)
                for index in range(0, len(active), 2):
                    pooling_block(pool_weights[stage], active[index], active[index + 1])
                active = active[1::2]
            return qml.expval(qml.PauliZ(active[0]))

        self.qnode = circuit

    def expectation(self, features: np.ndarray) -> float:
        if features.shape != (4,):
            raise ValueError("QCNN features must have shape [4]")
        if torch is not None:
            source = torch.as_tensor(features, dtype=torch.float64)
            return self.qnode(source, self.conv_weights, self.pool_weights)
        return float(self.qnode(np.asarray(features, dtype=np.float64), self.conv_weights, self.pool_weights))

    def load_state(self, state: dict[str, Any]) -> None:
        try:
            conv_weights = np.asarray(state["conv_weights"], dtype=np.float64)
            pool_weights = np.asarray(state["pool_weights"], dtype=np.float64)
            output_scale = float(state["output_scale"])
            output_bias = float(state["output_bias"])
        except (KeyError, TypeError, ValueError) as exc:
            raise QcnnArtifactError("QCNN serving weights are invalid") from exc
        if conv_weights.shape != (2, 15) or pool_weights.shape != (2, 3):
            raise QcnnArtifactError("QCNN serving weight shapes do not match the architecture")
        if not all(np.isfinite(value).all() for value in (conv_weights, pool_weights)):
            raise QcnnArtifactError("QCNN serving weights contain non-finite values")
        if not math.isfinite(output_scale) or not math.isfinite(output_bias):
            raise QcnnArtifactError("QCNN output weights contain non-finite values")
        if torch is not None:
            self.conv_weights = torch.as_tensor(conv_weights, dtype=torch.float64)
            self.pool_weights = torch.as_tensor(pool_weights, dtype=torch.float64)
            self.output_scale = torch.tensor(output_scale, dtype=torch.float64)
            self.output_bias = torch.tensor(output_bias, dtype=torch.float64)
        else:
            self.conv_weights = conv_weights
            self.pool_weights = pool_weights
            self.output_scale = output_scale
            self.output_bias = output_bias


@dataclass(frozen=True)
class ProcessedImage:
    original_shape: list[int]
    original_mode: str
    pixels: np.ndarray
    angles: np.ndarray


def _mode_channels(mode: str) -> int:
    return {"1": 1, "L": 1, "I": 1, "F": 1, "RGB": 3, "RGBA": 4}.get(mode, len(mode))


def spatial_pool_angles(images: np.ndarray) -> np.ndarray:
    values = np.asarray(images, dtype=np.float64)
    if values.ndim != 3 or values.shape[1:] != (IMAGE_SIZE, IMAGE_SIZE):
        raise ValueError("spatial pooling expects N x 28 x 28 grayscale images")
    pooled = values.reshape(len(values), 2, 14, 2, 14).mean(axis=(2, 4)).reshape(len(values), 4)
    return np.pi * (2.0 * (pooled / 255.0) - 1.0)


def decode_image(payload: bytes, content_type: str) -> ProcessedImage:
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type not in SUPPORTED_IMAGE_TYPES:
        raise QcnnInputError("Only PNG and JPEG images are supported")
    if not payload:
        raise QcnnInputError("Image body is missing")
    if len(payload) > MAX_IMAGE_BYTES:
        raise QcnnInputError("Image must be 5 MB or smaller")
    try:
        with Image.open(io.BytesIO(payload)) as source:
            if source.width * source.height > MAX_DECODED_PIXELS:
                raise QcnnInputError("Decoded image dimensions are too large")
            source.verify()
        with Image.open(io.BytesIO(payload)) as source:
            source = ImageOps.exif_transpose(source)
            original_mode = source.mode
            original_shape = [source.height, source.width, _mode_channels(source.mode)]
            pixels = np.asarray(
                source.convert("L").resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.BILINEAR),
                dtype=np.uint8,
            ).copy()
    except QcnnInputError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise QcnnInputError("Uploaded file is not a readable PNG or JPEG image") from exc
    return ProcessedImage(
        original_shape,
        original_mode,
        pixels,
        spatial_pool_angles(pixels[None, ...])[0],
    )


class QcnnBundle:
    """Cached model, exact preprocessing metadata and real checkpoint inference."""

    def __init__(self, root: Path, manifest: dict[str, Any]) -> None:
        self.metadata_path = root / "qcnn/breastmnist/serving.json"
        self.checkpoint_path = root / "qcnn/breastmnist/serving-weights.json"
        self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        checkpoint = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        self._validate_metadata(checkpoint, manifest)
        self.model = ServingQCNN(int(self.metadata["architecture"]["qubits"]))
        self.model.load_state(checkpoint["model_state"])
        self.threshold = float(checkpoint["threshold"])
        self.run_id = str(checkpoint["run_id"])
        self.version = str(manifest["version"])
        self.preprocessing_hash = manifest["files"]["qcnn/breastmnist/serving.json"]["sha256"]

    def _validate_metadata(self, checkpoint: dict[str, Any], manifest: dict[str, Any]) -> None:
        required = {"model_type", "model_state", "config", "threshold", "run_id", "reducer"}
        if not isinstance(checkpoint, dict) or not required.issubset(checkpoint):
            raise QcnnArtifactError("QCNN checkpoint payload is incomplete")
        if checkpoint["model_type"] != "qcnn":
            raise QcnnArtifactError("Checkpoint is not a QCNN model")
        config = checkpoint["config"]
        checks = {
            "run id": (checkpoint["run_id"], self.metadata["runId"]),
            "dataset": (config.get("dataset"), "breastmnist"),
            "image size": (config.get("image_size"), 28),
            "reducer": (config.get("reducer"), "spatial_pool"),
            "reduced features": (config.get("reduced_features"), 4),
            "qubits": (config.get("qubits"), 4),
            "encoding": (config.get("encoding"), "angle_ry"),
            "stages": (config.get("stages"), 2),
            "threshold": (
                float(checkpoint["threshold"]),
                float(self.metadata["output"]["threshold"]),
            ),
        }
        for label, (actual, wanted) in checks.items():
            if actual != wanted:
                raise QcnnArtifactError(f"QCNN {label} mismatch")
        if not 0.0 <= float(checkpoint["threshold"]) <= 1.0:
            raise QcnnArtifactError("QCNN threshold is outside [0, 1]")
        if manifest.get("selection", {}).get("qcnn") != QCNN_MODEL_ID:
            raise QcnnArtifactError("Manifest does not select the verified QCNN bundle")

    def _score_angles(self, angles: np.ndarray) -> tuple[float, float, float]:
        expectation = float(self.model.expectation(np.asarray(angles, dtype=np.float64)))
        logit = float(self.model.output_scale) * expectation + float(self.model.output_bias)
        malignant_score = 1.0 / (1.0 + math.exp(-logit))
        if not math.isfinite(malignant_score) or not 0.0 <= malignant_score <= 1.0:
            raise QcnnArtifactError("QCNN produced an invalid score")
        return float(expectation), float(logit), malignant_score

    def predict_processed(self, processed: ProcessedImage) -> dict[str, Any]:
        started = perf_counter()
        expectation, logit, malignant_score = self._score_angles(processed.angles)
        region_names = ("top_left", "top_right", "bottom_left", "bottom_right")
        regions = []
        for index, name in enumerate(region_names):
            occluded = processed.angles.copy()
            occluded[index] = 0.0
            _, _, score_when_occluded = self._score_angles(occluded)
            regions.append(
                {
                    "id": name,
                    "row": index // 2,
                    "column": index % 2,
                    "modelScoreChange": malignant_score - score_when_occluded,
                    "scoreWhenOccluded": score_when_occluded,
                }
            )
        inference_time_ms = (perf_counter() - started) * 1000.0
        malignant = malignant_score >= self.threshold
        return {
            "model": {
                "id": QCNN_MODEL_ID,
                "name": "BreastMNIST QCNN",
                "version": self.version,
                "type": "quantum_convolutional",
            },
            "prediction": "malignant" if malignant else "normal_or_benign",
            "predictedClass": int(malignant),
            "classId": int(malignant),
            "probabilities": {
                "normal_or_benign": 1.0 - malignant_score,
                "malignant": malignant_score,
            },
            "malignantScore": malignant_score,
            "scoreType": "sigmoid_model_score_uncalibrated",
            "threshold": self.threshold,
            "measurementExpectationZ": expectation,
            "logit": logit,
            "inferenceTimeMs": inference_time_ms,
            "input": {
                "originalShape": processed.original_shape,
                "originalMode": processed.original_mode,
                "processedShape": [28, 28, 1],
            },
            "transformedFeatures": {
                f"angle_{index}": float(value) for index, value in enumerate(processed.angles)
            },
            "preprocessing": {
                "grayscale": True,
                "resize": "28x28 bilinear",
                "reduction": "2x2 spatial mean pooling over 14x14 regions",
                "scaling": "pi * (2 * pooled_intensity/255 - 1)",
                "versionSha256": self.preprocessing_hash,
            },
            "researchRunId": self.run_id,
            "researchSeed": int(self.metadata["research"]["seed"]),
            "backend": {
                "type": "ideal_simulator",
                "name": "PennyLane default.qubit analytic CPU simulation",
            },
            "quantum": {
                **self.metadata["quantum"],
                "circuitExecutionsThisPrediction": 5,
            },
            "explainability": {
                "method": "four_region_midgray_occlusion",
                "scope": "patient_level_model_behaviour",
                "reference": "Each 14x14 pooled region is replaced with mid-gray, equivalent to encoded angle 0, and the QCNN is rerun.",
                "regions": regions,
                "disclaimer": "Occlusion sensitivity shows how this model score changes under a synthetic perturbation; it is not lesion localization or medical causation.",
            },
            "warnings": [
                self.metadata["research"]["evidenceWarning"],
                "The sigmoid score is not calibrated as an individual clinical probability.",
            ],
            "disclaimer": QCNN_DISCLAIMER,
        }

    def predict_bytes(self, payload: bytes, content_type: str) -> dict[str, Any]:
        return self.predict_processed(decode_image(payload, content_type))

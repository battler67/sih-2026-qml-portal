"""Versioned inference from fitted research pipelines and calibrated estimators."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from time import perf_counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pennylane as qml
import sklearn

try:
    import pandas as pd
except ImportError:  # Vercel uses the lighter NumPy-only serving path.
    pd = None

from .errors import ArtifactError, InvalidInput
from .fh import FhStore
from .qcnn import QCNN_MODEL_ID, QcnnBundle

DISCLAIMER = "Research-use prototype; the model output is not a medical diagnosis or treatment recommendation."
FEATURES_FHS = (
    "SEX", "AGE", "EDUC", "CURSMOKE", "CIGPDAY", "BPMEDS", "PREVSTRK",
    "PREVHYP", "DIABETES", "TOTCHOL", "SYSBP", "DIABP", "BMI", "HEARTRTE", "GLUCOSE",
)
FEATURES_UCI = (
    "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach",
    "exang", "oldpeak", "slope", "ca", "thal",
)

# The Framingham bounds are the observed min/max in the audited eligible teaching cohort.
# They are input compatibility bounds, not clinical reference intervals.
FHS_FIELDS = (
    ("SEX", "Sex code", "code", 1, 2, "1 or 2"),
    ("AGE", "Age", "years", 32, 70, None),
    ("EDUC", "Education code", "code", 1, 4, "1 to 4"),
    ("CURSMOKE", "Current smoking", "0/1", 0, 1, "0 or 1"),
    ("CIGPDAY", "Cigarettes per day", "cigarettes/day", 0, 70, None),
    ("BPMEDS", "Blood pressure medication", "0/1", 0, 1, "0 or 1"),
    ("PREVSTRK", "Prior stroke", "0/1", 0, 1, "0 or 1"),
    ("PREVHYP", "Prior hypertension", "0/1", 0, 1, "0 or 1"),
    ("DIABETES", "Diabetes", "0/1", 0, 1, "0 or 1"),
    ("TOTCHOL", "Total cholesterol", "mg/dL", 113, 696, None),
    ("SYSBP", "Systolic blood pressure", "mmHg", 83.5, 295, None),
    ("DIABP", "Diastolic blood pressure", "mmHg", 50, 142.5, None),
    ("BMI", "Body mass index", "kg/m²", 15.54, 56.8, None),
    ("HEARTRTE", "Heart rate", "beats/min", 44, 143, None),
    ("GLUCOSE", "Glucose", "mg/dL", 40, 394, None),
)
UCI_FIELDS = (
    ("age", "Age", "years", 18, 100, None),
    ("sex", "Sex code", "0/1", 0, 1, "0 or 1"),
    ("cp", "Chest pain category", "code", 1, 4, "1 to 4"),
    ("trestbps", "Resting blood pressure", "mmHg", 70, 260, None),
    ("chol", "Serum cholesterol", "mg/dL", 80, 700, None),
    ("fbs", "Fasting blood sugar flag", "0/1", 0, 1, "0 or 1"),
    ("restecg", "Resting ECG category", "code", 0, 2, "0 to 2"),
    ("thalach", "Maximum heart rate", "beats/min", 50, 250, None),
    ("exang", "Exercise-induced angina", "0/1", 0, 1, "0 or 1"),
    ("oldpeak", "Exercise ST depression", "mm", -3, 10, None),
    ("slope", "ST slope category", "code", 1, 3, "1 to 3"),
    ("ca", "Major vessels count", "count", 0, 4, "0 to 4"),
    ("thal", "Thalassemia code", "code", 0, 7, "dataset code 0 to 7"),
)
FHS_DEMO = {
    "SEX": 2, "AGE": 48, "EDUC": 2, "CURSMOKE": 0, "CIGPDAY": 0,
    "BPMEDS": 0, "PREVSTRK": 0, "PREVHYP": 0, "DIABETES": 0,
    "TOTCHOL": 234, "SYSBP": 128, "DIABP": 82, "BMI": 25.41,
    "HEARTRTE": 75, "GLUCOSE": 78,
}
UCI_DEMO = {
    "age": 54, "sex": 1, "cp": 2, "trestbps": 130, "chol": 240,
    "fbs": 0, "restecg": 0, "thalach": 150, "exang": 0, "oldpeak": 1.0,
    "slope": 2, "ca": 0, "thal": 3,
}
MODELS = {
    "framingham-logistic-pca2": {
        "name": "Matched logistic regression", "workflow": "framingham",
        "type": "classical", "research_model": "logistic_pca2", "recommended": True,
        "limitation": "Teaching-data future-CHD benchmark; not clinical validation.",
    },
    "framingham-angle-qksvm-pca2": {
        "name": "Angle quantum-kernel SVM", "workflow": "framingham",
        "type": "quantum_kernel", "research_model": "angle_qksvm_pca2", "recommended": False,
        "limitation": "Exact simulator states and classical fidelity; no QPU execution or quantum speedup.",
    },
    "uci-rbf-svm": {
        "name": "Cleveland RBF SVM", "workflow": "uci",
        "type": "classical", "research_model": "rbf_svm", "recommended": True,
        "limitation": "Single-seed diagnostic smoke benchmark; no future-event or clinical validation.",
    },
    QCNN_MODEL_ID: {
        "name": "BreastMNIST QCNN", "workflow": "imaging",
        "type": "quantum_convolutional", "research_model": "qcnn", "recommended": False,
        "limitation": "32-image, two-epoch smoke run with weak held-out performance; research demonstration only.",
    },
}


def _title(model: str) -> str:
    aliases = {
        "oqsvm_pauli": "Pauli OQSVM",
        "hqmlp_preferred": "Preferred BCE HQMLP",
        "hqmlp_paper_ablation": "Paper-loss HQMLP",
        "qcnn": "Four-qubit QCNN",
        "mobilenet_v3_small_imagenet": "MobileNetV3-Small ImageNet",
        "resnet18_imagenet": "ResNet-18 ImageNet",
        "rbf_svm": "RBF SVM",
        "linear_svm": "Linear SVM",
        "classical_mlp": "Classical MLP",
        "reduced_mlp": "Reduced classical MLP",
        "small_cnn": "Small CNN",
    }
    return aliases.get(model, model.replace("_", " ").title().replace("Qksvm", "QKSVM").replace("Vqc", "VQC").replace("Hqmlp", "HQMLP"))


def _family(model: str, supplied: str | None = None) -> str:
    if supplied:
        return supplied
    lowered = model.lower()
    if "qcnn" in lowered:
        return "qcnn"
    if "qksvm" in lowered or "oqsvm" in lowered:
        return "quantum_kernel"
    if "vqc" in lowered or "hqmlp" in lowered:
        return "hybrid_qml"
    if "cnn" in lowered or "resnet" in lowered or "mobilenet" in lowered:
        return "deep_learning"
    return "classical"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def schema(model_id: str) -> dict[str, Any]:
    if model_id not in MODELS:
        raise KeyError(model_id)
    workflow = MODELS[model_id]["workflow"]
    if workflow == "imaging":
        return {
            "modelId": model_id,
            "workflow": workflow,
            "inputType": "image",
            "acceptedMediaTypes": ["image/png", "image/jpeg"],
            "maxBytes": 5 * 1024 * 1024,
            "processedShape": [28, 28, 1],
            "fields": [],
            "disclaimer": DISCLAIMER,
        }
    fields = FHS_FIELDS if workflow == "framingham" else UCI_FIELDS
    return {
        "modelId": model_id,
        "workflow": workflow,
        "fields": [
            {"name": name, "label": label, "unit": unit, "min": low, "max": high,
             "allowedCodes": allowed, "required": True, "nullable": workflow == "framingham"}
            for name, label, unit, low, high, allowed in fields
        ],
        "demo": dict(FHS_DEMO if workflow == "framingham" else UCI_DEMO),
        "demoLabel": "Synthetic teaching example; not a patient record",
        "rangeNote": "Framingham limits are observed teaching-cohort bounds, not medical reference ranges."
        if workflow == "framingham" else "UCI limits follow the research prediction validator.",
        "disclaimer": DISCLAIMER,
    }


def validate(model_id: str, features: Any) -> Any:
    if model_id not in MODELS:
        raise KeyError(model_id)
    if MODELS[model_id]["workflow"] == "imaging":
        raise InvalidInput("Use the QCNN image prediction endpoint for this model")
    if not isinstance(features, dict):
        raise InvalidInput("features must be a JSON object")
    fields = FHS_FIELDS if MODELS[model_id]["workflow"] == "framingham" else UCI_FIELDS
    names = {field[0] for field in fields}
    missing = names - set(features)
    unknown = set(features) - names
    if missing:
        raise InvalidInput(f"Missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise InvalidInput(f"Unknown or outcome fields: {', '.join(sorted(unknown))}")
    values = {}
    for name, _, _, low, high, allowed in fields:
        item = features[name]
        if item is None and MODELS[model_id]["workflow"] == "framingham":
            values[name] = np.nan
            continue
        if isinstance(item, bool):
            raise InvalidInput(f"{name} must be numeric")
        try:
            value = float(item)
        except (TypeError, ValueError) as exc:
            raise InvalidInput(f"{name} must be numeric") from exc
        if not math.isfinite(value) or not low <= value <= high:
            raise InvalidInput(f"{name} must be a finite number between {low} and {high}")
        if allowed is not None and value != int(value):
            raise InvalidInput(f"{name} must be an integer code")
        values[name] = value
    if pd is not None:
        return pd.DataFrame([values], columns=[field[0] for field in fields])
    return values


def _frame_matrix(frame: Any, order: tuple[str, ...] | list[str]) -> np.ndarray:
    if pd is not None and isinstance(frame, pd.DataFrame):
        return frame.loc[:, list(order)].to_numpy(dtype=float)
    return np.asarray([[frame[name] for name in order]], dtype=float)


def _frame_value(frame: Any, name: str) -> Any:
    if pd is not None and isinstance(frame, pd.DataFrame):
        return frame.iloc[0][name]
    return frame[name]


def _frame_items(frame: Any):
    if pd is not None and isinstance(frame, pd.DataFrame):
        return frame.iloc[0].items()
    return frame.items()


def _frame_with(frame: Any, name: str, value: float) -> Any:
    if pd is not None and isinstance(frame, pd.DataFrame):
        updated = frame.copy()
        updated.at[0, name] = value
        return updated
    return {**frame, name: value}


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(np.isnan(value))
    except TypeError:
        return False


class ModelStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        manifest_path = self.root / "manifest.json"
        evidence_path = self.root / "evidence.json"
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        if self.manifest.get("schemaVersion") != 1 or self.evidence.get("schemaVersion") != 1:
            raise ArtifactError("Unsupported QML artifact schema")
        if f"{sys.version_info.major}.{sys.version_info.minor}" != self.manifest["python"]:
            raise ArtifactError("Python version differs from the fitted bundle")
        if np.__version__ != self.manifest["researchEnvironment"]["numpy"]:
            raise ArtifactError("NumPy version differs from the fitted bundle")
        if sklearn.__version__ != self.manifest["researchEnvironment"]["sklearn"]:
            raise ArtifactError("scikit-learn version differs from the fitted bundle")
        if qml.__version__ != self.manifest["researchEnvironment"]["pennylane"]:
            raise ArtifactError("PennyLane version differs from the fitted bundle")
        for relative, entry in self.manifest["files"].items():
            path = (self.root / relative).resolve()
            if not path.is_relative_to(self.root) or not path.is_file() or _sha256(path) != entry["sha256"]:
                raise ArtifactError(f"Missing or corrupt QML artifact: {relative}")
        self.fhs_pipeline = joblib.load(self.root / "framingham/pca2_pipeline.joblib")
        if list(self.fhs_pipeline.feature_names_in_) != list(FEATURES_FHS):
            raise ArtifactError("Framingham preprocessing feature order mismatch")
        self.fhs_qsvm = joblib.load(self.root / "framingham/angle_qksvm_pca2/svm.joblib")
        self.fhs_qcal = joblib.load(self.root / "framingham/angle_qksvm_pca2/calibrator.joblib")
        with np.load(self.root / "framingham/angle_qksvm_pca2/training_states.npz", allow_pickle=False) as data:
            self.fhs_training_states = np.array(data["states"])
        if self.fhs_training_states.shape != (self.fhs_qsvm.n_features_in_, 4):
            raise ArtifactError("Quantum kernel training state shape mismatch")
        self.fhs_logistic = joblib.load(self.root / "framingham/logistic_pca2/model.joblib")
        self.fhs_lcal = joblib.load(self.root / "framingham/logistic_pca2/calibrator.joblib")
        self.uci_pipeline = joblib.load(self.root / "uci/selected_pipeline.joblib")
        if not isinstance(self.uci_pipeline, dict) or self.uci_pipeline.get("schemaVersion") != 1:
            raise ArtifactError("Unsupported UCI preprocessing bundle")
        self.uci_feature_order = list(self.uci_pipeline.get("featureOrder", ()))
        if self.uci_feature_order != ["thal", "cp", "thalach", "ca"]:
            raise ArtifactError("UCI preprocessing selected-feature order mismatch")
        if not {"imputer", "standardScaler"}.issubset(self.uci_pipeline):
            raise ArtifactError("UCI preprocessing bundle is incomplete")
        self.uci_rbf = joblib.load(self.root / "uci/rbf_svm.joblib")
        self.uci_cal = joblib.load(self.root / "uci/rbf_svm_platt.joblib")
        fhs_imputer = self.fhs_pipeline.named_steps.get("impute")
        if fhs_imputer is None or len(fhs_imputer.statistics_) != len(FEATURES_FHS):
            raise ArtifactError("Framingham explanation reference is unavailable")
        self.fhs_reference = dict(zip(FEATURES_FHS, map(float, fhs_imputer.statistics_)))
        if len(self.uci_pipeline["imputer"].statistics_) != len(self.uci_feature_order):
            raise ArtifactError("UCI explanation reference is unavailable")
        self.uci_reference = dict(
            zip(self.uci_feature_order, map(float, self.uci_pipeline["imputer"].statistics_))
        )
        qcnn_record = next(
            item for item in self.evidence["qcnn"]["runs"]
            if item["runId"] == self.manifest["qcnnRun"]
        )
        self._metrics = {
            "framingham-angle-qksvm-pca2": self._fhs_metric("angle_qksvm_pca2"),
            "framingham-logistic-pca2": self._fhs_metric("logistic_pca2"),
            "uci-rbf-svm": next(item for item in self.evidence["uci"]["models"] if item["model"] == "rbf_svm"),
            QCNN_MODEL_ID: {
                "model": "qcnn", "runId": qcnn_record["runId"], **qcnn_record["metrics"]
            },
        }
        self.qcnn = QcnnBundle(self.root, self.manifest)
        self._device = qml.device("default.qubit", wires=2)

        @qml.qnode(self._device)
        def state(x):
            qml.AngleEmbedding(x, wires=range(2), rotation="Y")
            return qml.state()

        self._state = state
        self.fh = FhStore(self.root / "fh")
        self._registry = self._build_registry()

    def _fhs_metric(self, model: str) -> dict:
        return next(item for item in self.evidence["framingham"]["perSeed"]
                    if item["model"] == model and item["seed"] == self.manifest["framinghamSeed"])

    def _entry(self, *, model_id: str, name: str, modality: str, workflow: str,
               family: str, availability: str, performance_tag: str, endpoint: str,
               evidence_maturity: str, metric: dict[str, Any], limitation: str,
               research_model: str) -> dict[str, Any]:
        return {
            "id": model_id,
            "name": name,
            "modality": modality,
            "workflow": workflow,
            "type": family,
            "family": family,
            "research_model": research_model,
            "availability": availability,
            "ready": availability == "runnable",
            "performanceTag": performance_tag,
            "evidenceMaturity": evidence_maturity,
            "endpoint": endpoint,
            "metric": metric,
            "limitation": limitation,
            "version": self.manifest["version"],
            "recommended": performance_tag == "best" and availability == "runnable",
        }

    def _build_registry(self) -> list[dict[str, Any]]:
        registry: list[dict[str, Any]] = []
        runnable = {
            "framingham-angle-qksvm-pca2", "framingham-logistic-pca2", "uci-rbf-svm",
        }
        for metric in self.evidence["framingham"]["summary"]:
            model = metric["model"]
            model_id = f"framingham-{model.replace('_', '-')}"
            family = _family(model)
            tag = "best" if model == "rbf_svm_full" else ("experimental" if family != "classical" else "moderate")
            registry.append(self._entry(
                model_id=model_id,
                name=_title(model),
                modality="ehr",
                workflow="framingham",
                family=family,
                availability="runnable" if model_id in runnable else "evidence_only",
                performance_tag=tag,
                endpoint="Educational future-CHD classification",
                evidence_maturity="three-seed teaching benchmark",
                metric=metric,
                limitation=self.evidence["framingham"]["limitation"],
                research_model=model,
            ))
        for metric in self.evidence["uci"]["models"]:
            model = metric["model"]
            model_id = f"uci-{model.replace('_', '-')}"
            family = _family(model, metric.get("family"))
            if model == "rbf_svm":
                tag = "best"
            elif model in {"logistic", "linear_svm", "random_forest"}:
                tag = "moderate"
            else:
                tag = "experimental"
            registry.append(self._entry(
                model_id=model_id,
                name=_title(model),
                modality="ehr",
                workflow="uci",
                family=family,
                availability="runnable" if model_id in runnable else "evidence_only",
                performance_tag=tag,
                endpoint="Heart-disease presence classification",
                evidence_maturity="single-seed diagnostic smoke test",
                metric=metric,
                limitation=self.evidence["uci"]["limitation"],
                research_model=model,
            ))

        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for run in self.evidence["qcnn"]["runs"]:
            grouped.setdefault((run["dataset"], run["model"]), []).append(run["metrics"])
        for (dataset, model), metrics in grouped.items():
            keys = {"auprc", "auroc", "balanced_accuracy", "sensitivity", "specificity", "training_time_seconds"}
            aggregate = {
                key: float(np.mean([item[key] for item in metrics if item.get(key) is not None]))
                for key in keys if any(item.get(key) is not None for item in metrics)
            }
            aggregate["model"] = model
            aggregate["runCount"] = len(metrics)
            if dataset == "breastmnist":
                tag = "best" if model == "mobilenet_v3_small_imagenet" else ("experimental" if model == "qcnn" else "moderate")
                maturity = "single small BreastMNIST smoke test"
            else:
                tag = "best" if model == "logistic" else "experimental"
                maturity = "two tiny WDBC control folds"
            model_id = QCNN_MODEL_ID if dataset == "breastmnist" and model == "qcnn" else f"imaging-{dataset}-{model.replace('_', '-')}"
            registry.append(self._entry(
                model_id=model_id,
                name=_title(model),
                modality="imaging",
                workflow=dataset,
                family=_family(model),
                availability="runnable" if model_id == QCNN_MODEL_ID else "evidence_only",
                performance_tag=tag,
                endpoint="Breast image classification" if dataset == "breastmnist" else "WDBC morphology control",
                evidence_maturity=maturity,
                metric=aggregate,
                limitation=self.evidence["qcnn"]["limitation"],
                research_model=model,
            ))

        fh_metrics = {item["model"]: item for item in self.fh.model_evidence["models"]}
        for model, name, family in (
            ("fh_logistic_rule_reproduction", "FH synthetic logistic rule-reproduction", "classical"),
            ("fh_angle_qksvm_rule_reproduction", "FH four-qubit Angle QKSVM rule-reproduction", "quantum_kernel"),
        ):
            registry.append(self._entry(
                model_id=model.replace("_", "-"),
                name=name,
                modality="genomics",
                workflow="fh_synthetic",
                family=family,
                availability="runnable",
                performance_tag="experimental",
                endpoint="Synthetic FH referral-rule reproduction",
                evidence_maturity="deterministic synthetic functionality benchmark",
                metric=fh_metrics[model],
                limitation=self.fh.model_evidence["limitation"],
                research_model=model,
            ))
        return sorted(registry, key=lambda item: (item["modality"], item["workflow"], item["name"]))

    def models(self, modality: str | None = None) -> list[dict]:
        return [item for item in self._registry if modality is None or item["modality"] == modality]

    def evidence_for(self, model_id: str) -> dict:
        entry = next((item for item in self._registry if item["id"] == model_id), None)
        if entry is None:
            raise KeyError(model_id)
        return {
            "modelId": model_id,
            "model": entry,
            "selectedRun": entry["metric"],
            "comparisons": self.evidence,
            "disclaimer": DISCLAIMER,
        }

    def predict_qcnn(self, payload: bytes, content_type: str) -> dict:
        return self.qcnn.predict_bytes(payload, content_type)

    def _score_tabular(self, model_id: str, frame: Any) -> dict[str, Any]:
        meta = MODELS[model_id]
        if meta["workflow"] == "framingham":
            source = frame if pd is not None and isinstance(frame, pd.DataFrame) else _frame_matrix(frame, FEATURES_FHS)
            reduced = self.fhs_pipeline.transform(source)
            if meta["type"] == "quantum_kernel":
                state = np.asarray(self._state(reduced[0]))
                kernel = np.clip(
                    np.abs(state.conj() @ self.fhs_training_states.T) ** 2, 0, 1
                ).reshape(1, -1)
                score = float(self.fhs_qsvm.decision_function(kernel)[0])
                calibration = self.fhs_qcal
                backend = {
                    "type": "ideal_simulator",
                    "name": "PennyLane default.qubit + classical cached-state fidelity",
                }
                resources = {
                    "qubits": 2,
                    "shots": None,
                    "circuitDepth": None,
                    "circuitExecutionsThisPrediction": 1,
                }
            else:
                score = float(self.fhs_logistic.decision_function(reduced)[0])
                calibration = self.fhs_lcal
                backend = {"type": "classical", "name": "scikit-learn"}
                resources = {"qubits": None, "shots": None, "circuitDepth": None}
            transformed = {
                "PCA component 1": float(reduced[0, 0]),
                "PCA component 2": float(reduced[0, 1]),
            }
            run_id = self.manifest["framinghamRun"]
        else:
            selected = (
                frame.loc[:, self.uci_feature_order]
                if pd is not None and isinstance(frame, pd.DataFrame)
                else _frame_matrix(frame, self.uci_feature_order)
            )
            imputed = self.uci_pipeline["imputer"].transform(selected)
            reduced = np.asarray(
                self.uci_pipeline["standardScaler"].transform(imputed), dtype=float
            )
            score = float(self.uci_rbf.decision_function(reduced)[0])
            calibration = self.uci_cal
            backend = {"type": "classical", "name": "scikit-learn"}
            resources = {"qubits": None, "shots": None, "circuitDepth": None}
            transformed = {name: float(_frame_value(frame, name)) for name in self.uci_feature_order}
            run_id = self.manifest["uciRun"]
        probability = float(calibration.predict_proba(np.array([[score]]))[0, 1])
        return {
            "score": score,
            "probability": probability,
            "transformed": transformed,
            "backend": backend,
            "resources": resources,
            "runId": run_id,
        }

    def _explain_tabular(
        self, model_id: str, frame: Any, baseline_probability: float
    ) -> dict[str, Any]:
        meta = MODELS[model_id]
        fields = FHS_FIELDS if meta["workflow"] == "framingham" else UCI_FIELDS
        field_metadata = {item[0]: item for item in fields}
        references = (
            self.fhs_reference if meta["workflow"] == "framingham" else self.uci_reference
        )
        contributions = []
        for name, reference in references.items():
            perturbed = _frame_with(frame, name, reference)
            perturbed_probability = self._score_tabular(model_id, perturbed)["probability"]
            value = _frame_value(frame, name)
            delta = baseline_probability - perturbed_probability
            contributions.append(
                {
                    "feature": name,
                    "label": field_metadata[name][1],
                    "unit": field_metadata[name][2],
                    "inputValue": None if _is_missing(value) else float(value),
                    "referenceValue": reference,
                    "modelScoreChange": delta,
                    "scoreAtReference": perturbed_probability,
                    "direction": "raises_model_score"
                    if delta > 0
                    else "lowers_model_score"
                    if delta < 0
                    else "no_change",
                }
            )
        contributions.sort(key=lambda item: abs(item["modelScoreChange"]), reverse=True)
        return {
            "method": "single_feature_training_median_perturbation",
            "scope": "patient_level_model_behaviour",
            "reference": "Each used input is replaced one at a time by its training-set median and the complete saved pipeline is rerun.",
            "features": contributions,
            "disclaimer": "Perturbation contributions describe this fitted model around this input. They are not medical causation and can be affected by correlated features.",
        }

    def predict(self, model_id: str, features: Any) -> dict:
        if model_id == QCNN_MODEL_ID:
            raise InvalidInput("Use the QCNN image prediction endpoint for this model")
        frame = validate(model_id, features)
        meta = MODELS[model_id]
        started = perf_counter()
        result = self._score_tabular(model_id, frame)
        explanation = self._explain_tabular(model_id, frame, result["probability"])
        resources = dict(result["resources"])
        if meta["type"] == "quantum_kernel":
            resources["circuitExecutionsThisPrediction"] = 1 + len(explanation["features"])
        inference_time_ms = (perf_counter() - started) * 1000.0
        threshold = float(
            self._metrics[model_id].get(
                "selected_threshold", self._metrics[model_id].get("threshold")
            )
        )
        elevated = bool(result["probability"] >= threshold)
        return {
            "prediction": "elevated research risk score" if elevated else "lower research risk score",
            "predictedClass": int(elevated),
            "score": result["score"],
            "scoreType": "decision_value",
            "calibratedProbability": result["probability"],
            "threshold": threshold,
            "inferenceTimeMs": inference_time_ms,
            "model": {
                "id": model_id,
                "name": meta["name"],
                "version": self.manifest["version"],
                "type": meta["type"],
            },
            "preprocessingVersion": self.manifest["files"][
                "framingham/pca2_pipeline.joblib"
                if meta["workflow"] == "framingham"
                else "uci/selected_pipeline.joblib"
            ]["sha256"],
            "researchRunId": result["runId"],
            "researchSeed": self.manifest["framinghamSeed"]
            if meta["workflow"] == "framingham"
            else 7,
            "backend": result["backend"],
            "resources": resources,
            "inputFeatures": {
                key: None if _is_missing(value) else float(value)
                for key, value in _frame_items(frame)
            },
            "transformedFeatures": result["transformed"],
            "explainability": explanation,
            "warnings": [
                meta["limitation"],
                "Benchmark intervals describe groups, not confidence in this individual result.",
            ],
            "disclaimer": DISCLAIMER,
        }

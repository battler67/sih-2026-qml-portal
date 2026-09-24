"""Synthetic-only familial hypercholesterolemia evidence and referral pathway."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pennylane as qml

from .errors import ArtifactError, InvalidInput


FH_DISCLAIMER = (
    "Synthetic research demonstration only; this output is not a diagnosis, genetic test, "
    "medical advice or treatment recommendation."
)
CLASSIFICATION_STRENGTH = {
    "pathogenic": 1.0,
    "likely_pathogenic": 0.75,
    "uncertain_significance": 0.25,
    "likely_benign": 0.0,
    "benign": 0.0,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def fh_schema(snapshot: dict[str, Any]) -> dict[str, Any]:
    records = snapshot["records"]
    return {
        "schemaVersion": 1,
        "syntheticOnly": True,
        "population": "adults_18_plus",
        "snapshotId": snapshot["snapshotId"],
        "variantOptions": [
            {
                "id": item["id"],
                "gene": item["gene"],
                "classification": item["classification"],
                "label": f"{item['gene']} · {item['classification'].replace('_', ' ')}",
            }
            for item in records
        ],
        "examples": [
            {
                "id": "high-evidence",
                "label": "LDLR evidence with raised LDL-C",
                "record": {
                    "synthetic": True,
                    "exampleId": "synthetic-fh-high-evidence",
                    "ageYears": 34,
                    "sexAtBirth": "female",
                    "untreatedLdlCMgDl": 232,
                    "familyHistoryPrematureAscvd": True,
                    "familyHistoryHighLdl": True,
                    "personalHistoryPrematureAscvd": False,
                    "tendonXanthomas": False,
                    "cornealArcusBefore45": False,
                    "secondaryCausesReviewed": True,
                    "variantId": "SYNTHETIC_LDLR_001",
                },
            },
            {
                "id": "uncertain",
                "label": "LDLR uncertain evidence",
                "record": {
                    "synthetic": True,
                    "exampleId": "synthetic-fh-vus",
                    "ageYears": 42,
                    "sexAtBirth": "male",
                    "untreatedLdlCMgDl": 178,
                    "familyHistoryPrematureAscvd": True,
                    "familyHistoryHighLdl": False,
                    "personalHistoryPrematureAscvd": False,
                    "tendonXanthomas": False,
                    "cornealArcusBefore45": False,
                    "secondaryCausesReviewed": True,
                    "variantId": "SYNTHETIC_LDLR_VUS_001",
                },
            },
            {
                "id": "phenotype-only",
                "label": "High LDL-C without qualifying genomic evidence",
                "record": {
                    "synthetic": True,
                    "exampleId": "synthetic-fh-phenotype",
                    "ageYears": 51,
                    "sexAtBirth": "female",
                    "untreatedLdlCMgDl": 286,
                    "familyHistoryPrematureAscvd": True,
                    "familyHistoryHighLdl": True,
                    "personalHistoryPrematureAscvd": False,
                    "tendonXanthomas": False,
                    "cornealArcusBefore45": False,
                    "secondaryCausesReviewed": True,
                    "variantId": "SYNTHETIC_LDLR_BENIGN_001",
                },
            },
        ],
        "disclaimer": FH_DISCLAIMER,
    }


def _boolean(record: dict[str, Any], name: str) -> bool:
    value = record.get(name)
    if not isinstance(value, bool):
        raise InvalidInput(f"{name} must be true or false")
    return value


def validate_fh(record: Any, snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(record, dict):
        raise InvalidInput("record must be a JSON object")
    expected = {
        "synthetic", "exampleId", "ageYears", "sexAtBirth", "untreatedLdlCMgDl",
        "familyHistoryPrematureAscvd", "familyHistoryHighLdl",
        "personalHistoryPrematureAscvd", "tendonXanthomas", "cornealArcusBefore45",
        "secondaryCausesReviewed", "variantId",
    }
    missing = expected - set(record)
    unknown = set(record) - expected
    if missing:
        raise InvalidInput(f"Missing FH fields: {', '.join(sorted(missing))}")
    if unknown:
        raise InvalidInput(f"Unknown FH fields: {', '.join(sorted(unknown))}")
    if record["synthetic"] is not True:
        raise InvalidInput("The public FH pathway accepts synthetic records only")
    if not isinstance(record["exampleId"], str) or not record["exampleId"].startswith("synthetic-"):
        raise InvalidInput("exampleId must identify a synthetic example")
    age = record["ageYears"]
    ldl = record["untreatedLdlCMgDl"]
    if isinstance(age, bool) or not isinstance(age, (int, float)) or not 18 <= age <= 100:
        raise InvalidInput("ageYears must be between 18 and 100")
    if isinstance(ldl, bool) or not isinstance(ldl, (int, float)) or not math.isfinite(ldl) or not 40 <= ldl <= 700:
        raise InvalidInput("untreatedLdlCMgDl must be between 40 and 700")
    if record["sexAtBirth"] not in {"female", "male", "not_specified"}:
        raise InvalidInput("sexAtBirth must be female, male or not_specified")
    for name in (
        "familyHistoryPrematureAscvd", "familyHistoryHighLdl",
        "personalHistoryPrematureAscvd", "tendonXanthomas", "cornealArcusBefore45",
        "secondaryCausesReviewed",
    ):
        _boolean(record, name)
    evidence = next((item for item in snapshot["records"] if item["id"] == record["variantId"]), None)
    if evidence is None:
        raise InvalidInput("variantId is not present in the pinned synthetic evidence snapshot")
    return record, evidence


def dlcn_breakdown(record: dict[str, Any], evidence: dict[str, Any]) -> dict[str, int]:
    ldl = float(record["untreatedLdlCMgDl"])
    if ldl >= 325:
        ldl_points = 8
    elif ldl >= 251:
        ldl_points = 5
    elif ldl >= 191:
        ldl_points = 3
    elif ldl >= 155:
        ldl_points = 1
    else:
        ldl_points = 0
    family_points = 1 if (
        record["familyHistoryPrematureAscvd"] or record["familyHistoryHighLdl"]
    ) else 0
    history_points = 2 if record["personalHistoryPrematureAscvd"] else 0
    examination_points = 6 if record["tendonXanthomas"] else (4 if record["cornealArcusBefore45"] else 0)
    dna_points = 8 if evidence["classification"] in {"pathogenic", "likely_pathogenic"} else 0
    return {
        "familyHistory": family_points,
        "clinicalHistory": history_points,
        "physicalExamination": examination_points,
        "untreatedLdlC": ldl_points,
        "syntheticDnaEvidence": dna_points,
    }


class FhStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        self.snapshot = json.loads((self.root / "evidence_snapshot.json").read_text(encoding="utf-8"))
        self.model_evidence = json.loads((self.root / "model_evidence.json").read_text(encoding="utf-8"))
        if self.manifest.get("schemaVersion") != 1 or self.snapshot.get("schemaVersion") != 1:
            raise ArtifactError("Unsupported synthetic FH artifact schema")
        for name, metadata in self.manifest["files"].items():
            path = (self.root / name).resolve()
            if not path.is_relative_to(self.root) or not path.is_file() or _sha256(path) != metadata["sha256"]:
                raise ArtifactError(f"Missing or corrupt synthetic FH artifact: {name}")
        self.scaler = joblib.load(self.root / "feature_scaler.joblib")
        self.logistic = joblib.load(self.root / "logistic_rule_reproduction.joblib")
        self.qksvm = joblib.load(self.root / "angle_qksvm_rule_reproduction.joblib")
        with np.load(self.root / "angle_qksvm_training_states.npz", allow_pickle=False) as data:
            self.training_states = np.asarray(data["states"], dtype=float)
        self.device = qml.device("default.qubit", wires=4)

        @qml.qnode(self.device)
        def state(values):
            qml.AngleEmbedding(values, wires=range(4), rotation="Y")
            return qml.state()

        self._state = state

    def analyze(self, raw_record: Any) -> dict[str, Any]:
        record, evidence = validate_fh(raw_record, self.snapshot)
        breakdown = dlcn_breakdown(record, evidence)
        score = sum(breakdown.values())
        if score >= 9:
            category = "definite_suspicion"
        elif score >= 6:
            category = "probable_suspicion"
        elif score >= 3:
            category = "possible_suspicion"
        else:
            category = "unlikely_by_entered_criteria"

        classification = evidence["classification"]
        if float(record["untreatedLdlCMgDl"]) >= 400:
            referral = "specialist_review_priority"
        elif score >= 6 or classification in {"pathogenic", "likely_pathogenic"}:
            referral = "fh_specialist_or_genetic_counselling_referral"
        elif classification == "uncertain_significance":
            referral = "uncertain_evidence_review"
        elif score >= 3:
            referral = "routine_clinical_review"
        else:
            referral = "no_fh_specific_signal_in_this_demo"
        if not record["secondaryCausesReviewed"] and referral not in {
            "specialist_review_priority", "fh_specialist_or_genetic_counselling_referral"
        }:
            referral = "insufficient_information"

        evidence_strength = CLASSIFICATION_STRENGTH[classification]
        family_signal = float(record["familyHistoryPrematureAscvd"] or record["familyHistoryHighLdl"])
        phenotype_signal = min(
            float(record["personalHistoryPrematureAscvd"])
            + float(record["tendonXanthomas"])
            + float(record["cornealArcusBefore45"]),
            2.0,
        ) / 2.0
        raw_features = np.array([[
            float(record["untreatedLdlCMgDl"]), evidence_strength, family_signal, phenotype_signal,
        ]])
        scaled = self.scaler.transform(raw_features)
        logistic_probability = float(self.logistic.predict_proba(scaled)[0, 1])
        angles = np.clip(scaled, -3.0, 3.0) * (np.pi / 3.0)
        state = np.asarray(self._state(angles[0])).real.astype(float, copy=False)
        qkernel = np.clip(np.abs(state.conj() @ self.training_states.T) ** 2, 0.0, 1.0).reshape(1, -1)
        qksvm_probability = float(self.qksvm.predict_proba(qkernel)[0, 1])

        metric_by_id = {item["model"]: item for item in self.model_evidence["models"]}
        return {
            "synthetic": True,
            "inputQuality": {
                "status": "valid_synthetic_record",
                "secondaryCausesReviewed": record["secondaryCausesReviewed"],
            },
            "evidence": {
                **evidence,
                "snapshotId": self.snapshot["snapshotId"],
                "snapshotCreatedAt": self.snapshot["createdAt"],
                "isQualifyingPositive": classification in {"pathogenic", "likely_pathogenic"},
                "interpretation": (
                    "Qualifying synthetic FH evidence match."
                    if classification in {"pathogenic", "likely_pathogenic"}
                    else "No qualifying pathogenic or likely pathogenic evidence match."
                ),
            },
            "clinicalSuspicion": {
                "method": "educational DLCN reproduction",
                "score": score,
                "category": category,
                "breakdown": breakdown,
            },
            "referral": {
                "category": referral,
                "requiresHumanReview": referral != "no_fh_specific_signal_in_this_demo",
                "message": _referral_message(referral),
            },
            "researchModels": [
                {
                    "id": "fh-logistic-rule-reproduction",
                    "name": "FH synthetic logistic rule-reproduction",
                    "type": "classical",
                    "performanceTag": "experimental",
                    "probability": logistic_probability,
                    "threshold": 0.5,
                    "metrics": metric_by_id["fh_logistic_rule_reproduction"],
                    "resources": {"qubits": None, "backend": "scikit-learn"},
                },
                {
                    "id": "fh-angle-qksvm-rule-reproduction",
                    "name": "FH four-qubit Angle QKSVM rule-reproduction",
                    "type": "quantum_kernel",
                    "performanceTag": "experimental",
                    "probability": qksvm_probability,
                    "threshold": 0.5,
                    "metrics": metric_by_id["fh_angle_qksvm_rule_reproduction"],
                    "resources": {
                        "qubits": 4,
                        "shots": None,
                        "backend": "PennyLane default.qubit exact statevector",
                        "circuitExecutionsThisPrediction": 1,
                    },
                },
            ],
            "derivedFeatures": {
                "untreatedLdlCMgDl": float(record["untreatedLdlCMgDl"]),
                "genomicEvidenceStrength": evidence_strength,
                "familyHistorySignal": family_signal,
                "phenotypeSignal": phenotype_signal,
            },
            "warnings": [
                self.model_evidence["limitation"],
                "A negative or uncertain synthetic variant does not exclude FH.",
                "Confirmatory clinical assessment and qualified review are outside this prototype.",
            ],
            "disclaimer": FH_DISCLAIMER,
        }


def _referral_message(category: str) -> str:
    messages = {
        "specialist_review_priority": "The entered synthetic pattern warrants priority specialist review in a real clinical workflow.",
        "fh_specialist_or_genetic_counselling_referral": "The synthetic evidence supports referral to an FH specialist or genetic counsellor for confirmation.",
        "uncertain_evidence_review": "Uncertain evidence must not be treated as positive; qualified review may be appropriate.",
        "routine_clinical_review": "The synthetic phenotype supports routine clinical review and repeat/confirmatory measurements.",
        "insufficient_information": "Review possible secondary causes and complete the clinical context before interpreting this pattern.",
        "no_fh_specific_signal_in_this_demo": "No FH-specific signal was produced from these synthetic fields; this is not an all-clear.",
    }
    return messages[category]

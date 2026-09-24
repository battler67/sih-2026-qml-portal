"""Build the versioned synthetic FH rule-reproduction artifacts.

This script never reads a patient record. It produces deterministic educational
artifacts for plumbing tests and must not be used to claim clinical performance.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qml_inference" / "artifacts" / "v1" / "fh"
SEED = 26139


def angle_states(features: np.ndarray) -> np.ndarray:
    states = []
    for row in features:
        state = np.array([1.0])
        for value in row:
            state = np.kron(state, [np.cos(value / 2), np.sin(value / 2)])
        states.append(state)
    return np.asarray(states, dtype=np.float64)


def kernel(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return np.clip(np.abs(left @ right.T) ** 2, 0.0, 1.0)


def make_data(count: int = 360) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(SEED)
    ldl = np.clip(rng.normal(205, 68, count), 80, 430)
    evidence = rng.choice([0.0, 0.25, 0.75, 1.0], count, p=[0.48, 0.18, 0.17, 0.17])
    family = rng.binomial(1, 0.42, count).astype(float)
    phenotype = np.clip(
        rng.binomial(1, 0.18, count)
        + rng.binomial(1, 0.08, count)
        + rng.binomial(1, 0.05, count),
        0,
        2,
    ) / 2
    features = np.column_stack([ldl, evidence, family, phenotype])

    # Synthetic referral-rule reproduction, not a biological ground truth label.
    ldl_points = np.select(
        [ldl >= 325, ldl >= 251, ldl >= 191, ldl >= 155],
        [8, 5, 3, 1],
        default=0,
    )
    genomic_points = np.where(evidence >= 0.75, 8, 0)
    family_points = family
    phenotype_points = np.rint(phenotype * 6)
    labels = ((ldl_points + genomic_points + family_points + phenotype_points) >= 6).astype(int)
    return features, labels


def metric(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    predicted = (probabilities >= 0.5).astype(int)
    return {
        "auprc": float(average_precision_score(y_true, probabilities)),
        "auroc": float(roc_auc_score(y_true, probabilities)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predicted)),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    features, labels = make_data()
    indices = np.random.default_rng(SEED).permutation(len(labels))
    train_idx, test_idx = indices[:240], indices[240:]
    train_x, test_x = features[train_idx], features[test_idx]
    train_y, test_y = labels[train_idx], labels[test_idx]

    scaler = StandardScaler().fit(train_x)
    train_scaled = scaler.transform(train_x)
    test_scaled = scaler.transform(test_x)

    logistic = LogisticRegression(C=1.0, max_iter=2000, random_state=SEED).fit(train_scaled, train_y)
    logistic_probability = logistic.predict_proba(test_scaled)[:, 1]

    # Bound each feature to an angle for a four-qubit separable AngleEmbedding.
    train_angles = np.clip(train_scaled, -3.0, 3.0) * (np.pi / 3.0)
    test_angles = np.clip(test_scaled, -3.0, 3.0) * (np.pi / 3.0)
    train_states = angle_states(train_angles)
    test_states = angle_states(test_angles)
    qksvm = SVC(C=1.0, kernel="precomputed", probability=True, random_state=SEED)
    qksvm.fit(kernel(train_states, train_states), train_y)
    qksvm_probability = qksvm.predict_proba(kernel(test_states, train_states))[:, 1]

    joblib.dump(scaler, OUT / "feature_scaler.joblib")
    joblib.dump(logistic, OUT / "logistic_rule_reproduction.joblib")
    joblib.dump(qksvm, OUT / "angle_qksvm_rule_reproduction.joblib")
    np.savez_compressed(OUT / "angle_qksvm_training_states.npz", states=train_states)

    evidence = {
        "schemaVersion": 1,
        "experiment": "synthetic_fh_rule_reproduction",
        "seed": SEED,
        "trainCount": int(len(train_idx)),
        "testCount": int(len(test_idx)),
        "positiveTrainCount": int(train_y.sum()),
        "positiveTestCount": int(test_y.sum()),
        "primaryMetric": "auprc",
        "featureOrder": [
            "untreated_ldl_c_mg_dl",
            "genomic_evidence_strength",
            "family_history_signal",
            "phenotype_signal",
        ],
        "models": [
            {
                "model": "fh_logistic_rule_reproduction",
                "family": "classical",
                **metric(test_y, logistic_probability),
            },
            {
                "model": "fh_angle_qksvm_rule_reproduction",
                "family": "quantum_kernel",
                "qubits": 4,
                "kernelMethod": "exact_statevector_fidelity",
                **metric(test_y, qksvm_probability),
            },
        ],
        "limitation": "Metrics measure reproduction of synthetic referral rules, not FH detection or clinical validity.",
    }
    (OUT / "model_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    files = [
        "feature_scaler.joblib",
        "logistic_rule_reproduction.joblib",
        "angle_qksvm_rule_reproduction.joblib",
        "angle_qksvm_training_states.npz",
        "model_evidence.json",
        "evidence_snapshot.json",
    ]
    bundle = {
        "schemaVersion": 1,
        "version": "synthetic-fh-v1",
        "seed": SEED,
        "files": {name: {"sha256": sha256(OUT / name), "bytes": (OUT / name).stat().st_size} for name in files},
    }
    (OUT / "manifest.json").write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "evidence": evidence}, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import io
import json
import shutil
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image

from qml_inference.model import ArtifactError, InvalidInput, MODELS, ModelStore, schema, validate
from qml_inference.server import create_handler


BUNDLE = Path(__file__).resolve().parents[1] / "artifacts/v1"


class BundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = ModelStore(BUNDLE)

    def test_all_promoted_models_run_synthetic_examples(self):
        for model_id in MODELS:
            if model_id == "breastmnist-qcnn":
                continue
            with self.subTest(item=model_id):
                output = self.store.predict(model_id, schema(model_id)["demo"])
                self.assertEqual(output["model"]["id"], model_id)
                self.assertEqual(len(output["preprocessingVersion"]), 64)
                self.assertGreaterEqual(output["calibratedProbability"], 0)
                self.assertLessEqual(output["calibratedProbability"], 1)
                self.assertIn("not a medical diagnosis", output["disclaimer"])
                self.assertGreater(output["inferenceTimeMs"], 0)
                self.assertEqual(
                    output["explainability"]["method"],
                    "single_feature_training_median_perturbation",
                )
                expected_features = 15 if MODELS[model_id]["workflow"] == "framingham" else 4
                self.assertEqual(len(output["explainability"]["features"]), expected_features)

    def test_registry_includes_every_track_without_making_all_models_runnable(self):
        models = self.store.models()
        self.assertEqual(len(models), 38)
        self.assertEqual({item["modality"] for item in models}, {"ehr", "genomics", "imaging"})
        self.assertTrue(any(item["availability"] == "evidence_only" for item in models))
        self.assertTrue(any(item["performanceTag"] == "best" for item in models))
        qcnn = next(item for item in models if item["id"] == "breastmnist-qcnn")
        self.assertEqual(qcnn["performanceTag"], "experimental")
        self.assertEqual(qcnn["availability"], "runnable")

    def test_synthetic_fh_evidence_referral_and_vus_boundaries(self):
        high = self.store.fh.analyze({
            "synthetic": True, "exampleId": "synthetic-test-high", "ageYears": 34,
            "sexAtBirth": "female", "untreatedLdlCMgDl": 232,
            "familyHistoryPrematureAscvd": True, "familyHistoryHighLdl": True,
            "personalHistoryPrematureAscvd": False, "tendonXanthomas": False,
            "cornealArcusBefore45": False, "secondaryCausesReviewed": True,
            "variantId": "SYNTHETIC_LDLR_001",
        })
        self.assertTrue(high["synthetic"])
        self.assertTrue(high["evidence"]["isQualifyingPositive"])
        self.assertEqual(high["referral"]["category"], "fh_specialist_or_genetic_counselling_referral")
        self.assertEqual(len(high["researchModels"]), 2)
        example = {
            "synthetic": True, "exampleId": "synthetic-test-vus", "ageYears": 42,
            "sexAtBirth": "male", "untreatedLdlCMgDl": 140,
            "familyHistoryPrematureAscvd": False, "familyHistoryHighLdl": False,
            "personalHistoryPrematureAscvd": False, "tendonXanthomas": False,
            "cornealArcusBefore45": False, "secondaryCausesReviewed": True,
            "variantId": "SYNTHETIC_LDLR_VUS_001",
        }
        vus = self.store.fh.analyze(example)
        self.assertFalse(vus["evidence"]["isQualifyingPositive"])
        self.assertEqual(vus["referral"]["category"], "uncertain_evidence_review")
        with self.assertRaisesRegex(InvalidInput, "synthetic records only"):
            self.store.fh.analyze({**example, "synthetic": False})

    def test_schema_rejects_unknown_outcome_missing_and_bad_codes(self):
        item = schema("framingham-angle-qksvm-pca2")["demo"]
        with self.assertRaisesRegex(InvalidInput, "Unknown or outcome"):
            validate("framingham-angle-qksvm-pca2", {**item, "TIMECHD": 1})
        with self.assertRaisesRegex(InvalidInput, "Missing fields"):
            validate("framingham-angle-qksvm-pca2", {k: v for k, v in item.items() if k != "AGE"})
        with self.assertRaisesRegex(InvalidInput, "integer code"):
            validate("framingham-angle-qksvm-pca2", {**item, "SEX": 1.5})

    def test_corrupt_artifacts_block_startup(self):
        targets = (
            "framingham/pca2_pipeline.joblib",
            "qcnn/breastmnist/checkpoint.pt",
        )
        for target in targets:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                copy = Path(directory) / "bundle"
                shutil.copytree(BUNDLE, copy)
                (copy / target).write_bytes(b"broken")
                with self.assertRaisesRegex(ArtifactError, "corrupt"):
                    ModelStore(copy)

    def test_saved_demo_scores_remain_stable(self):
        expected = {
            "framingham-angle-qksvm-pca2": 0.056141051440025694,
            "framingham-logistic-pca2": 0.04850663739573488,
            "uci-rbf-svm": 0.25860280113179784,
        }
        for model_id, probability in expected.items():
            with self.subTest(model_id=model_id):
                value = self.store.predict(model_id, schema(model_id)["demo"])["calibratedProbability"]
                self.assertAlmostEqual(value, probability, places=8)

    def test_uci_preprocessing_bundle_has_no_research_package_dependency(self):
        artifact = BUNDLE / "uci/selected_pipeline.joblib"
        self.assertNotIn(b"qml_research", artifact.read_bytes())
        self.assertEqual(self.store.uci_feature_order, ["thal", "cp", "thalach", "ca"])


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = ModelStore(BUNDLE)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(cls.store, {"http://127.0.0.1:8080"}))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/api/qml/v1"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def call_image(
        self,
        payload: bytes,
        content_type: str = "image/png",
        declared_length: int | None = None,
    ):
        headers = {"Content-Type": content_type, "Origin": "http://127.0.0.1:8080"}
        if declared_length is not None:
            headers["Content-Length"] = str(declared_length)
        request = Request(
            self.base + "/qcnn/breastmnist/predict",
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                return response.status, dict(response.headers), json.load(response)
        except HTTPError as exc:
            return exc.code, dict(exc.headers), json.load(exc)

    def call(self, path: str, body: dict | None = None):
        request = Request(
            self.base + path,
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers={"Content-Type": "application/json", "Origin": "http://127.0.0.1:8080"},
        )
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, dict(response.headers), json.load(response)
        except HTTPError as exc:
            return exc.code, dict(exc.headers), json.load(exc)

    def test_demo_journey_models_schema_predict_evidence_report(self):
        status, _, models = self.call("/models")
        self.assertEqual(status, 200)
        self.assertEqual(len(models["models"]), 38)
        status, _, modalities = self.call("/lab/modalities")
        self.assertEqual(status, 200)
        imaging = next(item for item in modalities["modalities"] if item["id"] == "imaging")
        self.assertEqual(imaging["status"], "available")
        self.assertEqual(imaging["modelCount"], len(self.store.models("imaging")))
        model_id = "framingham-angle-qksvm-pca2"
        status, _, input_schema = self.call(f"/models/{model_id}/schema")
        self.assertEqual(status, 200)
        request = {"modelId": model_id, "features": input_schema["demo"]}
        status, headers, prediction = self.call("/predict", request)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(prediction["backend"]["type"], "ideal_simulator")
        self.assertEqual(prediction["resources"]["circuitExecutionsThisPrediction"], 16)
        self.assertEqual(len(prediction["explainability"]["features"]), 15)
        status, _, evidence = self.call(f"/models/{model_id}/evidence")
        self.assertEqual(status, 200)
        self.assertEqual(evidence["selectedRun"]["model"], "angle_qksvm_pca2")
        status, _, report = self.call("/report", request)
        self.assertEqual(status, 200)
        self.assertEqual(report["prediction"]["preprocessingVersion"], prediction["preprocessingVersion"])
        self.assertEqual(
            report["prediction"]["explainability"]["method"],
            "single_feature_training_median_perturbation",
        )
        self.assertIn("not a medical diagnosis", report["disclaimer"])

        status, _, fh_schema = self.call("/lab/genomics/fh/schema")
        self.assertEqual(status, 200)
        self.assertTrue(fh_schema["syntheticOnly"])
        status, _, fh_result = self.call(
            "/lab/genomics/fh/analyze", {"record": fh_schema["examples"][0]["record"]}
        )
        self.assertEqual(status, 200)
        self.assertTrue(fh_result["synthetic"])
        self.assertEqual(len(fh_result["researchModels"]), 2)

    def test_qcnn_image_prediction_and_invalid_uploads(self):
        stream = io.BytesIO()
        Image.fromarray(np.full((28, 28), 128, dtype=np.uint8), mode="L").save(
            stream, format="PNG"
        )
        status, headers, prediction = self.call_image(stream.getvalue())
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(prediction["model"]["id"], "breastmnist-qcnn")
        self.assertEqual(prediction["quantum"]["qubits"], 4)
        self.assertEqual(len(prediction["transformedFeatures"]), 4)
        self.assertEqual(len(prediction["explainability"]["regions"]), 4)
        self.assertEqual(prediction["quantum"]["circuitExecutionsThisPrediction"], 5)
        self.assertGreater(prediction["inferenceTimeMs"], 0)
        self.assertGreaterEqual(prediction["malignantScore"], 0)
        self.assertLessEqual(prediction["malignantScore"], 1)

        status, _, response = self.call_image(b"")
        self.assertEqual(status, 422)
        self.assertIn("missing", response["error"])
        status, _, response = self.call_image(b"broken")
        self.assertEqual(status, 422)
        self.assertIn("readable", response["error"])
        status, _, response = self.call_image(stream.getvalue(), "image/gif")
        self.assertEqual(status, 422)
        self.assertIn("Only PNG and JPEG", response["error"])

        status, _, response = self.call_image(
            b"x", declared_length=5 * 1024 * 1024 + 1
        )
        self.assertEqual(status, 422)
        self.assertIn("5 MB", response["error"])

        jpeg = io.BytesIO()
        Image.fromarray(np.full((28, 28), 128, dtype=np.uint8)).save(jpeg, format="JPEG")
        status, _, prediction = self.call_image(jpeg.getvalue(), "image/jpeg")
        self.assertEqual(status, 200)
        self.assertEqual(prediction["model"]["id"], "breastmnist-qcnn")

    def test_invalid_input_and_cors(self):
        example = schema("framingham-angle-qksvm-pca2")["demo"]
        status, _, response = self.call("/predict", {"modelId": "framingham-angle-qksvm-pca2", "features": {**example, "RANDID": 123}})
        self.assertEqual(status, 422)
        self.assertNotIn("123", json.dumps(response))
        denied = Request(self.base + "/models", headers={"Origin": "https://not-allowed.example"})
        with self.assertRaises(HTTPError) as caught:
            urlopen(denied, timeout=10)
        self.assertEqual(caught.exception.code, 403)


if __name__ == "__main__":
    unittest.main()

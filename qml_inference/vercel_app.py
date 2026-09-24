"""ASGI adapter for deploying the existing QML model store as a Vercel Service."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .errors import ArtifactError, InvalidInput
from .model import MODELS, ModelStore, schema
from .qcnn import MAX_IMAGE_BYTES, QcnnArtifactError, QcnnInputError, decode_image


class HardwareError(RuntimeError):
    pass


class VercelHardwareService:
    """Expose truthful hardware status without bundling provider SDKs into the function."""

    def __init__(self, model_store: ModelStore) -> None:
        self.store = model_store

    def capabilities(self) -> dict:
        return {
            "simulatorDefault": True,
            "providers": {
                "ibm": {"configured": False, "realHardwareOnly": True},
                "qbraid": {"configured": False, "realHardwareOnly": True},
            },
            "models": {
                "breastmnist-qcnn": {
                    "qubits": 4,
                    "circuitCount": 1,
                    "providers": {
                        "ibm": {"supported": False, "reason": "Provider SDK is not enabled in this Vercel deployment."},
                        "qbraid": {"supported": False, "reason": "Provider SDK is not enabled in this Vercel deployment."},
                    },
                },
                "framingham-angle-qksvm-pca2": {
                    "qubits": 2,
                    "circuitCount": int(self.store.fhs_qsvm.n_features_in_),
                    "providers": {
                        "ibm": {"supported": False, "reason": "Provider SDK is not enabled in this Vercel deployment."},
                        "qbraid": {"supported": False, "reason": "Provider SDK is not enabled in this Vercel deployment."},
                    },
                },
            },
            "credentialPolicy": "Provider execution is disabled on this deployment; analytic simulation remains available.",
        }

    @staticmethod
    def _unavailable() -> None:
        raise HardwareError("Real-hardware execution is not enabled in this Vercel deployment")

    def preview(self, model_id: str, provider: str):
        self._unavailable()

    def submit_tabular(self, *args, **kwargs):
        self._unavailable()

    def submit_qcnn(self, *args, **kwargs):
        self._unavailable()

    def get(self, job_id: str):
        raise KeyError(job_id)

root = Path(os.getenv("QML_BUNDLE_DIR", Path(__file__).parent / "artifacts/v1"))
store = ModelStore(root)
hardware = VercelHardwareService(store)
app = FastAPI(title="QDNA QML Inference", version=str(store.manifest["version"]))


def reply(data: dict | list, status: int = 200) -> JSONResponse:
    return JSONResponse(
        data,
        status_code=status,
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


def error(message: str, status: int) -> JSONResponse:
    return reply({"error": message}, status)


async def json_body(request: Request) -> dict:
    body = await request.body()
    if len(body) > 32_768:
        raise InvalidInput("JSON request is missing or too large")
    if "application/json" not in request.headers.get("content-type", ""):
        raise InvalidInput("Content-Type must be application/json")
    value = json.loads(body)
    if not isinstance(value, dict):
        raise InvalidInput("Expected a JSON object")
    return value


@app.get("/api/qml/v1/health")
def health():
    return reply({"status": "ready", "service": "qml-inference", "bundleVersion": store.manifest["version"]})


@app.get("/api/qml/v1/models")
def models(modality: str | None = None):
    if modality not in {None, "ehr", "genomics", "imaging"}:
        return error("modality must be ehr, genomics or imaging", 422)
    return reply({"models": store.models(modality), "disclaimer": store.evidence["framingham"]["limitation"]})


@app.get("/api/qml/v1/lab/modalities")
def modalities():
    counts = {name: len(store.models(name)) for name in ("ehr", "genomics", "imaging")}
    return reply({
        "modalities": [
            {"id": name, "name": label, "modelCount": counts[name], "status": "available"}
            for name, label in (("ehr", "EHR"), ("genomics", "Genomics"), ("imaging", "Medical imaging"))
        ],
        "disclaimer": "Research-use workflows only; no modality provides a medical diagnosis.",
    })


@app.get("/api/qml/v1/lab/models")
def lab_models(modality: str | None = None):
    if modality not in {None, "ehr", "genomics", "imaging"}:
        return error("modality must be ehr, genomics or imaging", 422)
    return reply({"models": store.models(modality)})


@app.get("/api/qml/v1/lab/genomics/fh/schema")
def fh_schema_route():
    from .fh import fh_schema

    return reply(fh_schema(store.fh.snapshot))


@app.get("/api/qml/v1/lab/evidence-snapshots/{snapshot_id}")
def evidence_snapshot(snapshot_id: str):
    if snapshot_id != store.fh.snapshot["snapshotId"]:
        return error("Evidence snapshot not found", 404)
    return reply(store.fh.snapshot)


@app.post("/api/qml/v1/lab/genomics/fh/analyze")
async def analyze_fh(request: Request):
    try:
        body = await json_body(request)
        if set(body) != {"record"}:
            raise InvalidInput("Expected record only")
        return reply(store.fh.analyze(body["record"]))
    except (InvalidInput, ValueError, TypeError, json.JSONDecodeError) as exc:
        return error(str(exc), 422)


@app.get("/api/qml/v1/evidence")
def evidence():
    return reply(store.evidence)


@app.get("/api/qml/v1/models/{model_id}/schema")
def model_schema(model_id: str):
    if not any(item["id"] == model_id for item in store.models()):
        return error("Model not found", 404)
    if model_id not in MODELS:
        return error("This model is evidence-only and has no live inference schema", 409)
    return reply(schema(model_id))


@app.get("/api/qml/v1/models/{model_id}/evidence")
def model_evidence(model_id: str):
    if not any(item["id"] == model_id for item in store.models()):
        return error("Model not found", 404)
    return reply(store.evidence_for(model_id))


async def prediction_response(request: Request, report: bool):
    try:
        body = await json_body(request)
        if set(body) != {"modelId", "features"}:
            raise InvalidInput("Expected modelId and features only")
        model_id = body["modelId"]
        if not isinstance(model_id, str) or model_id not in MODELS:
            return error("Model not found", 404)
        prediction = store.predict(model_id, body["features"])
        if not report:
            return reply(prediction)
        return reply({
            "reportId": uuid4().hex,
            "generatedAt": datetime.now(UTC).isoformat(),
            "prediction": prediction,
            "benchmark": store.evidence_for(model_id)["selectedRun"],
            "disclaimer": prediction["disclaimer"],
        })
    except (InvalidInput, ValueError, TypeError, json.JSONDecodeError) as exc:
        return error(str(exc), 422)
    except Exception:
        return error("QML inference is unavailable", 503)


@app.post("/api/qml/v1/predict")
async def predict(request: Request):
    return await prediction_response(request, False)


@app.post("/api/qml/v1/report")
async def report(request: Request):
    return await prediction_response(request, True)


@app.post("/api/qml/v1/qcnn/breastmnist/predict")
async def predict_qcnn(request: Request):
    try:
        body = await request.body()
        if len(body) > MAX_IMAGE_BYTES:
            raise QcnnInputError("Image must be 5 MB or smaller")
        return reply(store.predict_qcnn(body, request.headers.get("content-type", "")))
    except QcnnInputError as exc:
        return error(str(exc), 422)
    except (QcnnArtifactError, OSError, RuntimeError, ValueError):
        return error("QCNN inference is unavailable", 503)


@app.get("/api/qml/v1/hardware/capabilities")
def hardware_capabilities():
    return reply(hardware.capabilities())


@app.post("/api/qml/v1/hardware/preview")
async def hardware_preview(request: Request):
    try:
        body = await json_body(request)
        if set(body) != {"modelId", "provider"}:
            raise InvalidInput("Expected modelId and provider only")
        return reply(hardware.preview(str(body["modelId"]), str(body["provider"])))
    except InvalidInput as exc:
        return error(str(exc), 422)
    except HardwareError as exc:
        return error(str(exc), 409)


@app.post("/api/qml/v1/hardware/jobs")
async def submit_hardware(request: Request):
    try:
        body = await json_body(request)
        expected = {"modelId", "features", "provider", "shots", "confirmRealHardware"}
        if set(body) != expected:
            raise InvalidInput("Expected modelId, features, provider, shots and confirmRealHardware")
        job = hardware.submit_tabular(
            str(body["modelId"]), body["features"], str(body["provider"]),
            body["shots"], body["confirmRealHardware"] is True,
        )
        return reply(job.public(), 202)
    except InvalidInput as exc:
        return error(str(exc), 422)
    except HardwareError as exc:
        return error(str(exc), 409)


@app.post("/api/qml/v1/hardware/qcnn/breastmnist/jobs")
async def submit_qcnn_hardware(request: Request, provider: str = "", shots: str = "128", confirmRealHardware: bool = False):
    try:
        body = await request.body()
        if len(body) > MAX_IMAGE_BYTES:
            raise QcnnInputError("Image must be 5 MB or smaller")
        job = hardware.submit_qcnn(
            decode_image(body, request.headers.get("content-type", "")),
            provider,
            shots,
            confirmRealHardware,
        )
        return reply(job.public(), 202)
    except QcnnInputError as exc:
        return error(str(exc), 422)
    except HardwareError as exc:
        return error(str(exc), 409)


@app.get("/api/qml/v1/hardware/jobs/{job_id}")
def hardware_job(job_id: str):
    try:
        return reply(hardware.get(job_id).public())
    except KeyError:
        return error("Hardware job not found", 404)


@app.get("/api/qml/v1/hardware/jobs/{job_id}/results")
def hardware_result(job_id: str):
    try:
        job = hardware.get(job_id)
    except KeyError:
        return error("Hardware job not found", 404)
    if job.status == "failed":
        return error(job.error or "Hardware job failed", 409)
    if job.result is None:
        return reply(job.public(), 202)
    return reply(job.result)


@app.options("/{path:path}")
def options(path: str):
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
